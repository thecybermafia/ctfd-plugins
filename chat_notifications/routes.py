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
    configs = {
        # Webhook HMAC Shared Secret
        "shared_secret": get_shared_secret(),

        # Participant Channel
        "platform": get_config("chat_notifications_platform", "auto"),
        "webhook_url": (
            get_config("chat_notifications_webhook_url") or
            get_config("gchat_participant_webhook_url") or
            get_config("gchat_webhook_url", "")
        ),
        "enabled": (
            get_config("chat_notifications_enabled") or
            get_config("gchat_enabled", "true")
        ) == "true",
        "prefix": (
            get_config("chat_notifications_prefix") or
            get_config("gchat_prefix", "[CTFd]")
        ),
        "telegram_chat_id": get_config("chat_notifications_telegram_chat_id", ""),
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

        # Admin Operations Channel
        "admin_platform": get_config("chat_notifications_admin_platform", "auto"),
        "admin_webhook_url": (
            get_config("chat_notifications_admin_webhook_url") or
            get_config("gchat_admin_webhook_url", "")
        ),
        "admin_enabled": (
            get_config("chat_notifications_admin_enabled") or
            get_config("gchat_admin_enabled", "true")
        ) == "true",
        "admin_prefix": (
            get_config("chat_notifications_admin_prefix") or
            get_config("gchat_admin_prefix", "[CTFd-Admin]")
        ),
        "admin_telegram_chat_id": get_config("chat_notifications_admin_telegram_chat_id", ""),
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

    # 1. Participant Channel Configurations
    part_url = (data.get("webhook_url") or "").strip()
    part_platform = (data.get("platform") or "auto").strip()
    part_prefix = (data.get("prefix") or "[CTFd]").strip()
    part_tg = (data.get("telegram_chat_id") or "").strip()

    set_config("chat_notifications_platform", part_platform)
    set_config("chat_notifications_webhook_url", part_url)
    set_config("chat_notifications_prefix", part_prefix)
    set_config("chat_notifications_telegram_chat_id", part_tg)

    # Legacy key sync
    set_config("gchat_webhook_url", part_url)
    set_config("gchat_participant_webhook_url", part_url)
    set_config("gchat_prefix", part_prefix)

    # Participant event flags
    p_enabled = "true" if data.get("enabled") in (True, "true", "on", 1) else "false"
    p_ann = "true" if data.get("notify_announcements") in (True, "true", "on", 1) else "false"
    p_chal = "true" if data.get("notify_new_challenges") in (True, "true", "on", 1) else "false"
    p_fb = "true" if data.get("notify_first_blood") in (True, "true", "on", 1) else "false"
    p_solves = "true" if data.get("notify_all_solves") in (True, "true", "on", 1) else "false"
    p_reg = "true" if data.get("notify_registrations") in (True, "true", "on", 1) else "false"

    set_config("chat_notifications_enabled", p_enabled)
    set_config("gchat_enabled", p_enabled)
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

    # 2. Admin Operations Channel Configurations
    admin_url = (data.get("admin_webhook_url") or "").strip()
    admin_platform = (data.get("admin_platform") or "auto").strip()
    admin_prefix = (data.get("admin_prefix") or "[CTFd-Admin]").strip()
    admin_tg = (data.get("admin_telegram_chat_id") or "").strip()

    set_config("chat_notifications_admin_platform", admin_platform)
    set_config("chat_notifications_admin_webhook_url", admin_url)
    set_config("chat_notifications_admin_prefix", admin_prefix)
    set_config("chat_notifications_admin_telegram_chat_id", admin_tg)

    # Legacy key sync
    set_config("gchat_admin_webhook_url", admin_url)
    set_config("gchat_admin_prefix", admin_prefix)

    # Admin event flags
    a_enabled = "true" if data.get("admin_enabled") in (True, "true", "on", 1) else "false"
    a_reg = "true" if data.get("admin_notify_registrations") in (True, "true", "on", 1) else "false"
    a_sub = "true" if data.get("admin_notify_submissions") in (True, "true", "on", 1) else "false"
    a_ref = "true" if data.get("admin_notify_referrals") in (True, "true", "on", 1) else "false"
    a_mirror = "true" if data.get("mirror_participant_events") in (True, "true", "on", 1) else "false"

    set_config("chat_notifications_admin_enabled", a_enabled)
    set_config("gchat_admin_enabled", a_enabled)
    set_config("chat_notifications_admin_notify_registrations", a_reg)
    set_config("gchat_admin_notify_registrations", a_reg)
    set_config("chat_notifications_admin_notify_submissions", a_sub)
    set_config("gchat_admin_notify_submissions", a_sub)
    set_config("chat_notifications_admin_notify_referrals", a_ref)
    set_config("gchat_admin_notify_referrals", a_ref)
    set_config("chat_notifications_mirror_participant_events", a_mirror)
    # Shared Secret (if provided)
    custom_secret = (data.get("shared_secret") or "").strip()
    if custom_secret:
        set_config("chat_notifications_shared_secret", custom_secret)
        set_config("webhooks_shared_secret", custom_secret)

    return jsonify({"success": True, "message": "Chat notification configurations saved successfully!"})

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

