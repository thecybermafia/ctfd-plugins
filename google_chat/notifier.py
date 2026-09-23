import json
import logging
import threading
import urllib.request
from urllib.parse import urlparse
from CTFd.utils import get_config

logger = logging.getLogger("google_chat_notifier")

# Only allow delivery to Google Chat's webhook host to mitigate SSRF via the
# admin-configurable webhook URL.
ALLOWED_WEBHOOK_HOSTS = {"chat.googleapis.com"}

def _is_allowed_webhook(url):
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_WEBHOOK_HOSTS

def _send_payload(url, payload):
    if not _is_allowed_webhook(url):
        logger.warning("Refusing to deliver Google Chat webhook to disallowed host")
        return False, "Webhook URL must be an https://chat.googleapis.com address"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            logger.info(f"Google Chat response: {response.status}")
            return True, res_body
    except Exception as e:
        logger.warning(f"Failed to deliver Google Chat webhook: {e}")
        return False, str(e)

def dispatch_async(text, card_title=None, card_sections=None):
    webhook_url = get_config("gchat_webhook_url")
    if not webhook_url or get_config("gchat_enabled", "true") != "true":
        return

    prefix = get_config("gchat_prefix", "[CTFd]")
    full_text = f"*{prefix}* {text}" if prefix else text

    payload = {"text": full_text}

    if card_title and card_sections:
        payload["cardsV2"] = [
            {
                "cardId": "ctfd-notification-card",
                "card": {
                    "header": {
                        "title": prefix if prefix else "CTFd",
                        "subtitle": card_title,
                        "imageUrl": "https://raw.githubusercontent.com/CTFd/CTFd/master/CTFd/themes/core/assets/img/logo.png",
                        "imageType": "CIRCLE"
                    },
                    "sections": card_sections
                }
            }
        ]

    # Run in detached daemon thread so CTFd requests are never blocked
    thread = threading.Thread(target=_send_payload, args=(webhook_url, payload), daemon=True)
    thread.start()

def test_webhook(url):
    """Synchronous test message function for admin testing"""
    prefix = get_config("gchat_prefix", "[CTFd]")
    payload = {
        "text": f"*{prefix} Google Chat Integration Active!*\nThis is a test notification confirming your CTFd webhook is operational."
    }
    return _send_payload(url, payload)

def notify_announcement(notif):
    if get_config("gchat_notify_announcements", "true") != "true":
        return

    title = notif.title or "Platform Announcement"
    content = notif.content or ""
    text = f"*Announcement: {title}*\n{content}"

    sections = [
        {
            "header": title,
            "widgets": [
                {"textParagraph": {"text": content}}
            ]
        }
    ]
    dispatch_async(text, card_title="Platform Announcement", card_sections=sections)

def notify_new_challenge(chal):
    if get_config("gchat_notify_new_challenges", "true") != "true":
        return

    name = chal.name or "Unknown"
    category = chal.category or "General"
    value = chal.value or 0

    text = f"*New Challenge Live:* *{name}* ({category} - {value} pts)\nA new challenge has just been unlocked on the grid!"
    sections = [
        {
            "header": "New Challenge Unlocked",
            "widgets": [
                {
                    "decoratedText": {
                        "topLabel": f"Category: {category}",
                        "text": f"<b>{name}</b> ({value} PTS)",
                        "bottomLabel": "Now accessible to all participants"
                    }
                }
            ]
        }
    ]
    dispatch_async(text, card_title="Challenge Release", card_sections=sections)

def notify_first_blood(chal, solver_name):
    if get_config("gchat_notify_first_blood", "true") != "true":
        return

    name = chal.name if chal else "Unknown"
    category = chal.category if chal else "General"
    value = chal.value if chal else 0

    text = f"*FIRST BLOOD!* *{solver_name}* secured first blood on *{name}* ({category} - {value} pts)!"
    sections = [
        {
            "header": "First Blood Secured",
            "widgets": [
                {
                    "decoratedText": {
                        "topLabel": f"{category} | {value} PTS",
                        "text": f"<b>{solver_name}</b> solved <b>{name}</b>",
                        "bottomLabel": "First participant to capture this flag!"
                    }
                }
            ]
        }
    ]
    dispatch_async(text, card_title="First Blood", card_sections=sections)

def notify_solve(chal, solver_name):
    if get_config("gchat_notify_all_solves", "false") != "true":
        return

    name = chal.name if chal else "Unknown"
    text = f"*Challenge Solved:* *{solver_name}* completed *{name}*!"
    dispatch_async(text)

def notify_registration(name, is_team=False):
    if get_config("gchat_notify_registrations", "false") != "true":
        return

    kind = "Team" if is_team else "User"
    text = f"*New Registration:* {kind} *{name}* has joined the competition."
    dispatch_async(text)
