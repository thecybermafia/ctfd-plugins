import json
from CTFd.models import Flags, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.bingo.models import BingoChallenge
from CTFd.utils.user import is_admin

def parse_simple_lines_to_cells(text, grid_size=5):
    """
    Parses simple admin lines formatted as:
    Title | Flag (optional | Points)
    e.g.:
    Robots.txt | flag{robots} | 15
    """
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    total_cells = grid_size * grid_size
    cells = []

    for i in range(total_cells):
        if i < len(lines):
            parts = [p.strip() for p in lines[i].split("|")]
            title = parts[0] if len(parts) > 0 else f"Square #{i+1}"
            flag = parts[1] if len(parts) > 1 else f"flag_{i+1}"
            pts = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
        else:
            title = f"Square #{i+1}"
            flag = f"flag_{i+1}"
            pts = 10

        cells.append({
            "index": i,
            "title": title,
            "desc": f"Complete '{title}' and enter the flag.",
            "flag": flag,
            "points": pts
        })
    return cells

def cells_to_simple_lines(cells_json):
    try:
        cells = json.loads(cells_json or "[]")
        lines = []
        for c in cells:
            lines.append(f"{c.get('title', '')} | {c.get('flag', '')}")
        return "\n".join(lines)
    except Exception:
        return ""

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
        if c:
            sanitized_cells = []
            try:
                raw_cells = json.loads(c.cells_json or "[]")
                for cell in raw_cells:
                    sanitized_cells.append({
                        "index": cell.get("index"),
                        "title": cell.get("title", ""),
                        "desc": cell.get("desc", ""),
                        "points": cell.get("points", 10),
                    })
            except Exception as e:
                print("Error parsing bingo cells_json:", e)

            data.update({
                "grid_size": c.grid_size,
                "line_bonus": c.line_bonus,
                "blackout_bonus": c.blackout_bonus,
                "cells_data": sanitized_cells,
            })
            if is_admin():
                data["squares_text"] = cells_to_simple_lines(c.cells_json)
        return data

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        for attr in ("grid_size", "line_bonus", "blackout_bonus"):
            if attr in data:
                setattr(challenge, attr, int(data[attr]))

        # Handle simple squares_text input from admin
        if "squares_text" in data:
            size = int(data.get("grid_size", challenge.grid_size or 5))
            cells = parse_simple_lines_to_cells(data["squares_text"], grid_size=size)
            challenge.cells_json = json.dumps(cells)

        return super().update(challenge, request)

    @classmethod
    def create(cls, request):
        # Create the base challenge first so the row exists, then persist the
        # bingo-specific fields. Previously a local data dict was built and the
        # original request passed to super().create(), discarding cells_json.
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
            message="Please click squares on the Bingo card to enter tile flags."
        )
