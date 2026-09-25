import ipaddress
from CTFd.models import Submissions, Tracking, Users, Teams
from CTFd.utils import get_config
from CTFd.plugins.referrals.config import ReferralConfig
from CTFd.plugins.referrals.models import ReferralCodes, Referrals


def resolve_user_ip(user_id):
    """
    Accurately resolves a user's most recent IP address from CTFd Tracking or Submissions.
    """
    if not user_id:
        return None
    try:
        track = Tracking.query.filter_by(user_id=user_id).order_by(Tracking.id.desc()).first()
        if track and track.ip and track.ip.strip():
            return track.ip.strip()
    except Exception:
        pass

    try:
        sub = Submissions.query.filter_by(user_id=user_id).order_by(Submissions.id.desc()).first()
        if sub and sub.ip and sub.ip.strip():
            return sub.ip.strip()
    except Exception:
        pass

    return None


class AntiCheatEngine:
    @staticmethod
    def is_same_subnet(ip1, ip2, prefix=24):
        if not ip1 or not ip2:
            return False
        try:
            net1 = ipaddress.ip_network(f"{ip1}/{prefix}", strict=False)
            net2 = ipaddress.ip_network(f"{ip2}/{prefix}", strict=False)
            return net1 == net2
        except ValueError:
            return False

    @staticmethod
    def evaluate_new_referral(referrer_user, referee_user, code_obj, referee_ip):
        """
        Validates a new referral linking attempt.
        Returns: (success: bool, status: str, message: str, notes: str)
        """
        if not ReferralConfig.get_bool("referral_enabled"):
            return False, "rejected", "Referral system is currently disabled by administrators.", ""

        if not referrer_user or not referee_user:
            return False, "rejected", "Invalid referrer or recruit operative.", ""

        # 0. User & Team Administrative Exclusion Checks
        if ReferralConfig.is_user_disabled(referrer_user.id):
            return False, "rejected", "Recruiter referral privileges have been suspended by administrators.", "Recruiter user is administratively disabled."

        if referrer_user.team_id and ReferralConfig.is_team_disabled(referrer_user.team_id):
            return False, "rejected", "Recruiter team referral privileges have been suspended by administrators.", "Recruiter team is administratively disabled."

        if ReferralConfig.is_user_disabled(referee_user.id):
            return False, "rejected", "Referral privileges for your account have been suspended.", "Recruit user is administratively disabled."

        if referee_user.team_id and ReferralConfig.is_team_disabled(referee_user.team_id):
            return False, "rejected", "Referral privileges for your team have been suspended.", "Recruit team is administratively disabled."

        # 1. Self-Referral Prevention
        if referrer_user.id == referee_user.id:
            return False, "rejected", "Self-referral is prohibited.", "Attempted to use own referral code."

        if referrer_user.email and referee_user.email and referrer_user.email.strip().lower() == referee_user.email.strip().lower():
            return False, "rejected", "Duplicate identity detected.", "Referrer and recruit share identical email address."

        # 2. Existing Referrer Check (A user can only be referred once)
        existing = Referrals.query.filter_by(referee_id=referee_user.id).first()
        if existing:
            return False, "rejected", "Operative has already been recruited by a verified syndicate.", "Duplicate referral attempt."

        # 3. Circular Referral Prevention (A referred B, so B cannot refer A)
        circular = Referrals.query.filter_by(referrer_id=referee_user.id, referee_id=referrer_user.id).first()
        if circular:
            return False, "rejected", "Circular recruitment loops are prohibited by tactical protocol.", "Circular referral loop detected."

        # 4. Team Mode Integrity Check
        user_mode = get_config("user_mode")
        disallow_teammates = ReferralConfig.get_bool("referral_disallow_teammates")
        if user_mode == "teams" and disallow_teammates:
            if referrer_user.team_id and referee_user.team_id:
                if referrer_user.team_id == referee_user.team_id:
                    return False, "rejected", "Teammates are prohibited from referring operatives within the same syndicate team.", "Teammate self-farming attempt."

        # 5. IP & Subnet Screening
        notes_list = []
        status = "pending"
        ip_policy = ReferralConfig.get("referral_ip_policy", "flag")
        referrer_ip = resolve_user_ip(referrer_user.id)

        is_ip_collision = (
            referrer_ip and referee_ip and referrer_ip.strip() == referee_ip.strip() and referee_ip.strip() != ""
        )
        is_subnet_collision = False
        if not is_ip_collision and ReferralConfig.get_bool("referral_block_subnets") and referrer_ip:
            is_subnet_collision = AntiCheatEngine.is_same_subnet(referrer_ip, referee_ip)

        if is_ip_collision:
            notes_list.append(f"Matching IP Address ({referee_ip}) with recruiter.")
            if ip_policy == "block":
                return False, "rejected", "Referral blocked: recruit shares identical network identity with recruiter.", "Identical IP address blocked."
            elif ip_policy == "flag":
                status = "flagged"

        elif is_subnet_collision:
            notes_list.append(f"Subnet /24 collision ({referee_ip} vs {referrer_ip}).")
            if ip_policy == "flag":
                status = "flagged"

        # 6. Referral Cap Check (Pre-screening)
        max_cap = ReferralConfig.get_int("referral_max_per_account")
        if max_cap > 0:
            if user_mode == "teams" and referrer_user.team_id:
                active_count = Referrals.query.filter(
                    Referrals.referrer_team_id == referrer_user.team_id,
                    Referrals.status.in_(["qualified", "pending"])
                ).count()
            else:
                active_count = Referrals.query.filter(
                    Referrals.referrer_id == referrer_user.id,
                    Referrals.status.in_(["qualified", "pending"])
                ).count()

            if active_count >= max_cap:
                notes_list.append(f"Recruiter has reached maximum reward allocation ({max_cap}).")
                if status != "flagged":
                    status = "cap_reached"

        notes = " | ".join(notes_list) if notes_list else "Clean onboarding."
        return True, status, "Recruitment established successfully.", notes
