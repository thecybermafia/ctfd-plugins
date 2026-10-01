import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from CTFd.utils.decorators import admins_only
from CTFd.plugins import (
    get_plugin_names,
    get_admin_plugin_menu_bar,
    register_admin_plugin_menu_bar,
)
from CTFd.plugins import get_disabled_plugins, set_disabled_plugins

plugin_manager_bp = Blueprint(
    "plugin_manager",
    __name__,
    template_folder="templates",
    static_folder="assets",
)

CORE_PLUGINS = {"challenges", "dynamic_challenges", "flags", "plugin_manager"}

PLUGIN_TITLES = {
    "bingo": "Bingo Challenges",
    "challenges": "Standard Challenges (Core)",
    "crossword": "Crossword Challenges",
    "dynamic_challenges": "Dynamic Value Challenges (Core)",
    "flags": "Flag Handlers (Core)",
    "chat_notifications": "Webhook Notifications",
    "cyber_wordle": "Wordle Challenges",
    "quiz_challenges": "Quiz Challenges",
    "image_upload": "Image Upload",
    "referrals": "Referrals",
    "sso": "Single Sign On (SSO)",
    "textarea": "Manual Verification",
    "url_anatomy": "URL Anatomy Analysis",
    "phishing_inbox": "Phishing Email Triage",
    "branching_scenario": "CEO Fraud Decision Simulator",
    "incident_sequence": "Incident Response Procedure",
    "red_flag_hotspot": "Spot the Phishing Red Flags",
    "world_theme": "World Theme Settings",
    "plugin_manager": "Plugin Manager (Core)",
}

SETTINGS_ROUTES = {
    "chat_notifications": "/admin/chat_notifications",
    "image_upload": "/admin/image_uploads",
    "referrals": "/admin/referrals",
    "textarea": "/admin/textarea_submissions",
    "sso": "/admin/sso",
    "world_theme": "/admin/theme_settings",
}


@plugin_manager_bp.route("/admin/plugins", methods=["GET"])
@admins_only
def admin_plugins():
    plugin_dirs = get_plugin_names()
    disabled = get_disabled_plugins()
    menu_items = get_admin_plugin_menu_bar()

    # Map menu bar routes to plugin names if possible
    dynamic_routes = {}
    for m in menu_items:
        clean_route = m.route.strip("/")
        parts = clean_route.split("/")
        if len(parts) >= 2:
            key = parts[1]
            dynamic_routes[key] = m.route

    plugins_list = []
    for name in plugin_dirs:
        is_core = name in CORE_PLUGINS
        is_enabled = name not in disabled

        settings_route = SETTINGS_ROUTES.get(name) or dynamic_routes.get(name)
        title = PLUGIN_TITLES.get(name, name.replace("_", " ").title())
        plugins_list.append({
            "name": name,
            "title": title,
            "is_core": is_core,
            "enabled": is_enabled,
            "settings_route": settings_route,
        })

    plugins_list.sort(key=lambda x: (not x["is_core"], x["title"].lower()))

    return render_template("admin/plugins.html", installed_plugins=plugins_list)


@plugin_manager_bp.route("/admin/plugins/toggle", methods=["POST"])
@admins_only
def admin_plugins_toggle():
    plugin_name = request.form.get("plugin_name")
    action = request.form.get("action")

    if not plugin_name:
        flash("Plugin name is required.", "danger")
        return redirect(url_for("plugin_manager.admin_plugins"))

    if plugin_name in CORE_PLUGINS:
        flash(f"Cannot modify core plugin '{plugin_name}'.", "danger")
        return redirect(url_for("plugin_manager.admin_plugins"))

    if plugin_name not in get_plugin_names():
        flash(f"Unrecognized plugin '{plugin_name}'.", "danger")
        return redirect(url_for("plugin_manager.admin_plugins"))

    disabled = set(get_disabled_plugins())

    if action == "disable":
        disabled.add(plugin_name)
        set_disabled_plugins(disabled)
        flash(f"Plugin '{plugin_name}' has been disabled. Restart CTFd to apply changes.", "warning")
    elif action == "enable":
        disabled.discard(plugin_name)
        set_disabled_plugins(disabled)
        flash(f"Plugin '{plugin_name}' has been enabled. Restart CTFd to apply changes.", "success")
    else:
        flash("Invalid action.", "danger")

    return redirect(url_for("plugin_manager.admin_plugins"))


def load(app):
    app.register_blueprint(plugin_manager_bp)
    register_admin_plugin_menu_bar(title="Plugins", route="/admin/plugins")
