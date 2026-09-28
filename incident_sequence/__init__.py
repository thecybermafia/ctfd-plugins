from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.incident_sequence.challenge import IncidentSequenceChallengeType
from CTFd.plugins.incident_sequence.models import IncidentSequenceChallenge


def load(app):
    with app.app_context():
        IncidentSequenceChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["incident_sequence"] = IncidentSequenceChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/incident_sequence/assets/"
    )
