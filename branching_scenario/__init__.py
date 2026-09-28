from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES
from CTFd.plugins.branching_scenario.challenge import BranchingScenarioChallengeType
from CTFd.plugins.branching_scenario.models import BranchingScenarioChallenge


def load(app):
    with app.app_context():
        BranchingScenarioChallenge.__table__.create(bind=db.engine, checkfirst=True)

    CHALLENGE_CLASSES["branching_scenario"] = BranchingScenarioChallengeType

    register_plugin_assets_directory(
        app, base_path="/plugins/branching_scenario/assets/"
    )
