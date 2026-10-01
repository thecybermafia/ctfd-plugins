from CTFd.models import db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
)
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.image_upload.api import image_upload_bp
from CTFd.plugins.image_upload.challenge import ImageUploadChallengeType
from CTFd.plugins.image_upload.models import (
    ImageUploadChallenge,
    ImageUploadFiles,
    ImageUploadSubmission,
)

def load(app):
    with app.app_context():
        ImageUploadChallenge.__table__.create(bind=db.engine, checkfirst=True)
        ImageUploadSubmission.__table__.create(bind=db.engine, checkfirst=True)

        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            existing = {c["name"] for c in inspector.get_columns("image_upload_challenge")}
            with db.engine.connect() as conn:
                if "allowed_extensions" not in existing:
                    conn.execute(text("ALTER TABLE image_upload_challenge ADD COLUMN allowed_extensions VARCHAR(256) DEFAULT 'png,jpg,jpeg,webp,gif'"))
                if "rubric_json" not in existing:
                    conn.execute(text("ALTER TABLE image_upload_challenge ADD COLUMN rubric_json TEXT NULL"))
                try:
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass

    app.register_blueprint(image_upload_bp)
    CHALLENGE_CLASSES["image_upload"] = ImageUploadChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/image_upload/assets/"
    )

    register_admin_plugin_menu_bar(title="Image Upload", route="/admin/image_uploads")
