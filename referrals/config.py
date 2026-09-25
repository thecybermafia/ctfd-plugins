from CTFd.utils import get_config, set_config

DEFAULT_CONFIGS = {
    # 1. Master & Branding
    "referral_enabled": "true",
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

    # 6. UI & Messaging
    "referral_broadcast_feed": "true",
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
            return int(def_val)

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
            if k in form_data:
                ReferralConfig.set(k, form_data[k])
            elif k.endswith("_enabled") or k.startswith("referral_disallow_") or k.startswith("referral_block_") or k.startswith("referral_exclude_") or k.startswith("referral_auto_"):
                # Checkbox missing in POST form means unchecked / false
                ReferralConfig.set(k, "false")
