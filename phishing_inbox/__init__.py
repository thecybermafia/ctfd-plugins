from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.phishing_inbox.challenge import PhishingInboxChallengeType
from CTFd.plugins.phishing_inbox.models import PhishingInboxChallenge


def load(app):
    with app.app_context():
        PhishingInboxChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["phishing_inbox"] = PhishingInboxChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/phishing_inbox/assets/"
    )
