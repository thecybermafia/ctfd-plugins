import hashlib
import hmac
import json
from CTFd.models import Flags, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.crossword.models import CrosswordChallenge
from CTFd.utils.user import is_admin

def parse_simple_clues(text):
    """
    Parses simple lines:
    Clue Question | Answer
    e.g.:
    Protocol for secure web browsing | HTTPS
    """
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
        if c:
            # ANTI-CHEAT: Send clues with length and number, but WITHOUT the cleartext answers!
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

            data.update({
                "clues_data": sanitized_clues,
            })
            if is_admin():
                data["clues_text"] = clues_to_simple_text(c.clues_json)
        return data

    @classmethod
    def create(cls, request):
        # Create the base challenge first, then persist crossword-specific
        # fields. Previously these were written to a local dict and discarded
        # because super().create(request) received the original request.
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

        for attr in ("grid_width", "grid_height"):
            if attr in data:
                try:
                    setattr(challenge, attr, int(data[attr]))
                except (TypeError, ValueError):
                    pass

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

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()
        if not submission:
            return ChallengeResponse(status="incorrect", message="No answer provided")

        c = CrosswordChallenge.query.filter_by(id=challenge.id).first()
        norm_sub = submission.upper()

        # Check solution word
        if c and c.solution_word:
            sol = c.solution_word.strip().upper()
            if hmac.compare_digest(norm_sub.encode("utf-8"), sol.encode("utf-8")):
                return ChallengeResponse(status="correct", message="Crossword solved successfully!")
            flag_wrap = f"FLAG{{{sol}}}"
            if hmac.compare_digest(norm_sub.encode("utf-8"), flag_wrap.encode("utf-8")):
                return ChallengeResponse(status="correct", message="Crossword solved successfully!")
            clean_sub = norm_sub.replace("FLAG{", "").rstrip("}")
            if hmac.compare_digest(clean_sub.encode("utf-8"), sol.encode("utf-8")):
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

        return ChallengeResponse(status="incorrect", message="Incorrect solution. Keep solving the clues!")
