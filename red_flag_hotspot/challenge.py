import json
import math
from CTFd.models import Fails, Flags, Solves, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.red_flag_hotspot.models import HotspotChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def get_default_sample_hotspots():
    return [
        {
            "id": "spot_1",
            "label": "Forged Sender Display Name & Domain Mismatch",
            "x": 35.0,
            "y": 14.5,
            "radius": 6.5,
            "explanation": "Display name is 'Corporate Security' but sender domain is @notice-corp-auth.biz."
        },
        {
            "id": "spot_2",
            "label": "Suspicious Attachment Double Extension",
            "x": 68.2,
            "y": 38.0,
            "radius": 6.5,
            "explanation": "Attachment name ends with .pdf.exe, disguising a malicious executable."
        },
        {
            "id": "spot_3",
            "label": "Artificial Urgency & Threat",
            "x": 50.0,
            "y": 62.0,
            "radius": 7.0,
            "explanation": "Artificial deadline designed to induce panic and bypass verification protocols."
        }
    ]


class RedFlagHotspotChallengeType(BaseChallenge):
    id = "red_flag_hotspot"
    name = "red_flag_hotspot"
    templates = {
        "create": "/plugins/red_flag_hotspot/assets/create.html",
        "update": "/plugins/red_flag_hotspot/assets/update.html",
        "view": "/plugins/red_flag_hotspot/assets/view.html",
    }
    scripts = {
        "create": "/plugins/red_flag_hotspot/assets/create.js",
        "update": "/plugins/red_flag_hotspot/assets/update.js",
        "view": "/plugins/red_flag_hotspot/assets/view.js",
    }
    route = "/plugins/red_flag_hotspot/assets/"
    challenge_model = HotspotChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = HotspotChallenge.query.filter_by(id=challenge.id).first()
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

        raw_hotspots = c.hotspots_data
        total_hotspots = len(raw_hotspots)

        # Sanitize hotspot coordinates if participant has not solved yet
        if is_solved or is_admin():
            sanitized_hotspots = raw_hotspots
        else:
            sanitized_hotspots = [
                {"id": h.get("id"), "label": f"Red Flag #{i+1}"}
                for i, h in enumerate(raw_hotspots)
            ]

        data.update({
            "image_url": c.image_url or "",
            "hotspots_count": total_hotspots,
            "hotspots_data": sanitized_hotspots,
            "max_clicks": c.max_clicks or 5,
            "tolerance_radius": c.tolerance_radius or 6.0,
            "min_hits_required": c.min_hits_required or 0,
            "is_solved": is_solved,
            "attempts_used": attempts_used,
            "explanation": c.explanation if (is_solved or is_admin()) else "",
        })

        if is_admin():
            data["hotspots_json"] = c.hotspots_json

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = HotspotChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.image_url = data.get("image_url", "").strip()
            c.max_clicks = int(data.get("max_clicks", 5) or 5)
            c.tolerance_radius = float(data.get("tolerance_radius", 6.0) or 6.0)
            c.min_hits_required = int(data.get("min_hits_required", 0) or 0)
            c.explanation = data.get("explanation", "").strip()

            hotspots_json_val = data.get("hotspots_json", "").strip()
            if not hotspots_json_val:
                hotspots_json_val = json.dumps(get_default_sample_hotspots(), indent=2)
            c.hotspots_json = hotspots_json_val
            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        for attr in ("image_url", "explanation"):
            if attr in data:
                setattr(challenge, attr, data[attr].strip())

        for attr in ("max_clicks", "min_hits_required"):
            if attr in data:
                setattr(challenge, attr, int(data[attr] or 0))

        if "tolerance_radius" in data:
            setattr(challenge, "tolerance_radius", float(data["tolerance_radius"] or 6.0))

        if "hotspots_json" in data:
            challenge.hotspots_json = data["hotspots_json"].strip()

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        user = get_current_user()
        team = get_current_team()

        c = HotspotChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Check standard Flags
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="Spot-the-Red-Flag Success via Flag!")
            except Exception:
                pass

        # Check attempt limits
        if c.max_clicks and c.max_clicks > 0 and user:
            filter_kwargs = {"challenge_id": c.id}
            if team:
                filter_kwargs["team_id"] = team.id
            else:
                filter_kwargs["user_id"] = user.id

        # Parse submitted coordinates
        # Expected: [{"x": 34.5, "y": 14.2}, ...] or string pairs "34.5,14.2; 68.2,38.0"
        clicks = []
        try:
            if submission.startswith("[") and submission.endswith("]"):
                parsed = json.loads(submission)
                for item in parsed:
                    if isinstance(item, dict) and "x" in item and "y" in item:
                        clicks.append({"x": float(item["x"]), "y": float(item["y"])})
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        clicks.append({"x": float(item[0]), "y": float(item[1])})
            elif ";" in submission or "," in submission:
                pairs = [p.strip() for p in submission.replace(";", "\n").splitlines() if p.strip()]
                for pair in pairs:
                    parts = [p.strip() for p in pair.split(",") if p.strip()]
                    if len(parts) >= 2:
                        clicks.append({"x": float(parts[0]), "y": float(parts[1])})
        except Exception:
            return ChallengeResponse(status="incorrect", message="Invalid coordinates format submitted.")

        if not clicks:
            return ChallengeResponse(status="incorrect", message="No red flags marked on the image. Click to place markers.")

        if c.max_clicks and len(clicks) > c.max_clicks:
            return ChallengeResponse(
                status="incorrect",
                message=f"Too many markers placed ({len(clicks)}). Maximum allowed clicks: {c.max_clicks}."
            )

        hotspots = c.hotspots_data
        if not hotspots:
            return ChallengeResponse(status="correct", message="No red flags configured. Solved!")

        default_tol = c.tolerance_radius or 6.0
        hit_hotspot_ids = set()

        for click in clicks:
            cx = click["x"]
            cy = click["y"]
            for h in hotspots:
                hx = float(h.get("x", 0.0))
                hy = float(h.get("y", 0.0))
                tol = float(h.get("radius", default_tol))
                dist = math.hypot(cx - hx, cy - hy)
                if dist <= tol:
                    hit_hotspot_ids.add(h.get("id"))

        hits = len(hit_hotspot_ids)
        total = len(hotspots)
        required = c.min_hits_required if (c.min_hits_required and c.min_hits_required > 0) else total

        if hits >= required:
            return ChallengeResponse(
                status="correct",
                message=f"Spot-the-Red-Flag Success! Identified {hits}/{total} suspicious areas."
            )
        else:
            return ChallengeResponse(
                status="incorrect",
                message=f"Identified {hits} of {required} required red flags. Review the evidence carefully."
            )
