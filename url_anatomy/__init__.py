from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.url_anatomy.challenge import UrlAnatomyChallengeType
from CTFd.plugins.url_anatomy.models import UrlAnatomyChallenge


def load(app):
    with app.app_context():
        UrlAnatomyChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["url_anatomy"] = UrlAnatomyChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/url_anatomy/assets/"
    )
