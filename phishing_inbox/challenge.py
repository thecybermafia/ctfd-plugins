import json
from CTFd.models import Fails, Flags, Solves, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.phishing_inbox.models import PhishingInboxChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def get_default_sample_emails():
    return [
        {
            "id": "email_1",
            "subject": "Action Required: Re-authenticate Microsoft 365 Account",
            "sender_name": "Microsoft Identity Security",
            "sender_email": "security-update@micros0ft-support.com",
            "reply_to": "collector@credential-drop.net",
            "date": "Today, 09:15 AM",
            "auth_results": {
                "spf": "FAIL",
                "dkim": "FAIL",
                "dmarc": "FAIL"
            },
            "body_html": "<p>Dear User,</p><p>Your Microsoft 365 multi-factor authentication token has expired. Failure to re-verify within 24 hours will suspend your enterprise account access.</p><p><span class='inbox-safe-link' data-real-url='https://login.micros0ft-support.com.attacker-server.biz/token'>Click here to re-authenticate immediately</span></p><p>Regards,<br>IT Identity Services</p>",
            "attachments": [
                {"name": "Security_Notice_Token.pdf.exe", "size": "1.4 MB", "type": "executable"}
            ],
            "correct_action": "report",
            "explanation": "High-risk indicators: lookalike sender domain (@micros0ft-support.com), failed SPF/DKIM/DMARC authentication, malicious reply-to address, executable double-extension attachment (.pdf.exe), and deceptive destination URL."
        },
        {
            "id": "email_2",
            "subject": "Monthly Cybersecurity Newsletter & Security Best Practices",
            "sender_name": "Corporate Infosec Team",
            "sender_email": "infosec@company.internal",
            "reply_to": "infosec@company.internal",
            "date": "Yesterday, 02:30 PM",
            "auth_results": {
                "spf": "PASS",
                "dkim": "PASS",
                "dmarc": "PASS"
            },
            "body_html": "<p>Hello Team,</p><p>Welcome to this month's internal Infosec briefing. Please review the updated secure remote work guidelines on the company intranet.</p><p><span class='inbox-safe-link' data-real-url='https://intranet.company.internal/security/monthly-update'>View Infosec Portal</span></p><p>Stay vigilant,<br>Internal Security Operations</p>",
            "attachments": [
                {"name": "Monthly_Digest_2026.pdf", "size": "650 KB", "type": "pdf"}
            ],
            "correct_action": "safe",
            "explanation": "Legitimate internal communication: valid company internal domain, passing SPF/DKIM/DMARC authentication, internal intranet link, and standard PDF attachment."
        },
        {
            "id": "email_3",
            "subject": "Overdue Invoice #INV-98214 - Wire Transfer Pending",
            "sender_name": "Accounts Receivable - TechSupplies Ltd",
            "sender_email": "billing@techsupplies-invoicing-portal.cc",
            "reply_to": "finance-mule@offshore-pay.ru",
            "date": "Today, 10:45 AM",
            "auth_results": {
                "spf": "FAIL",
                "dkim": "FAIL",
                "dmarc": "FAIL"
            },
            "body_html": "<p>Please find attached our overdue payment invoice. Failure to disburse funds by end of day will trigger legal collections.</p><p><span class='inbox-safe-link' data-real-url='https://invoice-viewer.techsupplies-invoicing-portal.cc.stolen-creds.co/pay'>Review Invoice Online</span></p>",
            "attachments": [
                {"name": "Invoice_98214.xlsm", "size": "2.1 MB", "type": "macro"}
            ],
            "correct_action": "report",
            "explanation": "Phishing financial scam: aggressive collection tone, suspicious .cc and .ru domains, macro-enabled Excel sheet (.xlsm), and spoofed vendor identity."
        }
    ]


class PhishingInboxChallengeType(BaseChallenge):
    id = "phishing_inbox"
    name = "phishing_inbox"
    templates = {
        "create": "/plugins/phishing_inbox/assets/create.html",
        "update": "/plugins/phishing_inbox/assets/update.html",
        "view": "/plugins/phishing_inbox/assets/view.html",
    }
    scripts = {
        "create": "/plugins/phishing_inbox/assets/create.js",
        "update": "/plugins/phishing_inbox/assets/update.js",
        "view": "/plugins/phishing_inbox/assets/view.js",
    }
    route = "/plugins/phishing_inbox/assets/"
    challenge_model = PhishingInboxChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = PhishingInboxChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return data

        user = get_current_user()
        team = get_current_team()

        # Check if challenge is solved by this user or team
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

        # Sanitize emails for participant view if not yet solved and not admin
        raw_emails = c.emails_data
        sanitized_emails = []
        for em in raw_emails:
            item = {
                "id": em.get("id"),
                "subject": em.get("subject", "No Subject"),
                "sender_name": em.get("sender_name", ""),
                "sender_email": em.get("sender_email", ""),
                "reply_to": em.get("reply_to", ""),
                "date": em.get("date", ""),
                "body_html": em.get("body_html", ""),
                "attachments": em.get("attachments", []),
            }
            if c.show_auth_headers:
                item["auth_results"] = em.get("auth_results", {})

            # Only reveal solution details if already solved or admin
            if is_solved or is_admin():
                item["correct_action"] = em.get("correct_action", "")
                item["explanation"] = em.get("explanation", "")

            sanitized_emails.append(item)

        data.update({
            "emails_data": sanitized_emails,
            "action_options": c.action_options or "report,safe,delete",
            "min_accuracy_percent": c.min_accuracy_percent or 100,
            "show_auth_headers": bool(c.show_auth_headers),
            "max_attempts": c.max_attempts or 0,
            "attempts_used": attempts_used,
            "is_solved": is_solved,
            "explanation": c.explanation if (is_solved or is_admin()) else "",
        })

        if is_admin():
            data["emails_json"] = c.emails_json

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = PhishingInboxChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.action_options = data.get("action_options", "report,safe,delete")
            c.min_accuracy_percent = int(data.get("min_accuracy_percent", 100) or 100)
            c.show_auth_headers = str(data.get("show_auth_headers", "true")).lower() in ("true", "1", "yes", "on")
            c.max_attempts = int(data.get("max_attempts", 0) or 0)
            c.explanation = data.get("explanation", "")

            emails_json_val = data.get("emails_json", "").strip()
            if not emails_json_val:
                emails_json_val = json.dumps(get_default_sample_emails(), indent=2)
            c.emails_json = emails_json_val
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        for attr in ("action_options", "explanation"):
            if attr in data:
                setattr(challenge, attr, data[attr])

        for attr in ("min_accuracy_percent", "max_attempts"):
            if attr in data:
                setattr(challenge, attr, int(data[attr] or 0))

        if "show_auth_headers" in data:
            val = str(data["show_auth_headers"]).lower() in ("true", "1", "yes", "on")
            setattr(challenge, "show_auth_headers", val)

        if "emails_json" in data:
            challenge.emails_json = data["emails_json"]

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        user = get_current_user()
        team = get_current_team()

        c = PhishingInboxChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Check standard Flags
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="Inbox Analysis Verified via Flag!")
            except Exception:
                pass

        # Check attempt limits
        if c.max_attempts and c.max_attempts > 0 and user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id

            used = Fails.query.filter_by(**filter_kwargs).count()
            if used >= c.max_attempts:
                return ChallengeResponse(
                    status="incorrect",
                    message=f"Maximum allowed attempts ({c.max_attempts}) reached for this challenge."
                )

        # Parse user submission: expected {"email_1": "report", "email_2": "safe", ...}
        user_actions = {}
        try:
            if submission.startswith("{") and submission.endswith("}"):
                user_actions = json.loads(submission)
            elif ":" in submission:
                for pair in submission.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        user_actions[k.strip()] = v.strip().lower()
        except Exception:
            return ChallengeResponse(status="incorrect", message="Invalid submission format. Complete reviewing all messages.")

        emails = c.emails_data
        if not emails:
            return ChallengeResponse(status="correct", message="Simulation complete!")

        # Verify that all emails have been reviewed
        if len(user_actions) < len(emails):
            missing = len(emails) - len(user_actions)
            return ChallengeResponse(status="incorrect", message=f"You must review and classify all emails. {missing} remaining.")

        correct_count = 0
        total_count = len(emails)
        for em in emails:
            em_id = em.get("id")
            expected_action = (em.get("correct_action") or "report").strip().lower()
            chosen_action = str(user_actions.get(em_id, "")).strip().lower()
            if chosen_action == expected_action:
                correct_count += 1

        accuracy_percent = int((correct_count / total_count) * 100) if total_count > 0 else 100
        min_required = c.min_accuracy_percent or 100

        if accuracy_percent >= min_required:
            return ChallengeResponse(
                status="correct",
                message=f"Inbox Analysis Verified! Accuracy: {accuracy_percent}% ({correct_count}/{total_count} correct)."
            )
        else:
            return ChallengeResponse(
                status="incorrect",
                message=f"Assessment Failed. Accuracy was {accuracy_percent}% ({correct_count}/{total_count} correct). Minimum required: {min_required}%."
            )
