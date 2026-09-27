import json
from flask import Blueprint
from CTFd.models import db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.image_upload.models import ImageUploadChallenge
from CTFd.utils.user import is_admin


def parse_rubric_text(text):
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    rubric = []
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        name = parts[0] if len(parts) > 0 else "Criteria"
        max_pts = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
        rubric.append({"name": name, "max_points": max_pts})
    return rubric


def rubric_to_text(rubric_json):
    try:
        data = json.loads(rubric_json or "[]")
        return "\n".join([f"{r.get('name', '')} | {r.get('max_points', 10)}" for r in data])
    except Exception:
        return ""


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
                "rubric_data": c.rubric_data,
            })
            if is_admin():
                data["rubric_text"] = rubric_to_text(c.rubric_json)
        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = ImageUploadChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.max_file_size_mb = int(data.get("max_file_size_mb", 10) or 10)
            c.allowed_extensions = data.get("allowed_extensions", "png,jpg,jpeg,webp,gif,pdf,docx,txt,zip")
            rubric_text = data.get("rubric_text", "")
            if rubric_text:
                c.rubric_json = json.dumps(parse_rubric_text(rubric_text))
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}
        for attr in ("max_file_size_mb", "allowed_extensions"):
            if attr in data:
                val = data[attr]
                if attr == "max_file_size_mb":
                    val = int(val)
                setattr(challenge, attr, val)

        if "rubric_text" in data:
            challenge.rubric_json = json.dumps(parse_rubric_text(data["rubric_text"]))

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        return ChallengeResponse(
            status="incorrect",
            message="This is a file / proof upload challenge. Please use the upload form to submit your document or evidence for review."
        )
