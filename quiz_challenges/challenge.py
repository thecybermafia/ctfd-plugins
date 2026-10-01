import hashlib
import json
import random
from CTFd.models import Fails, Solves, Awards, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.quiz_challenges.models import QuizChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def parse_options_text(text):
    """
    Parses admin-entered options text into a structured JSON list.
    Options starting with '*' or '[x]' or '[X]' are marked as correct.
    e.g.:
    * Multi-Factor Authentication
    Single password only
    * Security Key token
    """
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    options = []
    for idx, line in enumerate(lines):
        is_correct = False
        clean_text = line
        if line.startswith("*"):
            is_correct = True
            clean_text = line.lstrip("*").strip()
        elif line.lower().startswith("[x]"):
            is_correct = True
            clean_text = line[3:].strip()
        elif line.startswith("[ ]"):
            is_correct = False
            clean_text = line[3:].strip()

        options.append({
            "id": f"opt_{idx}",
            "text": clean_text,
            "correct": is_correct
        })
    return options


def options_to_text(options_json):
    """Converts options JSON back to editable text for admin update form."""
    try:
        opts = json.loads(options_json or "[]")
        lines = []
        for o in opts:
            prefix = "* " if o.get("correct") else ""
            lines.append(f"{prefix}{o.get('text', '')}")
        return "\n".join(lines)
    except Exception:
        return ""


def get_deterministic_shuffle(items, seed_key):
    """Shuffles items consistently for a given user/team seed."""
    if not items:
        return items
    shuffled = list(items)
    seed = int(hashlib.md5(str(seed_key).encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    return shuffled


class QuizChallengeType(BaseChallenge):
    id = "quiz"
    name = "quiz"
    templates = {
        "create": "/plugins/quiz_challenges/assets/create.html",
        "update": "/plugins/quiz_challenges/assets/update.html",
        "view": "/plugins/quiz_challenges/assets/view.html",
    }
    scripts = {
        "create": "/plugins/quiz_challenges/assets/create.js",
        "update": "/plugins/quiz_challenges/assets/update.js",
        "view": "/plugins/quiz_challenges/assets/view.js",
    }
    route = "/plugins/quiz_challenges/assets/"
    challenge_model = QuizChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = QuizChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return data

        user = get_current_user()
        team = get_current_team()
        is_user_admin = is_admin()

        data.update({
            "question_mode": c.question_mode or "single",
            "randomize_options": bool(c.randomize_options),
            "max_attempts": c.max_attempts or 0,
            "penalty_per_attempt": c.penalty_per_attempt or 0,
            "partial_scoring": bool(c.partial_scoring),
        })

        # Calculate attempts count for user/team
        attempts_used = 0
        is_solved = False
        if user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id

            attempts_used = Fails.query.filter_by(**filter_kwargs).count()
            is_solved = Solves.query.filter_by(**filter_kwargs).first() is not None

        data["attempts_used"] = attempts_used
        data["is_solved"] = is_solved

        # Explanation is only visible to admin or after solve
        if is_user_admin or is_solved:
            data["explanation"] = c.explanation or ""

        if is_user_admin:
            data["options_text"] = options_to_text(c.options_json)
            data["options_data"] = c.options_data
        else:
            # Client gets sanitized options
            sanitized = c.get_sanitized_options()
            if c.randomize_options:
                seed = f"{team.id if team else (user.id if user else 0)}_{c.id}"
                sanitized = get_deterministic_shuffle(sanitized, seed)
            data["options_data"] = sanitized

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = QuizChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.question_mode = data.get("question_mode", "single")
            c.randomize_options = str(data.get("randomize_options", "true")).lower() in ("true", "1", "yes", "on")
            c.max_attempts = int(data.get("max_attempts", 0) or 0)
            c.penalty_per_attempt = int(data.get("penalty_per_attempt", 0) or 0)
            c.explanation = data.get("explanation", "")
            c.partial_scoring = str(data.get("partial_scoring", "false")).lower() in ("true", "1", "yes", "on")

            options_text = data.get("options_text", "")
            opts = parse_options_text(options_text)
            c.options_json = json.dumps(opts)
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        for attr in ("question_mode", "explanation"):
            if attr in data:
                setattr(challenge, attr, data[attr])

        for attr in ("max_attempts", "penalty_per_attempt"):
            if attr in data:
                setattr(challenge, attr, int(data[attr] or 0))

        for attr in ("randomize_options", "partial_scoring"):
            if attr in data:
                val = str(data[attr]).lower() in ("true", "1", "yes", "on")
                setattr(challenge, attr, val)

        if "options_text" in data and data["options_text"].strip():
            opts = parse_options_text(data["options_text"])
            challenge.options_json = json.dumps(opts)

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        user = get_current_user()
        team = get_current_team()

        c = QuizChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Check max attempts limit
        if c.max_attempts and c.max_attempts > 0 and user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id

            used = Fails.query.filter_by(**filter_kwargs).count()
            if used >= c.max_attempts:
                return ChallengeResponse(
                    status="incorrect",
                    message=f"Maximum allowed attempts ({c.max_attempts}) reached for this challenge."
                )

        # Parse user submission
        submitted_ids = set()
        if submission.startswith("[") and submission.endswith("]"):
            try:
                parsed = json.loads(submission)
                if isinstance(parsed, list):
                    submitted_ids = {str(x).strip() for x in parsed}
            except Exception:
                submitted_ids = {submission}
        elif "," in submission:
            submitted_ids = {x.strip() for x in submission.split(",") if x.strip()}
        else:
            submitted_ids = {submission}

        # Determine correct option IDs
        correct_ids = {opt["id"] for opt in c.options_data if opt.get("correct")}

        if not correct_ids:
            return ChallengeResponse(
                status="incorrect",
                message="No correct answers configured by admin."
            )

        # Verify answer
        if submitted_ids == correct_ids:
            msg = "Correct answer!"
            if c.explanation:
                msg = f"Correct! {c.explanation}"
            return ChallengeResponse(status="correct", message=msg)

        # Handle wrong attempt penalty if configured
        if c.penalty_per_attempt and c.penalty_per_attempt > 0 and user:
            # Create a penalty award
            award = Awards(
                user_id=user.id,
                team_id=team.id if team else None,
                name=f"Quiz Penalty: {challenge.name}",
                description=f"Incorrect attempt deduction on challenge {challenge.name}",
                value=-c.penalty_per_attempt,
                category="Penalties"
            )
            db.session.add(award)
            db.session.commit()
            return ChallengeResponse(
                status="incorrect",
                message=f"Incorrect selection. {c.penalty_per_attempt} points deducted. Please review and try again."
            )

        return ChallengeResponse(
            status="incorrect",
            message="Incorrect selection. Please review your choices and try again."
        )
