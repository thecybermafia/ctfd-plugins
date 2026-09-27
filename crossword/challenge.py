import hashlib
import hmac
import json
from CTFd.models import Awards, Flags, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.crossword.models import CrosswordChallenge, CrosswordWordSolve
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def parse_simple_clues(text):
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    clues = []
    for i, line in enumerate(lines):
        parts = [p.strip() for p in line.split("|")]
        clue_text = parts[0] if len(parts) > 0 else f"Clue #{i+1}"
        answer = parts[1].upper() if len(parts) > 1 else "ANSWER"
        clues.append({
            "number": i + 1,
            "clue": clue_text,
            "answer": answer,
            "length": len(answer)
        })
    return clues


def clues_to_simple_text(clues_json):
    try:
        clues = json.loads(clues_json or "[]")
        lines = []
        for c in clues:
            lines.append(f"{c.get('clue', '')} | {c.get('answer', '')}")
        return "\n".join(lines)
    except Exception:
        return ""


class CrosswordChallengeType(BaseChallenge):
    id = "crossword"
    name = "crossword"
    templates = {
        "create": "/plugins/crossword/assets/create.html",
        "update": "/plugins/crossword/assets/update.html",
        "view": "/plugins/crossword/assets/view.html",
    }
    scripts = {
        "create": "/plugins/crossword/assets/create.js",
        "update": "/plugins/crossword/assets/update.js",
        "view": "/plugins/crossword/assets/view.js",
    }
    route = "/plugins/crossword/assets/"
    challenge_model = CrosswordChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = CrosswordChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return data

        user = get_current_user()
        team = get_current_team()

        sanitized_clues = []
        try:
            raw_clues = json.loads(c.clues_json or "[]")
            for item in raw_clues:
                sanitized_clues.append({
                    "number": item.get("number"),
                    "clue": item.get("clue"),
                    "length": item.get("length", len(item.get("answer", ""))),
                })
        except Exception as e:
            print("Error parsing clues JSON:", e)

        # Get solved clue numbers for user/team
        solved_clues = []
        if user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id
            solves = CrosswordWordSolve.query.filter_by(**filter_kwargs).all()
            solved_clues = [s.clue_number for s in solves]

        data.update({
            "clues_data": sanitized_clues,
            "solved_clues": solved_clues,
            "partial_scoring": bool(c.partial_scoring),
            "points_per_word": c.points_per_word or 10,
        })
        if is_admin():
            data["clues_text"] = clues_to_simple_text(c.clues_json)
        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        clues_text = data.get("clues_text", "")
        if clues_text:
            clues = parse_simple_clues(clues_text)
        else:
            clues = parse_simple_clues("Protocol for secure web | HTTPS\nSelf-replicating malware | WORM\nUnique network identifier | IP")

        challenge.clues_json = json.dumps(clues)

        sol_word = (data.get("solution_word") or "").strip()
        if sol_word:
            challenge.solution_word = sol_word
            challenge.solution_hash = hashlib.sha256(sol_word.upper().encode("utf-8")).hexdigest()

        challenge.partial_scoring = str(data.get("partial_scoring", "false")).lower() in ("true", "1", "yes", "on")
        challenge.points_per_word = int(data.get("points_per_word", 10) or 10)

        db.session.commit()
        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        if "clues_text" in data:
            clues = parse_simple_clues(data["clues_text"])
            challenge.clues_json = json.dumps(clues)

        if "solution_word" in data:
            challenge.solution_word = data["solution_word"].strip()
            challenge.solution_hash = hashlib.sha256(
                challenge.solution_word.upper().encode("utf-8")
            ).hexdigest()

        if "partial_scoring" in data:
            challenge.partial_scoring = str(data["partial_scoring"]).lower() in ("true", "1", "yes", "on")

        if "points_per_word" in data:
            challenge.points_per_word = int(data["points_per_word"] or 10)

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()
        if not submission:
            return ChallengeResponse(status="incorrect", message="No answer provided")

        c = CrosswordChallenge.query.filter_by(id=challenge.id).first()
        norm_sub = submission.upper()
        user = get_current_user()
        team = get_current_team()

        # Check solution word (full solve)
        if c and c.solution_word and hmac.compare_digest(norm_sub.encode("utf-8"), c.solution_word.strip().upper().encode("utf-8")):
            return ChallengeResponse(status="correct", message="Crossword solved successfully!")

        if c and c.solution_hash:
            sub_hash = hashlib.sha256(norm_sub.encode("utf-8")).hexdigest()
            if hmac.compare_digest(sub_hash.encode("utf-8"), c.solution_hash.encode("utf-8")):
                return ChallengeResponse(status="correct", message="Crossword solved successfully!")

        # Check if submission matches the concatenation of all clue answers
        if c:
            try:
                clues = json.loads(c.clues_json or "[]")
                all_answers = "".join([clue.get("answer", "").upper() for clue in clues])
                if all_answers and hmac.compare_digest(norm_sub.encode("utf-8"), all_answers.encode("utf-8")):
                    return ChallengeResponse(status="correct", message="All crossword clues solved successfully!")
            except Exception:
                pass

        # Fallback to standard CTFd Flags table
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="Crossword solved successfully!")
            except Exception:
                pass

        # Check individual clue answers if partial scoring is enabled
        if c and c.partial_scoring and user:
            try:
                clues = json.loads(c.clues_json or "[]")
                for clue in clues:
                    ans = (clue.get("answer") or "").upper().strip()
                    if ans and hmac.compare_digest(norm_sub.encode("utf-8"), ans.encode("utf-8")):
                        clue_num = clue.get("number")
                        filter_args = {"challenge_id": challenge.id, "clue_number": clue_num}
                        if team:
                            filter_args["team_id"] = team.id
                        else:
                            filter_args["user_id"] = user.id

                        existing = CrosswordWordSolve.query.filter_by(**filter_args).first()
                        if not existing:
                            word_solve = CrosswordWordSolve(
                                challenge_id=challenge.id,
                                user_id=user.id,
                                team_id=team.id if team else None,
                                clue_number=clue_num,
                                word=ans
                            )
                            db.session.add(word_solve)
                            pts = c.points_per_word or 10
                            if pts > 0:
                                award = Awards(
                                    user_id=None if team else user.id,
                                    team_id=team.id if team else None,
                                    name=f"Crossword Clue #{clue_num} [{challenge.name}]",
                                    description=f"Solved clue #{clue_num} in {challenge.name}",
                                    value=pts,
                                    category=challenge.category
                                )
                                db.session.add(award)
                            db.session.commit()
                            return ChallengeResponse(
                                status="incorrect",
                                message=f"Answer confirmed! Clue #{clue_num} solved (+{pts} pts awarded)."
                            )
                        else:
                            return ChallengeResponse(
                                status="incorrect",
                                message=f"You have already validated the answer for Clue #{clue_num}."
                            )
            except Exception:
                pass

        return ChallengeResponse(status="incorrect", message="Incorrect solution. Keep solving the clues!")
