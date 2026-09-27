import json
from CTFd.models import Fails, Solves, Awards, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.cyber_wordle.models import WordleChallenge, WordleGuess
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def evaluate_guess(target, guess):
    """
    Standard Wordle evaluation:
    'correct' = green (right letter, right slot)
    'present' = yellow (right letter, wrong slot)
    'absent'  = gray (letter not in target word or already accounted for)
    """
    target = (target or "").upper().strip()
    guess = (guess or "").upper().strip()
    n = len(target)
    result = ["absent"] * n
    target_counts = {}

    for ch in target:
        target_counts[ch] = target_counts.get(ch, 0) + 1

    # First pass: find exact matches
    for i in range(min(n, len(guess))):
        if guess[i] == target[i]:
            result[i] = "correct"
            target_counts[guess[i]] -= 1

    # Second pass: find present letters
    for i in range(min(n, len(guess))):
        if result[i] != "correct" and guess[i] in target_counts and target_counts[guess[i]] > 0:
            result[i] = "present"
            target_counts[guess[i]] -= 1

    return result


class WordleChallengeType(BaseChallenge):
    id = "wordle"
    name = "wordle"
    templates = {
        "create": "/plugins/cyber_wordle/assets/create.html",
        "update": "/plugins/cyber_wordle/assets/update.html",
        "view": "/plugins/cyber_wordle/assets/view.html",
    }
    scripts = {
        "create": "/plugins/cyber_wordle/assets/create.js",
        "update": "/plugins/cyber_wordle/assets/update.js",
        "view": "/plugins/cyber_wordle/assets/view.js",
    }
    route = "/plugins/cyber_wordle/assets/"
    challenge_model = WordleChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = WordleChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return data

        user = get_current_user()
        team = get_current_team()
        is_user_admin = is_admin()

        data.update({
            "word_length": c.word_length or len(c.target_word or "CYBER"),
            "max_attempts": c.max_attempts or 6,
            "dynamic_scoring": bool(c.dynamic_scoring),
            "dictionary_enforced": bool(c.dictionary_enforced),
            "reveal_hint_after": c.reveal_hint_after or 4,
        })

        if is_user_admin:
            data["target_word"] = c.target_word
            data["hint_text"] = c.hint_text or ""

        # Fetch existing guesses for user/team
        guesses_history = []
        is_solved = False
        if user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id

            is_solved = Solves.query.filter_by(**filter_kwargs).first() is not None
            user_guesses = (
                WordleGuess.query.filter_by(**filter_kwargs)
                .order_by(WordleGuess.guess_number.asc())
                .all()
            )
            for g in user_guesses:
                guesses_history.append({
                    "number": g.guess_number,
                    "word": g.guess_word,
                    "evaluation": g.evaluation
                })

        data["guesses_history"] = guesses_history
        data["is_solved"] = is_solved
        if len(guesses_history) >= (c.reveal_hint_after or 4) or is_solved or is_user_admin:
            data["hint_text"] = c.hint_text or ""

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = WordleChallenge.query.filter_by(id=challenge.id).first()
        if c:
            raw_word = (data.get("target_word", "CYBER") or "CYBER").upper().strip()
            c.target_word = raw_word
            c.word_length = int(data.get("word_length", len(raw_word)) or len(raw_word))
            c.max_attempts = int(data.get("max_attempts", 6) or 6)
            c.dictionary_enforced = str(data.get("dictionary_enforced", "false")).lower() in ("true", "1", "yes", "on")
            c.dynamic_scoring = str(data.get("dynamic_scoring", "true")).lower() in ("true", "1", "yes", "on")
            c.reveal_hint_after = int(data.get("reveal_hint_after", 4) or 4)
            c.hint_text = data.get("hint_text", "")
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        if "target_word" in data:
            raw_word = (data["target_word"] or "CYBER").upper().strip()
            challenge.target_word = raw_word
            if "word_length" not in data:
                challenge.word_length = len(raw_word)

        if "word_length" in data:
            challenge.word_length = int(data["word_length"] or len(challenge.target_word))

        for attr in ("max_attempts", "reveal_hint_after"):
            if attr in data:
                setattr(challenge, attr, int(data[attr] or 0))

        for attr in ("dictionary_enforced", "dynamic_scoring"):
            if attr in data:
                val = str(data[attr]).lower() in ("true", "1", "yes", "on")
                setattr(challenge, attr, val)

        if "hint_text" in data:
            challenge.hint_text = data["hint_text"]

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").upper().strip()

        user = get_current_user()
        team = get_current_team()

        c = WordleChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        target = (c.target_word or "CYBER").upper().strip()
        expected_len = c.word_length or len(target)

        if len(submission) != expected_len:
            return ChallengeResponse(
                status="incorrect",
                message=f"Word must be exactly {expected_len} letters long."
            )

        if not submission.isalpha():
            return ChallengeResponse(
                status="incorrect",
                message="Submission must contain only letters."
            )

        # Count prior attempts
        filter_kwargs = {"challenge_id": c.id}
        if team:
            filter_kwargs["team_id"] = team.id
        else:
            filter_kwargs["user_id"] = user.id if user else 0

        prior_guesses = (
            WordleGuess.query.filter_by(**filter_kwargs)
            .order_by(WordleGuess.guess_number.asc())
            .all()
        )
        current_attempt = len(prior_guesses) + 1

        if current_attempt > (c.max_attempts or 6):
            return ChallengeResponse(
                status="incorrect",
                message=f"Maximum allowed guesses ({c.max_attempts}) reached for this puzzle."
            )

        # Evaluate guess
        eval_result = evaluate_guess(target, submission)

        # Record this guess
        guess_record = WordleGuess(
            challenge_id=c.id,
            user_id=user.id if user else 0,
            team_id=team.id if team else None,
            guess_number=current_attempt,
            guess_word=submission,
            result_json=json.dumps(eval_result)
        )
        db.session.add(guess_record)
        db.session.commit()

        # Check if solved
        if submission == target:
            msg = f"Decryption successful! Word cracked on attempt #{current_attempt}."
            return ChallengeResponse(status="correct", message=msg)

        if current_attempt >= (c.max_attempts or 6):
            return ChallengeResponse(
                status="incorrect",
                message=f"Maximum attempts ({c.max_attempts}) reached! The secret cipher was: {target}"
            )

        hint_msg = ""
        if current_attempt >= (c.reveal_hint_after or 4) and c.hint_text:
            hint_msg = f" Hint: {c.hint_text}"

        return ChallengeResponse(
            status="incorrect",
            message=f"Attempt {current_attempt}/{c.max_attempts} evaluated.{hint_msg}"
        )
