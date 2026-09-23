from flask import Blueprint, jsonify, render_template, request
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.plugins.google_chat.notifier import test_webhook

google_chat_bp = Blueprint(
    "google_chat",
    __name__,
    template_folder="templates",
    static_folder="assets",
)

@google_chat_bp.route("/admin/google_chat", methods=["GET"])
@admins_only
def admin_settings():
    configs = {
        "webhook_url": get_config("gchat_webhook_url", ""),
        "enabled": get_config("gchat_enabled", "true") == "true",
        "prefix": get_config("gchat_prefix", "[CTFd]"),
        "notify_announcements": get_config("gchat_notify_announcements", "true") == "true",
        "notify_new_challenges": get_config("gchat_notify_new_challenges", "true") == "true",
        "notify_first_blood": get_config("gchat_notify_first_blood", "true") == "true",
        "notify_all_solves": get_config("gchat_notify_all_solves", "false") == "true",
        "notify_registrations": get_config("gchat_notify_registrations", "false") == "true",
    }
    return render_template("admin/google_chat.html", configs=configs)

@google_chat_bp.route("/admin/google_chat/save", methods=["POST"])
@admins_only
def save_settings():
    data = request.get_json() or request.form

    set_config("gchat_webhook_url", (data.get("webhook_url") or "").strip())
    set_config("gchat_prefix", (data.get("prefix") or "[CTFd]").strip())
    set_config("gchat_enabled", "true" if data.get("enabled") in (True, "true", "on", 1) else "false")
    set_config("gchat_notify_announcements", "true" if data.get("notify_announcements") in (True, "true", "on", 1) else "false")
    set_config("gchat_notify_new_challenges", "true" if data.get("notify_new_challenges") in (True, "true", "on", 1) else "false")
    set_config("gchat_notify_first_blood", "true" if data.get("notify_first_blood") in (True, "true", "on", 1) else "false")
    set_config("gchat_notify_all_solves", "true" if data.get("notify_all_solves") in (True, "true", "on", 1) else "false")
    set_config("gchat_notify_registrations", "true" if data.get("notify_registrations") in (True, "true", "on", 1) else "false")

    return jsonify({"success": True, "message": "Google Chat settings saved successfully!"})

@google_chat_bp.route("/admin/google_chat/test", methods=["POST"])
@admins_only
def trigger_test():
    data = request.get_json() or request.form
    url = (data.get("webhook_url") or get_config("gchat_webhook_url") or "").strip()
    if not url:
        return jsonify({"success": False, "message": "No Webhook URL provided"}), 400

    success, res = test_webhook(url)
    if success:
        return jsonify({"success": True, "message": "Test notification sent successfully to Google Chat!"})
    else:
        return jsonify({"success": False, "message": f"Failed to send webhook: {res}"}), 500
