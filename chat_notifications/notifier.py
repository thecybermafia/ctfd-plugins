import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import threading
import time
import urllib.parse
import urllib.request
from urllib.parse import urlparse
from CTFd.utils import get_config

logger = logging.getLogger("chat_notifications_notifier")

def get_shared_secret():
    """Retrieve or generate the HMAC-SHA256 shared secret for CTFd webhooks."""
    secret = get_config("chat_notifications_shared_secret") or get_config("webhooks_shared_secret")
    if not secret:
        secret = secrets.token_hex(32)
        try:
            from CTFd.utils import set_config
            set_config("chat_notifications_shared_secret", secret)
            set_config("webhooks_shared_secret", secret)
        except Exception:
            pass
    return secret

# Color constants (decimal for Discord, hex for Teams/Slack)
COLORS = {
    "first_blood": {"dec": 0xFFD700, "hex": "FFD700"},      # Gold
    "solve": {"dec": 0x00FF41, "hex": "00FF41"},            # Matrix Green
    "challenge": {"dec": 0x00E5FF, "hex": "00E5FF"},        # Cyan
    "announcement": {"dec": 0x9B59B6, "hex": "9B59B6"},   # Purple
    "admin_alert": {"dec": 0xF39C12, "hex": "F39C12"},     # Amber
    "admin_review": {"dec": 0xE74C3C, "hex": "E74C3C"},    # Red
    "registration": {"dec": 0x3498DB, "hex": "3498DB"},    # Blue
    "info": {"dec": 0x2ECC71, "hex": "2ECC71"}             # Emerald
}

def is_allowed_webhook_url(url):
    """Validate webhook URL and mitigate SSRF to private/internal networks."""
    if not url:
        return False, "Webhook URL cannot be empty"
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "Webhook URL scheme must be http or https"
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL hostname"

        # Check for loopback / private IP
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Delivery to private/loopback IP ({hostname}) is restricted for security"
        except ValueError:
            if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
                return False, "Delivery to localhost is restricted for security"

        return True, ""
    except Exception as e:
        return False, str(e)

def detect_platform(url):
    """Auto-detect target chat platform from webhook URL hostname."""
    if not url:
        return "generic"
    url_lower = url.lower()
    if "discord.com" in url_lower or "discordapp.com" in url_lower:
        return "discord"
    if "hooks.slack.com" in url_lower:
        return "slack"
    if "chat.googleapis.com" in url_lower:
        return "google_chat"
    if "office.com" in url_lower or "office365.com" in url_lower or "logic.azure.com" in url_lower:
        return "teams"
    if "api.telegram.org" in url_lower:
        return "telegram"
    return "generic"

def format_payload(platform, prefix, text, card_title=None, fields=None, color_key="info", chat_id=None):
    """Format webhook payload customized for the destination chat platform."""
    color_info = COLORS.get(color_key, COLORS["info"])
    color_dec = color_info["dec"]
    color_hex = color_info["hex"]
    full_title = f"{prefix} {card_title}".strip() if prefix and card_title else (card_title or prefix or "CTFd")

    if platform == "discord":
        embed = {
            "title": full_title[:256],
            "description": text[:2048],
            "color": color_dec,
            "footer": {"text": "CTFd Intelligence Platform"}
        }
        if fields:
            embed["fields"] = [
                {"name": f["name"][:256], "value": f["value"][:1024], "inline": f.get("inline", True)}
                for f in fields[:25]
            ]
        return {
            "username": prefix.strip("[] ") if prefix else "CTFd",
            "embeds": [embed]
        }

    elif platform in ("slack", "mattermost"):
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": full_title[:150], "emoji": False}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            }
        ]
        if fields:
            field_elements = [
                {"type": "mrkdwn", "text": f"*{f['name']}:*\n{f['value']}"}
                for f in fields[:10]
            ]
            blocks.append({"type": "section", "fields": field_elements})

        return {
            "text": f"*{prefix}* {text}" if prefix else text,
            "blocks": blocks
        }

    elif platform == "teams":
        # Office 365 MessageCard format supported natively by Teams connectors & Power Automate
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color_hex,
            "summary": full_title,
            "title": full_title,
            "text": text
        }
        if fields:
            card["sections"] = [{
                "facts": [{"name": f["name"], "value": f["value"]} for f in fields]
            }]
        return card

    elif platform == "google_chat":
        payload = {"text": f"*{prefix}* {text}" if prefix else text}
        if card_title or fields:
            sections = []
            widgets = []
            if text:
                widgets.append({"textParagraph": {"text": text}})
            if fields:
                for f in fields:
                    widgets.append({
                        "decoratedText": {
                            "topLabel": f["name"],
                            "text": f"<b>{f['value']}</b>"
                        }
                    })
            sections.append({
                "header": card_title or prefix or "CTFd Event",
                "widgets": widgets
            })
            payload["cardsV2"] = [{
                "cardId": "ctfd-notification-card",
                "card": {
                    "header": {
                        "title": prefix if prefix else "CTFd",
                        "subtitle": card_title or "Platform Update",
                        "imageUrl": "https://raw.githubusercontent.com/CTFd/CTFd/master/CTFd/themes/core/assets/img/logo.png",
                        "imageType": "CIRCLE"
                    },
                    "sections": sections
                }
            }]
        return payload

    elif platform == "telegram":
        tg_text = f"<b>{full_title}</b>\n\n{text}"
        if fields:
            tg_text += "\n\n" + "\n".join(f"• <b>{f['name']}:</b> {f['value']}" for f in fields)
        return {
            "chat_id": chat_id,
            "text": tg_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

    else:
        # Generic Custom Webhook
        return {
            "event": color_key,
            "prefix": prefix,
            "title": card_title,
            "message": text,
            "fields": fields or [],
            "timestamp": int(time.time())
        }

def _send_payload(url, payload, event_type="notification"):
    valid, err = is_allowed_webhook_url(url)
    if not valid:
        logger.warning(f"Refusing webhook delivery: {err}")
        return False, err

    try:
        data = json.dumps(payload).encode("utf-8")
        timestamp = str(int(time.time()))
        secret = get_shared_secret()
        sig_input = f"{timestamp}.{data.decode('utf-8')}"
        signature = hmac.new(secret.encode("utf-8"), sig_input.encode("utf-8"), hashlib.sha256).hexdigest()

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "CTFd-Webhook",
                "Ctfd-Webhook-Event": event_type,
                "Ctfd-Webhook-Signature": f"t={timestamp},v1={signature}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_body = response.read().decode("utf-8")
            logger.info(f"Webhook dispatch response status: {response.status}")
            return True, res_body
    except Exception as e:
        logger.warning(f"Failed to deliver webhook to {url}: {e}")
        return False, str(e)

def _dispatch_to_channel(url, platform_config, prefix, enabled, text, card_title=None, fields=None, color_key="info", chat_id=None, event_type="notification"):
    if not url or not enabled:
        return

    platform = platform_config if platform_config and platform_config != "auto" else detect_platform(url)
    payload = format_payload(platform, prefix, text, card_title, fields, color_key, chat_id)

    thread = threading.Thread(target=_send_payload, args=(url, payload, event_type), daemon=True)
    thread.start()

SUPPORTED_PLATFORMS = ["discord", "slack", "teams", "google_chat", "telegram", "custom"]

def dispatch_participant(text, card_title=None, fields=None, color_key="info", event_type="notification"):
    dispatched_urls = set()

    for p in SUPPORTED_PLATFORMS:
        url = (get_config(f"webhook_{p}_participant_url") or "").strip()
        enabled = (get_config(f"webhook_{p}_participant_enabled") or "false") == "true"
        prefix = get_config(f"webhook_{p}_participant_prefix") or "[CTFd]"
        chat_id = get_config("webhook_telegram_participant_chat_id") if p == "telegram" else None
        platform_name = "generic" if p == "custom" else p
        if url and enabled:
            _dispatch_to_channel(url, platform_name, prefix, True, text, card_title, fields, color_key, chat_id, event_type=event_type)
            dispatched_urls.add(url)

    # Legacy fallback for backwards compatibility
    legacy_url = (
        get_config("chat_notifications_webhook_url") or
        get_config("gchat_participant_webhook_url") or
        get_config("gchat_webhook_url") or ""
    ).strip()
    legacy_enabled = (
        get_config("chat_notifications_enabled") or
        get_config("gchat_enabled", "true")
    ) == "true"
    if legacy_url and legacy_enabled and legacy_url not in dispatched_urls:
        legacy_prefix = get_config("chat_notifications_prefix") or "[CTFd]"
        legacy_plat = get_config("chat_notifications_platform", "auto")
        legacy_tg = get_config("chat_notifications_telegram_chat_id")
        _dispatch_to_channel(legacy_url, legacy_plat, legacy_prefix, True, text, card_title, fields, color_key, legacy_tg, event_type=event_type)

def dispatch_admin(text, card_title=None, fields=None, color_key="admin_alert", event_type="notification"):
    dispatched_urls = set()

    for p in SUPPORTED_PLATFORMS:
        url = (get_config(f"webhook_{p}_admin_url") or "").strip()
        enabled = (get_config(f"webhook_{p}_admin_enabled") or "false") == "true"
        prefix = get_config(f"webhook_{p}_admin_prefix") or "[CTFd-Admin]"
        chat_id = get_config("webhook_telegram_admin_chat_id") if p == "telegram" else None
        platform_name = "generic" if p == "custom" else p
        if url and enabled:
            _dispatch_to_channel(url, platform_name, prefix, True, text, card_title, fields, color_key, chat_id, event_type=event_type)
            dispatched_urls.add(url)

    # Legacy fallback for backwards compatibility
    legacy_url = (
        get_config("chat_notifications_admin_webhook_url") or
        get_config("gchat_admin_webhook_url") or ""
    ).strip()
    legacy_enabled = (
        get_config("chat_notifications_admin_enabled") or
        get_config("gchat_admin_enabled", "true")
    ) == "true"
    if legacy_url and legacy_enabled and legacy_url not in dispatched_urls:
        legacy_prefix = get_config("chat_notifications_admin_prefix") or "[CTFd-Admin]"
        legacy_plat = get_config("chat_notifications_admin_platform", "auto")
        legacy_tg = get_config("chat_notifications_admin_telegram_chat_id")
        _dispatch_to_channel(legacy_url, legacy_plat, legacy_prefix, True, text, card_title, fields, color_key, legacy_tg, event_type=event_type)

def dispatch_async(text, card_title=None, fields=None, color_key="info", channel="participant", event_type="notification"):
    if channel in ("participant", "both"):
        dispatch_participant(text, card_title, fields, color_key, event_type=event_type)
        # Mirror to admin ops if requested
        mirror = (
            get_config("chat_notifications_mirror_participant_events") or
            get_config("gchat_mirror_participant_events", "false")
        ) == "true"
        if channel == "participant" and mirror:
            dispatch_admin(text, card_title, fields, color_key, event_type=event_type)

    if channel in ("admin", "both") and channel != "participant":
        dispatch_admin(text, card_title, fields, color_key, event_type=event_type)

def validate_endpoint_ownership(url):
    """Validate endpoint ownership using official CTFd GET token HMAC challenge."""
    valid, err = is_allowed_webhook_url(url)
    if not valid:
        return False, f"Validation failed: {err}"

    token = secrets.token_hex(8)
    secret = get_shared_secret()
    expected_sig = hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()

    separator = "&" if "?" in url else "?"
    test_url = f"{url}{separator}token={token}"

    req = urllib.request.Request(
        test_url,
        headers={
            "User-Agent": "CTFd-Webhook",
            "Accept": "application/json"
        },
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status != 200:
                return False, f"Endpoint returned HTTP status {response.status} (expected 200 OK)"
            body = response.read().decode("utf-8")
            try:
                data = json.loads(body)
                received_sig = data.get("response")
                if received_sig == expected_sig:
                    return True, "Endpoint ownership successfully validated! Token HMAC-SHA256 signature verified."
                else:
                    return False, f"Invalid HMAC returned by endpoint. Expected: {expected_sig[:12]}..., Got: {str(received_sig)[:12]}..."
            except json.JSONDecodeError:
                return False, "Endpoint response was not valid JSON. Expected format: {\"response\": \"<hmac_sha256>\"}"
    except Exception as e:
        return False, f"Failed to connect to endpoint: {str(e)}"

def test_webhook(url, platform="auto", prefix="[CTFd]", channel_label="Channel", chat_id=None):
    """Synchronous test webhook function for admin UI testing."""
    if not url:
        return False, f"No Webhook URL provided for {channel_label}"

    resolved_platform = platform if platform and platform != "auto" else detect_platform(url)
    test_text = f"Connection Verified: This test notification confirms that your {channel_label} webhook ({resolved_platform.replace('_', ' ').title()}) is operational."
    test_fields = [
        {"name": "Status", "value": "ONLINE", "inline": True},
        {"name": "Platform", "value": resolved_platform.upper(), "inline": True},
        {"name": "Security Signature", "value": "HMAC-SHA256", "inline": True}
    ]

    payload = format_payload(
        resolved_platform,
        prefix,
        test_text,
        card_title=f"{channel_label} Connected",
        fields=test_fields,
        color_key="solve",
        chat_id=chat_id
    )
    return _send_payload(url, payload, event_type="test.notification")

# ---------------------------------------------------------------------------
# Event Dispatchers (Announcements, Solves, First Bloods, Registrations, etc.)
# ---------------------------------------------------------------------------

def notify_announcement(notif):
    ann_enabled = (
        get_config("chat_notifications_notify_announcements") or
        get_config("gchat_notify_announcements", "true")
    ) == "true"
    if not ann_enabled:
        return

    title = notif.title or "Platform Announcement"
    content = notif.content or ""
    text = f"**Announcement:** {title}\n{content}"
    fields = [{"name": "Subject", "value": title, "inline": False}]
    dispatch_async(text, card_title="Platform Announcement", fields=fields, color_key="announcement", channel="participant", event_type="announcement.created")

def notify_new_challenge(chal):
    chal_enabled = (
        get_config("chat_notifications_notify_new_challenges") or
        get_config("gchat_notify_new_challenges", "true")
    ) == "true"
    if not chal_enabled:
        return

    name = chal.name or "Unknown"
    category = chal.category or "General"
    value = chal.value or 0
    text = f"**New Challenge Live:** **{name}** ({category} - {value} PTS) has been unlocked!"
    fields = [
        {"name": "Category", "value": category, "inline": True},
        {"name": "Value", "value": f"{value} PTS", "inline": True}
    ]
    dispatch_async(text, card_title="New Challenge Released", fields=fields, color_key="challenge", channel="participant", event_type="challenge.created")

def notify_first_blood(chal, solver_name):
    fb_enabled = (
        get_config("chat_notifications_notify_first_blood") or
        get_config("gchat_notify_first_blood", "true")
    ) == "true"
    if not fb_enabled:
        return

    name = chal.name if chal else "Unknown"
    category = chal.category if chal else "General"
    value = chal.value if chal else 0
    text = f"**FIRST BLOOD!** **{solver_name}** captured first blood on **{name}** ({category} - {value} PTS)!"
    fields = [
        {"name": "Operative", "value": solver_name, "inline": True},
        {"name": "Challenge", "value": name, "inline": True},
        {"name": "Category / Value", "value": f"{category} ({value} PTS)", "inline": True}
    ]
    dispatch_async(text, card_title="FIRST BLOOD SECURED", fields=fields, color_key="first_blood", channel="participant", event_type="challenge.first_blood")

def notify_solve(chal, solver_name):
    solve_enabled = (
        get_config("chat_notifications_notify_all_solves") or
        get_config("gchat_notify_all_solves", "false")
    ) == "true"
    if not solve_enabled:
        return

    name = chal.name if chal else "Unknown"
    text = f"**Challenge Solved:** **{solver_name}** solved **{name}**!"
    fields = [
        {"name": "Operative", "value": solver_name, "inline": True},
        {"name": "Target", "value": name, "inline": True}
    ]
    dispatch_async(text, card_title="Challenge Solved", fields=fields, color_key="solve", channel="participant", event_type="challenge.solved")

def notify_registration(name, is_team=False):
    kind = "Team" if is_team else "User"
    event_type = f"{kind.lower()}.created"
    text = f"**New Registration:** {kind} **{name}** joined the competition."

    admin_reg = (
        get_config("chat_notifications_admin_notify_registrations") or
        get_config("gchat_admin_notify_registrations", "true")
    ) == "true"
    if admin_reg:
        dispatch_admin(text, card_title=f"New {kind} Registered", color_key="registration", event_type=event_type)

    pub_reg = (
        get_config("chat_notifications_notify_registrations") or
        get_config("gchat_notify_registrations", "false")
    ) == "true"
    if pub_reg:
        dispatch_participant(text, card_title=f"New {kind} Enrolled", color_key="registration", event_type=event_type)

def notify_admin_submission(chal, submitter_name, submission_type="Challenge Review", details=""):
    """Alert internal admin ops channel when a challenge submission requires manual review."""
    admin_sub = (
        get_config("chat_notifications_admin_notify_submissions") or
        get_config("gchat_admin_notify_submissions", "true")
    ) == "true"
    if not admin_sub:
        return

    chal_name = chal.name if chal else "Unknown Challenge"
    category = chal.category if chal else "Manual Review"
    pts = chal.value if chal else 0

    text = f"**Manual Review Pending:** **{submitter_name}** submitted a **{submission_type}** for **{chal_name}** ({pts} PTS)."
    fields = [
        {"name": "Operative", "value": submitter_name, "inline": True},
        {"name": "Challenge", "value": chal_name, "inline": True},
        {"name": "Review Type", "value": submission_type, "inline": True}
    ]
    if details:
        fields.append({"name": "Details", "value": details[:300], "inline": False})

    dispatch_admin(text, card_title=f"Pending {submission_type}", fields=fields, color_key="admin_review", event_type="submission.review")

def notify_admin_referral(referrer_name, recruit_name, status_msg):
    """Alert internal admin ops channel on referral milestone or anti-cheat trigger."""
    admin_ref = (
        get_config("chat_notifications_admin_notify_referrals") or
        get_config("gchat_admin_notify_referrals", "true")
    ) == "true"
    if not admin_ref:
        return

    text = f"**Referral Telemetry:** **{referrer_name}** &rarr; Recruit: **{recruit_name}** ({status_msg})"
    fields = [
        {"name": "Referrer", "value": referrer_name, "inline": True},
        {"name": "Recruit", "value": recruit_name, "inline": True},
        {"name": "Telemetry Status", "value": status_msg, "inline": False}
    ]
    dispatch_admin(text, card_title="Referral Activity Alert", fields=fields, color_key="admin_alert", event_type="referral.alert")
