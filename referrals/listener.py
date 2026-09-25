from sqlalchemy import event
from CTFd.models import Solves
from CTFd.plugins.referrals.models import Referrals
from CTFd.plugins.referrals.scoring import ReferralScoring


def on_solve_check_qualification(mapper, connection, target):
    """
    Listens for new solves to evaluate referral milestone qualifications.
    Executes safely at the connection level within the active flush transaction.
    """
    try:
        user_id = target.user_id
        if not user_id:
            return

        referral = Referrals.query.filter_by(referee_id=user_id, status="pending").first()
        if referral:
            ReferralScoring.check_and_qualify(referral, connection=connection)
    except Exception as e:
        # Defensive: Never let referral listener break solve recording
        print(f"[Referrals] Error during solve qualification check: {e}")


def register_referral_listeners():
    event.listen(Solves, "after_insert", on_solve_check_qualification)
