import json
from urllib.parse import urlparse
from CTFd.models import Fails, Flags, Solves, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.url_anatomy.models import UrlAnatomyChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def auto_tokenize_url(raw_url):
    """
    Parses a raw URL into RFC 3986 tokens automatically without requiring manual JSON.
    """
    raw_url = (raw_url or "").strip()
    if not raw_url:
        return []
    parsed = urlparse(raw_url)
    tokens = []
    if parsed.scheme:
        tokens.append({"type": "scheme", "value": f"{parsed.scheme}://"})

    netloc = parsed.netloc
    port = ""
    host = netloc
    if ":" in netloc:
        parts = netloc.split(":")
        host = parts[0]
        port = f":{parts[1]}"

    host_parts = host.split(".")
    if len(host_parts) > 2:
        domain = ".".join(host_parts[-2:])
        subdomain = ".".join(host_parts[:-2]) + "."
        tokens.append({"type": "subdomain", "value": subdomain})
        tokens.append({"type": "domain", "value": domain})
    else:
        tokens.append({"type": "domain", "value": host})

    if port:
        tokens.append({"type": "port", "value": port})

    if parsed.path and parsed.path != "/":
        tokens.append({"type": "path", "value": parsed.path})
    elif parsed.path == "/":
        tokens.append({"type": "path", "value": "/"})

    if parsed.query:
        q_parts = parsed.query.split("&")
        for i, q in enumerate(q_parts):
            prefix = "?" if i == 0 else "&"
            tokens.append({"type": "param", "value": f"{prefix}{q}"})

    if parsed.fragment:
        tokens.append({"type": "fragment", "value": f"#{parsed.fragment}"})

    return tokens


def parse_simple_urls_text(text):
    """
    Parses simple lines:
    URL | Question | Correct Segment | Explanation
    """
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    items = []
    for idx, line in enumerate(lines):
        parts = [p.strip() for p in line.split("|")]
        raw_url = parts[0] if len(parts) > 0 else ""
        if not raw_url:
            continue
        question = parts[1] if len(parts) > 1 else "Identify the deceptive or controlling URL segment:"
        correct_token = parts[2] if len(parts) > 2 else ""
        explanation = parts[3] if len(parts) > 3 else ""

        tokens = auto_tokenize_url(raw_url)
        if not correct_token:
            for t in tokens:
                if t["type"] == "domain":
                    correct_token = t["value"]
                    break

        items.append({
            "id": f"url_{idx+1}",
            "question": question,
            "raw_url": raw_url,
            "tokens": tokens,
            "correct_token": correct_token,
            "explanation": explanation
        })
    return items


def urls_to_simple_text(urls_json):
    try:
        urls = json.loads(urls_json or "[]")
        lines = []
        for u in urls:
            lines.append(f"{u.get('raw_url', '')} | {u.get('question', '')} | {u.get('correct_token', '')} | {u.get('explanation', '')}")
        return "\n".join(lines)
    except Exception:
        return ""


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
            raw_url = item.get("raw_url") or item.get("url") or ""
            tokens = item.get("tokens")
            if not tokens and raw_url:
                tokens = auto_tokenize_url(raw_url)

            u_entry = {
                "id": item.get("id"),
                "question": item.get("question", "Identify the deceptive or controlling URL segment:"),
                "raw_url": raw_url,
                "punycode_url": item.get("punycode_url", ""),
                "tokens": tokens or [],
                "qr_target": item.get("qr_target", "") if c.enable_qr_code else "",
            }
            if is_solved:
                u_entry["correct_token"] = item.get("correct_token", "")
                u_entry["explanation"] = item.get("explanation", "")

            sanitized_urls.append(u_entry)

        data.update({
            "urls_data": sanitized_urls,
            "enable_qr_code": bool(c.enable_qr_code),
            "allow_punycode_toggle": bool(c.allow_punycode_toggle),
            "is_solved": is_solved,
            "attempts_used": attempts_used,
            "explanation": c.explanation if is_solved else "",
        })

        if is_admin():
            data["urls_json"] = c.urls_json
            data["urls_text"] = urls_to_simple_text(c.urls_json)

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

            urls_text = (data.get("urls_text") or "").strip()
            urls_json_val = (data.get("urls_json") or "").strip()
            if urls_text:
                parsed_items = parse_simple_urls_text(urls_text)
                c.urls_json = json.dumps(parsed_items, indent=2)
            elif urls_json_val:
                c.urls_json = urls_json_val
            else:
                c.urls_json = json.dumps(get_default_sample_urls(), indent=2)
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

        if "urls_text" in data and data["urls_text"].strip():
            parsed_items = parse_simple_urls_text(data["urls_text"])
            challenge.urls_json = json.dumps(parsed_items, indent=2)
        elif "urls_json" in data:
            challenge.urls_json = data["urls_json"].strip()

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        c = UrlAnatomyChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Check standard Flags
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="URL Anatomy Dissection Successful via Flag!")
            except Exception:
                pass

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
