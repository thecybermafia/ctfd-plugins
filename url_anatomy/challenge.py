import json
from CTFd.models import Fails, Solves, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.url_anatomy.models import UrlAnatomyChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def get_default_sample_urls():
    return [
        {
            "id": "url_1",
            "question": "Click on the actual registrable domain that will receive credentials:",
            "raw_url": "https://sso.microsoftonline.com.auth-adfs-portal.cc:8443/login?redirect=office",
            "tokens": [
                {"type": "scheme", "value": "https://"},
                {"type": "subdomain", "value": "sso.microsoftonline.com."},
                {"type": "domain", "value": "auth-adfs-portal.cc"},
                {"type": "port", "value": ":8443"},
                {"type": "path", "value": "/login"},
                {"type": "query", "value": "?redirect=office"}
            ],
            "correct_token": "auth-adfs-portal.cc",
            "explanation": "Subdomains can mimic legitimate brands (sso.microsoftonline.com), but the actual registrable domain before the port is 'auth-adfs-portal.cc'."
        },
        {
            "id": "url_2",
            "question": "Inspect this lookalike domain and identify the homoglyph spoofing PayPal:",
            "raw_url": "https://pаypal.com/signin",
            "punycode_url": "https://xn--pypal-4ve.com/signin",
            "tokens": [
                {"type": "scheme", "value": "https://"},
                {"type": "domain", "value": "pаypal.com", "punycode": "xn--pypal-4ve.com"},
                {"type": "path", "value": "/signin"}
            ],
            "correct_token": "pаypal.com",
            "explanation": "The Cyrillic character 'а' (U+0430) substitutes the Latin 'a', resulting in an IDN homograph attack resolving to xn--pypal-4ve.com."
        },
        {
            "id": "url_3",
            "question": "Click on the open redirection parameter forwarding the victim to an external server:",
            "raw_url": "https://portal.company.internal/oauth/callback?client_id=128&return_url=https://attacker-c2.net/payload",
            "tokens": [
                {"type": "scheme", "value": "https://"},
                {"type": "domain", "value": "portal.company.internal"},
                {"type": "path", "value": "/oauth/callback"},
                {"type": "param", "value": "?client_id=128"},
                {"type": "param", "value": "&return_url=https://attacker-c2.net/payload"}
            ],
            "correct_token": "&return_url=https://attacker-c2.net/payload",
            "explanation": "An unvalidated return_url parameter allows attackers to hijack post-authentication redirect to malicious infrastructure."
        }
    ]


class UrlAnatomyChallengeType(BaseChallenge):
    id = "url_anatomy"
    name = "url_anatomy"
    templates = {
        "create": "/plugins/url_anatomy/assets/create.html",
        "update": "/plugins/url_anatomy/assets/update.html",
        "view": "/plugins/url_anatomy/assets/view.html",
    }
    scripts = {
        "create": "/plugins/url_anatomy/assets/create.js",
        "update": "/plugins/url_anatomy/assets/update.js",
        "view": "/plugins/url_anatomy/assets/view.js",
    }
    route = "/plugins/url_anatomy/assets/"
    challenge_model = UrlAnatomyChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = UrlAnatomyChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return data

        user = get_current_user()
        team = get_current_team()

        is_solved = False
        attempts_used = 0
        if user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id
            is_solved = Solves.query.filter_by(**filter_kwargs).count() > 0
            attempts_used = Fails.query.filter_by(**filter_kwargs).count()

        raw_urls = c.urls_data
        sanitized_urls = []
        for item in raw_urls:
            u_entry = {
                "id": item.get("id"),
                "question": item.get("question", "Identify the deceptive or controlling URL segment:"),
                "raw_url": item.get("raw_url", ""),
                "punycode_url": item.get("punycode_url", ""),
                "tokens": item.get("tokens", []),
                "qr_target": item.get("qr_target", "") if c.enable_qr_code else "",
            }
            if is_solved or is_admin():
                u_entry["correct_token"] = item.get("correct_token", "")
                u_entry["explanation"] = item.get("explanation", "")

            sanitized_urls.append(u_entry)

        data.update({
            "urls_data": sanitized_urls,
            "enable_qr_code": bool(c.enable_qr_code),
            "allow_punycode_toggle": bool(c.allow_punycode_toggle),
            "is_solved": is_solved,
            "attempts_used": attempts_used,
            "explanation": c.explanation if (is_solved or is_admin()) else "",
        })

        if is_admin():
            data["urls_json"] = c.urls_json

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = UrlAnatomyChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.enable_qr_code = str(data.get("enable_qr_code", "false")).lower() in ("true", "1", "yes", "on")
            c.allow_punycode_toggle = str(data.get("allow_punycode_toggle", "true")).lower() in ("true", "1", "yes", "on")
            c.explanation = data.get("explanation", "").strip()

            urls_json_val = data.get("urls_json", "").strip()
            if not urls_json_val:
                urls_json_val = json.dumps(get_default_sample_urls(), indent=2)
            c.urls_json = urls_json_val
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        if "explanation" in data:
            challenge.explanation = data["explanation"].strip()

        if "enable_qr_code" in data:
            challenge.enable_qr_code = str(data["enable_qr_code"]).lower() in ("true", "1", "yes", "on")

        if "allow_punycode_toggle" in data:
            challenge.allow_punycode_toggle = str(data["allow_punycode_toggle"]).lower() in ("true", "1", "yes", "on")

        if "urls_json" in data:
            challenge.urls_json = data["urls_json"].strip()

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        c = UrlAnatomyChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Submission expected: {"url_1": "auth-adfs-portal.cc", "url_2": "pаypal.com"} or single token string
        user_picks = {}
        try:
            if submission.startswith("{") and submission.endswith("}"):
                user_picks = json.loads(submission)
            elif ":" in submission:
                for pair in submission.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        user_picks[k.strip()] = v.strip()
            else:
                # Single URL fallback: match first url
                urls = c.urls_data
                if urls:
                    user_picks[urls[0].get("id", "url_1")] = submission
        except Exception:
            return ChallengeResponse(status="incorrect", message="Invalid submission format.")

        urls = c.urls_data
        if not urls:
            return ChallengeResponse(status="correct", message="No URLs configured. Solved!")

        if len(user_picks) < len(urls):
            missing = len(urls) - len(user_picks)
            return ChallengeResponse(status="incorrect", message=f"You must select the target token for all URLs ({missing} remaining).")

        correct_count = 0
        total_count = len(urls)

        for u in urls:
            u_id = u.get("id")
            expected_token = (u.get("correct_token") or "").strip()
            chosen_token = str(user_picks.get(u_id, "")).strip()

            # Accept match on token value, or token punycode representation, or substring
            matched = False
            if chosen_token and expected_token and chosen_token.lower() == expected_token.lower():
                matched = True
            elif u.get("punycode_url") and chosen_token.lower() in u.get("punycode_url").lower():
                matched = True
            elif chosen_token and expected_token in chosen_token:
                matched = True

            if matched:
                correct_count += 1

        if correct_count == total_count:
            return ChallengeResponse(
                status="correct",
                message=f"URL Anatomy Dissection Successful! All {total_count} suspicious segments correctly identified."
            )
        else:
            return ChallengeResponse(
                status="incorrect",
                message=f"Analysis incomplete: {correct_count} of {total_count} segments identified correctly."
            )
