import logging
from sqlalchemy import event, inspect
from CTFd.models import Challenges, Notifications, Solves, Teams, Users, db
from CTFd.plugins import register_admin_plugin_menu_bar
from CTFd.plugins.google_chat.notifier import (
    notify_announcement,
    notify_first_blood,
    notify_new_challenge,
    notify_registration,
    notify_solve,
)
from CTFd.plugins.google_chat.routes import google_chat_bp

logger = logging.getLogger("google_chat_plugin")

# Notifications are queued during the flush and only dispatched once the
# transaction has committed. Running queries or loading relationships inside
# after_insert (i.e. mid-flush) is unsafe and made first-blood detection racy.
_PENDING_ATTR = "_gchat_pending_notifications"


def _queue(session, fn, *args, **kwargs):
    pending = getattr(session, _PENDING_ATTR, None)
    if pending is None:
        pending = []
        setattr(session, _PENDING_ATTR, pending)
    pending.append((fn, args, kwargs))


def setup_event_listeners():
    @event.listens_for(Notifications, "after_insert")
    def on_notification_created(mapper, connection, target):
        _queue(db.session, notify_announcement, target)

    @event.listens_for(Challenges, "after_insert")
    def on_challenge_created(mapper, connection, target):
        if target.state == "visible":
            _queue(db.session, notify_new_challenge, target)

    @event.listens_for(Challenges, "after_update")
    def on_challenge_updated(mapper, connection, target):
        try:
            hist = inspect(target).attrs.state.history
            if hist.has_changes():
                old_state = hist.deleted[0] if hist.deleted else None
                new_state = target.state
                if old_state == "hidden" and new_state == "visible":
                    _queue(db.session, notify_new_challenge, target)
        except Exception as e:
            logger.warning(f"Error checking challenge state transition: {e}")

    @event.listens_for(Solves, "after_insert")
    def on_solve_created(mapper, connection, target):
        # Only capture identifiers here; resolve details after commit.
        _queue(db.session, _dispatch_solve, target.id)

    @event.listens_for(Teams, "after_insert")
    def on_team_registered(mapper, connection, target):
        _queue(db.session, notify_registration, target.name, True)

    @event.listens_for(Users, "after_insert")
    def on_user_registered(mapper, connection, target):
        if getattr(target, "type", "user") != "admin":
            _queue(db.session, notify_registration, target.name, False)

    @event.listens_for(db.session, "after_commit")
    def on_after_commit(session):
        pending = getattr(session, _PENDING_ATTR, None)
        if not pending:
            return
        setattr(session, _PENDING_ATTR, [])
        for fn, args, kwargs in pending:
            try:
                fn(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Error dispatching queued Google Chat notification: {e}")

    @event.listens_for(db.session, "after_rollback")
    def on_after_rollback(session):
        setattr(session, _PENDING_ATTR, [])


def _dispatch_solve(solve_id):
    """Resolve a committed solve and dispatch solve / first-blood notifications."""
    solve = Solves.query.filter_by(id=solve_id).first()
    if not solve:
        return

    chal = Challenges.query.filter_by(id=solve.challenge_id).first()
    solver_name = "Anonymous"
    if solve.team:
        solver_name = solve.team.name
    elif solve.user:
        solver_name = solve.user.name

    # First blood = the earliest solve on this challenge, determined from
    # committed data by ordering, which is robust against concurrency.
    first_solve = (
        Solves.query.filter_by(challenge_id=solve.challenge_id)
        .order_by(Solves.date.asc(), Solves.id.asc())
        .first()
    )
    if first_solve and first_solve.id == solve.id:
        notify_first_blood(chal, solver_name)
    else:
        notify_solve(chal, solver_name)


def load(app):
    # Register admin blueprint
    app.register_blueprint(google_chat_bp)

    # Register admin navigation link
    register_admin_plugin_menu_bar(title="Google Chat", route="/admin/google_chat")

    # Set up database event hooks
    setup_event_listeners()
    logger.info("Google Chat Notifications plugin loaded successfully.")
