from CTFd.models import db
from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
)
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.image_upload.api import image_upload_bp
from CTFd.plugins.image_upload.challenge import ImageUploadChallengeType
from CTFd.plugins.image_upload.models import ImageUploadChallenge, ImageUploadSubmission

def load(app):
    with app.app_context():
        ImageUploadChallenge.__table__.create(bind=db.engine, checkfirst=True)
        ImageUploadSubmission.__table__.create(bind=db.engine, checkfirst=True)

    app.register_blueprint(image_upload_bp)
    CHALLENGE_CLASSES["image_upload"] = ImageUploadChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/image_upload/assets/"
    )

    register_admin_plugin_menu_bar(title="Image Reviews", route="/admin/image_uploads")
