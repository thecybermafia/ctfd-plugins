from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.red_flag_hotspot.challenge import RedFlagHotspotChallengeType
from CTFd.plugins.red_flag_hotspot.models import HotspotChallenge


def load(app):
    with app.app_context():
        HotspotChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["red_flag_hotspot"] = RedFlagHotspotChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/red_flag_hotspot/assets/"
    )
