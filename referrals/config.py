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

    # 3. Qualification & Proof of Play
    "referral_min_points_to_qualify": "100",
    "referral_min_solves_to_qualify": "1",
    "referral_exclude_zero_point_chals": "true",

    # 4. Limits & Caps
    "referral_max_per_account": "5",
    "referral_global_point_cap": "0",  # 0 = unlimited

    # 5. Anti-Cheat & Security Shields
    "referral_ip_policy": "flag",  # 'flag', 'block', 'allow'
    "referral_disallow_teammates": "true",
    "referral_block_subnets": "false",
    "referral_auto_revoke_on_ban": "true",

    # 6. Exclusions & Suspensions (User and Team IDs)
    "referral_disabled_user_ids": "",
    "referral_disabled_team_ids": "",

    # 7. UI & Messaging
    "referral_broadcast_feed": "true",
    "referral_show_bonus_notice": "true",
    "referral_bonus_notice_text": "",
    "referral_show_progress_in_roster": "true",
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
    def get_bool(key):
        val = ReferralConfig.get(key)
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes", "on")

    @staticmethod
    def get_int(key):
        val = ReferralConfig.get(key)
        try:
            return int(val)
        except (ValueError, TypeError):
            def_val = DEFAULT_CONFIGS.get(key, 0)
    @staticmethod
    def get_bonus_notice_text():
        custom = (ReferralConfig.get("referral_bonus_notice_text") or "").strip()
        if custom:
            return custom
        pts = ReferralConfig.get_int("referral_points")
        req_pts = ReferralConfig.get_int("referral_min_points_to_qualify")
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
            elif k.endswith("_enabled") or k == "referral_show_in_navbar" or k.startswith("referral_disallow_") or k.startswith("referral_block_") or k.startswith("referral_exclude_") or k.startswith("referral_auto_"):
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
