from flask import Blueprint
from CTFd.models import db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.textarea.models import TextareaChallenge
from CTFd.utils.user import is_admin


class TextareaChallengeType(BaseChallenge):
    id = "textarea"
    name = "textarea"
    templates = {
        "create": "/plugins/textarea/assets/create.html",
        "update": "/plugins/textarea/assets/update.html",
        "view": "/plugins/textarea/assets/view.html",
    }
    scripts = {
        "create": "/plugins/textarea/assets/create.js",
        "update": "/plugins/textarea/assets/update.js",
        "view": "/plugins/textarea/assets/view.js",
    }
    route = "/plugins/textarea/assets/"
    challenge_model = TextareaChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = TextareaChallenge.query.filter_by(id=challenge.id).first()
        if c:
            data.update({
                "min_chars": c.min_chars,
                "max_chars": c.max_chars,
                "placeholder": c.placeholder,
            })
            if is_admin():
                data.update({
                    "auto_grade": bool(c.auto_grade),
                    "required_keywords": c.required_keywords or "",
                    "auto_pass_mode": c.auto_pass_mode or "all",
                    "auto_award_points": c.auto_award_points or 0,
                })
        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = TextareaChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.min_chars = int(data.get("min_chars", 0) or 0)
            c.max_chars = int(data.get("max_chars", 5000) or 5000)
            c.placeholder = data.get("placeholder", "")
            c.auto_grade = str(data.get("auto_grade", "false")).lower() in ("true", "1", "yes", "on")
            c.required_keywords = data.get("required_keywords", "")
            c.auto_pass_mode = data.get("auto_pass_mode", "all")
            c.auto_award_points = int(data.get("auto_award_points", 0) or 0)
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}
        for attr in ("min_chars", "max_chars", "auto_award_points"):
            if attr in data:
                try:
                    setattr(challenge, attr, int(data[attr] or 0))
                except (ValueError, TypeError):
                    pass

        for attr in ("placeholder", "required_keywords", "auto_pass_mode"):
            if attr in data:
                setattr(challenge, attr, data[attr])

        if "auto_grade" in data:
            challenge.auto_grade = str(data["auto_grade"]).lower() in ("true", "1", "yes", "on")

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        return ChallengeResponse(
            status="incorrect",
            message="This is an open response / writeup challenge. Please submit your response using the writeup box."
        )
