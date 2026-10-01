from flask import Blueprint
from CTFd.models import db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.image_upload.models import ImageUploadChallenge

class ImageUploadChallengeType(BaseChallenge):
    id = "image_upload"
    name = "image_upload"
    templates = {
        "create": "/plugins/image_upload/assets/create.html",
        "update": "/plugins/image_upload/assets/update.html",
        "view": "/plugins/image_upload/assets/view.html",
    }
    scripts = {
        "create": "/plugins/image_upload/assets/create.js",
        "update": "/plugins/image_upload/assets/update.js",
        "view": "/plugins/image_upload/assets/view.js",
    }
    route = "/plugins/image_upload/assets/"
    challenge_model = ImageUploadChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = ImageUploadChallenge.query.filter_by(id=challenge.id).first()
        if c:
            data.update({
                "max_file_size_mb": c.max_file_size_mb,
                "allowed_extensions": c.allowed_extensions,
            })
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}
        for attr in ("max_file_size_mb", "allowed_extensions"):
            if attr in data:
                val = data[attr]
                if attr == "max_file_size_mb":
                    val = int(val)
                setattr(challenge, attr, val)
        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        # Instruct users that this is an image upload challenge
        return ChallengeResponse(
            status="incorrect",
            message="This is an image upload challenge. Please use the image uploader to submit your solution for review."
        )
