from CTFd.models import db
from CTFd.plugins.challenges import BaseChallenge
from CTFd.plugins.textarea.models import TextareaChallenge

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
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}
        for attr in ("min_chars", "max_chars"):
            if attr in data and data[attr] is not None and str(data[attr]).isdigit():
                setattr(challenge, attr, int(data[attr]))
        if "placeholder" in data:
            challenge.placeholder = str(data["placeholder"])
        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        return False, "This mission requires manual evaluation by Mission Control. Please submit your text writeup."
