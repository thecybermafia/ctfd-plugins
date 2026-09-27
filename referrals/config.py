from CTFd.utils import get_config, set_config

DEFAULT_CONFIGS = {
    # 1. Master, Navigation & Branding
    "referral_enabled": "true",
    "referral_show_in_navbar": "false",  # Default false as requested
    "referral_program_name": "Operative Recruitment Directive",
    "referral_code_prefix": "REF-",
    "referral_cookie_ttl_days": "7",

    # 2. Rewards & Points
    "referral_points": "100",
    "referral_referee_bonus_enabled": "true",
    "referral_referee_bonus_points": "25",
    "referral_award_category": "Recruitment Directive",

    # 3. Qualification & Proof of Play (Recruit Training)
    "referral_qualification_mode": "points_only",  # 'points_only', 'challenge_only', 'both', 'either'
    "referral_required_challenge_id": "",
    "referral_min_points_to_qualify": "100",
    "referral_min_solves_to_qualify": "1",
    "referral_exclude_zero_point_chals": "true",

    # 4. Limits & Caps
    "referral_max_per_account": "5",
    "referral_global_point_cap": "0",  # 0 = unlimited

    # 5. Referrer Access Gate (Prerequisites to unlock / access referral terminal)
    "referral_unlock_mode": "none",  # 'none', 'points', 'solves', 'challenge', 'all', 'any'
    "referral_unlock_min_points": "0",
    "referral_unlock_min_solves": "0",
    "referral_unlock_challenge_id": "",
    "referral_access_denied_message": "Referral system access restricted: Complete prerequisite training or contact command staff.",

    # 6. Anti-Cheat & Security Shields
    "referral_ip_policy": "flag",  # 'flag', 'block', 'allow'
    "referral_disallow_teammates": "true",
    "referral_block_subnets": "false",
    "referral_auto_revoke_on_ban": "true",

    # 7. Exclusions & Suspensions (User and Team IDs)
    "referral_disabled_user_ids": "",
    "referral_disabled_team_ids": "",

    # 8. UI & Messaging
    "referral_broadcast_feed": "true",
    "referral_show_bonus_notice": "true",
    "referral_bonus_notice_text": "",
    "referral_show_progress_in_roster": "true",
    "referral_leaderboard_visible": "true",
    "referral_instructions": (
        "Share your unique recruit link with operatives to expand your syndicate. "
        "Bonus points unlock when your recruit proves field capability by reaching the challenge score milestone!"
    ),
}


class ReferralConfig:
    @staticmethod
    def get(key, default=None):
        def_val = DEFAULT_CONFIGS.get(key, default)
        val = get_config(key)
        if val is None or val == "":
            return def_val
        return val

    @staticmethod
    def get_bool(key, default=False):
        val = ReferralConfig.get(key, default)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes", "on")

    @staticmethod
    def get_int(key, default=0):
        val = ReferralConfig.get(key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return int(DEFAULT_CONFIGS.get(key, default))

    @staticmethod
    def get_bonus_notice_text():
        custom = (ReferralConfig.get("referral_bonus_notice_text") or "").strip()
        if custom:
            return custom
        pts = ReferralConfig.get_int("referral_points")
        req_pts = ReferralConfig.get_int("referral_min_points_to_qualify")
        mode = ReferralConfig.get("referral_qualification_mode", "points_only")
        chal_id = ReferralConfig.get("referral_required_challenge_id", "")
        chal_name = None
        if chal_id:
            try:
                from CTFd.models import Challenges
                c = Challenges.query.filter_by(id=int(chal_id)).first()
                if c:
                    chal_name = c.name
            except Exception:
                pass

        if mode == "challenge_only" and chal_name:
            return f"Earn +{pts} PTS per recruit who completes training by solving challenge '{chal_name}'."
        elif mode == "both" and chal_name:
            return f"Earn +{pts} PTS per recruit who scores ≥ {req_pts} points and solves challenge '{chal_name}'."
        elif mode == "either" and chal_name:
            return f"Earn +{pts} PTS per recruit who scores ≥ {req_pts} points or solves challenge '{chal_name}'."
        return f"Earn +{pts} PTS per recruit who proves capability by scoring ≥ {req_pts} points."

    @staticmethod
    def set(key, value):
        set_config(key, str(value))

    @staticmethod
    def get_all():
        data = {}
        for k in DEFAULT_CONFIGS.keys():
            data[k] = ReferralConfig.get(k)
        return data

    @staticmethod
    def update_all(form_data):
        for k in DEFAULT_CONFIGS.keys():
            if k in ("referral_disabled_user_ids", "referral_disabled_team_ids"):
                continue  # Handled separately via exclusion controls
            if k in form_data:
                ReferralConfig.set(k, form_data[k])
            elif k in (
                "referral_enabled",
                "referral_show_in_navbar",
                "referral_broadcast_feed",
                "referral_referee_bonus_enabled",
                "referral_exclude_zero_point_chals",
                "referral_show_progress_in_roster",
                "referral_show_bonus_notice",
                "referral_block_subnets",
                "referral_disallow_teammates",
                "referral_auto_revoke_on_ban",
                "referral_leaderboard_visible",
            ):
                ReferralConfig.set(k, "false")

    # --- Exclusion Management for Users & Teams ---
    @staticmethod
    def get_disabled_user_ids():
        raw = ReferralConfig.get("referral_disabled_user_ids", "")
        if not raw:
            return set()
        return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

    @staticmethod
    def get_disabled_team_ids():
        raw = ReferralConfig.get("referral_disabled_team_ids", "")
        if not raw:
            return set()
        return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}

    @staticmethod
    def is_user_disabled(user_id):
        if not user_id:
            return False
        return int(user_id) in ReferralConfig.get_disabled_user_ids()

    @staticmethod
    def is_team_disabled(team_id):
        if not team_id:
            return False
        return int(team_id) in ReferralConfig.get_disabled_team_ids()

    @staticmethod
    def add_disabled_user(user_id):
        s = ReferralConfig.get_disabled_user_ids()
        s.add(int(user_id))
        ReferralConfig.set("referral_disabled_user_ids", ",".join(str(x) for x in sorted(s)))

    @staticmethod
    def remove_disabled_user(user_id):
        s = ReferralConfig.get_disabled_user_ids()
        s.discard(int(user_id))
        ReferralConfig.set("referral_disabled_user_ids", ",".join(str(x) for x in sorted(s)))

    @staticmethod
    def add_disabled_team(team_id):
        s = ReferralConfig.get_disabled_team_ids()
        s.add(int(team_id))
        ReferralConfig.set("referral_disabled_team_ids", ",".join(str(x) for x in sorted(s)))

    @staticmethod
    def remove_disabled_team(team_id):
        s = ReferralConfig.get_disabled_team_ids()
        s.discard(int(team_id))
        ReferralConfig.set("referral_disabled_team_ids", ",".join(str(x) for x in sorted(s)))
