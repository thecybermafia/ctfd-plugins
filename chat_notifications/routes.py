import secrets
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.plugins.chat_notifications.notifier import (
    get_shared_secret,
    test_webhook,
    validate_endpoint_ownership,
)

chat_notifications_bp = Blueprint(
    "chat_notifications",
    __name__,
    template_folder="templates",
    static_folder="assets",
)

@chat_notifications_bp.route("/admin/chat_notifications", methods=["GET"])
@admins_only
def admin_settings():
    from CTFd.plugins.chat_notifications.notifier import detect_platform

    configs = {
        # Webhook HMAC Shared Secret
        "shared_secret": get_shared_secret(),

        # Event flags (Participant)
        "notify_announcements": (
            get_config("chat_notifications_notify_announcements") or
            get_config("gchat_notify_announcements", "true")
        ) == "true",
        "notify_new_challenges": (
            get_config("chat_notifications_notify_new_challenges") or
            get_config("gchat_notify_new_challenges", "true")
        ) == "true",
        "notify_first_blood": (
            get_config("chat_notifications_notify_first_blood") or
            get_config("gchat_notify_first_blood", "true")
        ) == "true",
        "notify_all_solves": (
            get_config("chat_notifications_notify_all_solves") or
            get_config("gchat_notify_all_solves", "false")
        ) == "true",
        "notify_registrations": (
            get_config("chat_notifications_notify_registrations") or
            get_config("gchat_notify_registrations", "false")
        ) == "true",

        # Event flags (Admin)
        "admin_notify_registrations": (
            get_config("chat_notifications_admin_notify_registrations") or
            get_config("gchat_admin_notify_registrations", "true")
        ) == "true",
        "admin_notify_submissions": (
            get_config("chat_notifications_admin_notify_submissions") or
            get_config("gchat_admin_notify_submissions", "true")
        ) == "true",
        "admin_notify_referrals": (
            get_config("chat_notifications_admin_notify_referrals") or
            get_config("gchat_admin_notify_referrals", "true")
        ) == "true",
        "mirror_participant_events": (
            get_config("chat_notifications_mirror_participant_events") or
            get_config("gchat_mirror_participant_events", "false")
        ) == "true",
    }

    platforms = ["discord", "slack", "teams", "google_chat", "telegram", "custom"]
    for p in platforms:
        p_url = (get_config(f"webhook_{p}_participant_url") or "").strip()
        p_enabled = (get_config(f"webhook_{p}_participant_enabled") or "false") == "true"
        p_prefix = get_config(f"webhook_{p}_participant_prefix") or "[CTFd]"

        a_url = (get_config(f"webhook_{p}_admin_url") or "").strip()
        a_enabled = (get_config(f"webhook_{p}_admin_enabled") or "false") == "true"
        a_prefix = get_config(f"webhook_{p}_admin_prefix") or "[CTFd-Admin]"

        # Fallback to legacy config if per-platform config is empty
        if not p_url:
            leg_url = (get_config("chat_notifications_webhook_url") or get_config("gchat_participant_webhook_url") or get_config("gchat_webhook_url", "")).strip()
            leg_plat = get_config("chat_notifications_platform", "auto")
            resolved = leg_plat if leg_plat and leg_plat != "auto" else detect_platform(leg_url)
            if (p == "custom" and resolved == "generic") or p == resolved:
                p_url = leg_url
                p_enabled = (get_config("chat_notifications_enabled") or get_config("gchat_enabled", "true")) == "true"
                p_prefix = get_config("chat_notifications_prefix") or get_config("gchat_prefix", "[CTFd]")

        if not a_url:
            leg_a_url = (get_config("chat_notifications_admin_webhook_url") or get_config("gchat_admin_webhook_url", "")).strip()
            leg_a_plat = get_config("chat_notifications_admin_platform", "auto")
            resolved_a = leg_a_plat if leg_a_plat and leg_a_plat != "auto" else detect_platform(leg_a_url)
            if (p == "custom" and resolved_a == "generic") or p == resolved_a:
                a_url = leg_a_url
                a_enabled = (get_config("chat_notifications_admin_enabled") or get_config("gchat_admin_enabled", "true")) == "true"
                a_prefix = get_config("chat_notifications_admin_prefix") or get_config("gchat_admin_prefix", "[CTFd-Admin]")

        configs[f"{p}_participant_url"] = p_url
        configs[f"{p}_participant_enabled"] = p_enabled
        configs[f"{p}_participant_prefix"] = p_prefix
        configs[f"{p}_admin_url"] = a_url
        configs[f"{p}_admin_enabled"] = a_enabled
        configs[f"{p}_admin_prefix"] = a_prefix

    configs["telegram_participant_chat_id"] = get_config("webhook_telegram_participant_chat_id") or get_config("chat_notifications_telegram_chat_id", "")
    configs["telegram_admin_chat_id"] = get_config("webhook_telegram_admin_chat_id") or get_config("chat_notifications_admin_telegram_chat_id", "")

    return render_template("admin/chat_notifications.html", configs=configs)

# Backward Compatibility Alias Redirect
@chat_notifications_bp.route("/admin/google_chat", methods=["GET"])
@admins_only
def legacy_admin_redirect():
    return redirect("/admin/chat_notifications")

@chat_notifications_bp.route("/admin/chat_notifications/save", methods=["POST"])
@chat_notifications_bp.route("/admin/google_chat/save", methods=["POST"])
@admins_only
def save_settings():
    data = request.get_json() or request.form
    platforms = ["discord", "slack", "teams", "google_chat", "telegram", "custom"]

    first_part_url = ""
    first_part_enabled = "false"
    first_admin_url = ""
    first_admin_enabled = "false"

    for p in platforms:
        p_url = (data.get(f"{p}_participant_url") or "").strip()
        p_enabled = "true" if data.get(f"{p}_participant_enabled") in (True, "true", "on", 1) else "false"
        p_prefix = (data.get(f"{p}_participant_prefix") or "[CTFd]").strip()

        a_url = (data.get(f"{p}_admin_url") or "").strip()
        a_enabled = "true" if data.get(f"{p}_admin_enabled") in (True, "true", "on", 1) else "false"
        a_prefix = (data.get(f"{p}_admin_prefix") or "[CTFd-Admin]").strip()

        set_config(f"webhook_{p}_participant_url", p_url)
        set_config(f"webhook_{p}_participant_enabled", p_enabled)
        set_config(f"webhook_{p}_participant_prefix", p_prefix)

        set_config(f"webhook_{p}_admin_url", a_url)
        set_config(f"webhook_{p}_admin_enabled", a_enabled)
        set_config(f"webhook_{p}_admin_prefix", a_prefix)

        if p_url and p_enabled == "true" and not first_part_url:
            first_part_url = p_url
            first_part_enabled = "true"

        if a_url and a_enabled == "true" and not first_admin_url:
            first_admin_url = a_url
            first_admin_enabled = "true"

    # Telegram specific chat IDs
    tg_p_chat_id = (data.get("telegram_participant_chat_id") or "").strip()
    tg_a_chat_id = (data.get("telegram_admin_chat_id") or "").strip()
    set_config("webhook_telegram_participant_chat_id", tg_p_chat_id)
    set_config("webhook_telegram_admin_chat_id", tg_a_chat_id)
    set_config("chat_notifications_telegram_chat_id", tg_p_chat_id)
    set_config("chat_notifications_admin_telegram_chat_id", tg_a_chat_id)

    # Sync legacy keys for backward compatibility
    if first_part_url:
        set_config("chat_notifications_webhook_url", first_part_url)
        set_config("gchat_webhook_url", first_part_url)
        set_config("gchat_participant_webhook_url", first_part_url)
        set_config("chat_notifications_enabled", first_part_enabled)
        set_config("gchat_enabled", first_part_enabled)

    if first_admin_url:
        set_config("chat_notifications_admin_webhook_url", first_admin_url)
        set_config("gchat_admin_webhook_url", first_admin_url)
        set_config("chat_notifications_admin_enabled", first_admin_enabled)
        set_config("gchat_admin_enabled", first_admin_enabled)

    # Participant event flags
    p_ann = "true" if data.get("notify_announcements") in (True, "true", "on", 1) else "false"
    p_chal = "true" if data.get("notify_new_challenges") in (True, "true", "on", 1) else "false"
    p_fb = "true" if data.get("notify_first_blood") in (True, "true", "on", 1) else "false"
    p_solves = "true" if data.get("notify_all_solves") in (True, "true", "on", 1) else "false"
    p_reg = "true" if data.get("notify_registrations") in (True, "true", "on", 1) else "false"

    set_config("chat_notifications_notify_announcements", p_ann)
    set_config("gchat_notify_announcements", p_ann)
    set_config("chat_notifications_notify_new_challenges", p_chal)
    set_config("gchat_notify_new_challenges", p_chal)
    set_config("chat_notifications_notify_first_blood", p_fb)
    set_config("gchat_notify_first_blood", p_fb)
    set_config("chat_notifications_notify_all_solves", p_solves)
    set_config("gchat_notify_all_solves", p_solves)
    set_config("chat_notifications_notify_registrations", p_reg)
    set_config("gchat_notify_registrations", p_reg)

    # Admin event flags
    a_reg = "true" if data.get("admin_notify_registrations") in (True, "true", "on", 1) else "false"
    a_sub = "true" if data.get("admin_notify_submissions") in (True, "true", "on", 1) else "false"
    a_ref = "true" if data.get("admin_notify_referrals") in (True, "true", "on", 1) else "false"
    a_mirror = "true" if data.get("mirror_participant_events") in (True, "true", "on", 1) else "false"

    set_config("chat_notifications_admin_notify_registrations", a_reg)
    set_config("gchat_admin_notify_registrations", a_reg)
    set_config("chat_notifications_admin_notify_submissions", a_sub)
    set_config("gchat_admin_notify_submissions", a_sub)
    set_config("chat_notifications_admin_notify_referrals", a_ref)
    set_config("gchat_admin_notify_referrals", a_ref)
    set_config("chat_notifications_mirror_participant_events", a_mirror)

    # Shared Secret
    custom_secret = (data.get("shared_secret") or "").strip()
    if custom_secret:
        set_config("chat_notifications_shared_secret", custom_secret)
        set_config("webhooks_shared_secret", custom_secret)

    return jsonify({"success": True, "message": "All webhook configurations saved successfully!"})

@chat_notifications_bp.route("/admin/chat_notifications/secret/regenerate", methods=["POST"])
@admins_only
def regenerate_secret():
    new_secret = secrets.token_hex(32)
    set_config("chat_notifications_shared_secret", new_secret)
    set_config("webhooks_shared_secret", new_secret)
    return jsonify({"success": True, "secret": new_secret, "message": "Shared secret regenerated successfully!"})

@chat_notifications_bp.route("/admin/chat_notifications/validate_endpoint", methods=["POST"])
@admins_only
def validate_endpoint():
    data = request.get_json() or request.form
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"success": False, "message": "Endpoint URL cannot be empty"}), 400
    success, message = validate_endpoint_ownership(url)
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code

@chat_notifications_bp.route("/admin/chat_notifications/test", methods=["POST"])
@chat_notifications_bp.route("/admin/google_chat/test", methods=["POST"])
@admins_only
def trigger_test():
    data = request.get_json() or request.form
    target = data.get("target", "participant")

    if target == "admin":
        url = (
            data.get("admin_webhook_url") or
            get_config("chat_notifications_admin_webhook_url") or
            get_config("gchat_admin_webhook_url") or ""
        ).strip()
        platform = data.get("admin_platform") or get_config("chat_notifications_admin_platform", "auto")
        prefix = (
            data.get("admin_prefix") or
            get_config("chat_notifications_admin_prefix") or
            get_config("gchat_admin_prefix") or "[CTFd-Admin]"
        ).strip()
        chat_id = data.get("admin_telegram_chat_id") or get_config("chat_notifications_admin_telegram_chat_id")
        label = "Admin Ops Space"
    else:
        url = (
            data.get("webhook_url") or
            get_config("chat_notifications_webhook_url") or
            get_config("gchat_participant_webhook_url") or
            get_config("gchat_webhook_url") or ""
        ).strip()
        platform = data.get("platform") or get_config("chat_notifications_platform", "auto")
        prefix = (
            data.get("prefix") or
            get_config("chat_notifications_prefix") or
            get_config("gchat_prefix") or "[CTFd]"
        ).strip()
        chat_id = data.get("telegram_chat_id") or get_config("chat_notifications_telegram_chat_id")
        label = "Participant Space"

    if not url:
        return jsonify({"success": False, "message": f"No Webhook URL provided for {label}"}), 400

    success, res = test_webhook(url, platform=platform, prefix=prefix, channel_label=label, chat_id=chat_id)
    if success:
        return jsonify({"success": True, "message": f"Test notification sent successfully to {label}!"})
    else:
        return jsonify({"success": False, "message": f"Failed to send webhook to {label}: {res}"}), 500

