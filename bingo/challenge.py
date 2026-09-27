import hashlib
import json
import random
from CTFd.models import Flags, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.bingo.models import BingoChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def parse_simple_lines_to_cells(text, grid_size=5):
    """
    Parses simple admin lines formatted as:
    Title | Flag (or chal:ID) | Points | ChallengeID
    e.g.:
    Robots.txt | flag{robots} | 15
    Solve SQLi | chal:14 | 20
    Network Triage | flag{net} | 10 | 12
    """
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    total_cells = grid_size * grid_size
    cells = []

    for i in range(total_cells):
        chal_id = None
        if i < len(lines):
            parts = [p.strip() for p in lines[i].split("|")]
            title = parts[0] if len(parts) > 0 else f"Square #{i+1}"
            flag = parts[1] if len(parts) > 1 else f"flag_{i+1}"
            pts = 10
            if len(parts) > 2 and parts[2].isdigit():
                pts = int(parts[2])
            if len(parts) > 3 and parts[3].isdigit():
                chal_id = int(parts[3])

            # Check if flag column specifies chal:ID or #ID
            if flag.lower().startswith("chal:") or flag.startswith("#"):
                raw_id = flag.lower().replace("chal:", "").replace("#", "").strip()
                if raw_id.isdigit():
                    chal_id = int(raw_id)
                    flag = ""  # linked directly to challenge
        else:
            title = f"Square #{i+1}"
            flag = f"flag_{i+1}"
            pts = 10

        desc = f"Complete '{title}' and enter the flag."
        if chal_id:
            desc = f"Solve linked Challenge #{chal_id} to mark this tile complete."

        cells.append({
            "index": i,
            "title": title,
            "desc": desc,
            "flag": flag,
            "points": pts,
            "challenge_id": chal_id,
        })
    return cells


def cells_to_simple_lines(cells_json):
    try:
        cells = json.loads(cells_json or "[]")
        lines = []
        for c in cells:
            parts = [c.get("title", "")]
            flag_val = c.get("flag", "")
            chal_id = c.get("challenge_id")
            if chal_id and not flag_val:
                flag_val = f"chal:{chal_id}"

            parts.append(flag_val)
            parts.append(str(c.get("points", 10)))
            if chal_id and c.get("flag"):
                parts.append(str(chal_id))
            lines.append(" | ".join(parts))
        return "\n".join(lines)
    except Exception:
        return ""


def get_deterministic_shuffle(items, seed_key):
    if not items:
        return items
    shuffled = list(items)
    seed = int(hashlib.md5(str(seed_key).encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    return shuffled


class BingoChallengeType(BaseChallenge):
    id = "bingo"
    name = "bingo"
    templates = {
        "create": "/plugins/bingo/assets/create.html",
        "update": "/plugins/bingo/assets/update.html",
        "view": "/plugins/bingo/assets/view.html",
    }
    scripts = {
        "create": "/plugins/bingo/assets/create.js",
        "update": "/plugins/bingo/assets/update.js",
        "view": "/plugins/bingo/assets/view.js",
    }
    route = "/plugins/bingo/assets/"
    challenge_model = BingoChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = BingoChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return data

        user = get_current_user()
        team = get_current_team()
        is_user_admin = is_admin()

        sanitized_cells = []
        try:
            raw_cells = json.loads(c.cells_json or "[]")
            for cell in raw_cells:
                sanitized_cells.append({
                    "index": cell.get("index"),
                    "title": cell.get("title", ""),
                    "desc": cell.get("desc", ""),
                    "points": cell.get("points", 10),
                    "challenge_id": cell.get("challenge_id"),
                })
        except Exception as e:
            print("Error parsing bingo cells_json:", e)

        # Apply shuffle if enabled
        if c.shuffle_cards and not is_user_admin:
            seed = f"{team.id if team else (user.id if user else 0)}_{c.id}"
            sanitized_cells = get_deterministic_shuffle(sanitized_cells, seed)

        data.update({
            "grid_size": c.grid_size,
            "line_bonus": c.line_bonus,
            "blackout_bonus": c.blackout_bonus,
            "shuffle_cards": bool(c.shuffle_cards),
            "cells_data": sanitized_cells,
        })
        if is_user_admin:
            data["squares_text"] = cells_to_simple_lines(c.cells_json)
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        for attr in ("grid_size", "line_bonus", "blackout_bonus"):
            if attr in data:
                setattr(challenge, attr, int(data[attr]))

        if "shuffle_cards" in data:
            challenge.shuffle_cards = str(data["shuffle_cards"]).lower() in ("true", "1", "yes", "on")

        if "squares_text" in data:
            size = int(data.get("grid_size", challenge.grid_size or 5))
            cells = parse_simple_lines_to_cells(data["squares_text"], grid_size=size)
            challenge.cells_json = json.dumps(cells)

        return super().update(challenge, request)

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        size = int(data.get("grid_size", challenge.grid_size or 5))
        squares_text = data.get("squares_text", "")
        cells = parse_simple_lines_to_cells(squares_text, grid_size=size)

        challenge.grid_size = size
        challenge.cells_json = json.dumps(cells)
        for attr in ("line_bonus", "blackout_bonus"):
            if attr in data:
                setattr(challenge, attr, int(data[attr]))

        challenge.shuffle_cards = str(data.get("shuffle_cards", "false")).lower() in ("true", "1", "yes", "on")

        db.session.commit()
        return challenge

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        # Check standard Flags
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="Bingo blackout solved!")
            except Exception:
                pass

        return ChallengeResponse(
            status="incorrect",
            message="Please click squares on the Bingo card to enter tile flags or solve linked challenges."
        )
