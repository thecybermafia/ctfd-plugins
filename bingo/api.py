import hmac
import json
from datetime import datetime
from flask import Blueprint, jsonify, request
from CTFd.cache import clear_standings
from CTFd.models import Awards, Challenges, Solves, db
from CTFd.utils.dates import ctf_ended, ctf_started
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_team, get_current_user, is_admin
from CTFd.plugins.bingo.models import BingoCellSolve, BingoChallenge, BingoLineAward

bingo_bp = Blueprint("bingo", __name__, template_folder="templates", static_folder="assets")

def get_participant_filter(team, user, challenge_id):
    if team:
        return {"challenge_id": challenge_id, "team_id": team.id}
    return {"challenge_id": challenge_id, "user_id": user.id}

@bingo_bp.route("/api/v1/challenges/<int:challenge_id>/bingo/state", methods=["GET"])
@authed_only
def get_bingo_state(challenge_id):
    chal = BingoChallenge.query.filter_by(id=challenge_id).first_or_404()
    if chal.state == "hidden" and not is_admin():
        return jsonify({"success": False, "message": "Challenge is not available"}), 404

    user = get_current_user()
    team = get_current_team()
    p_filter = get_participant_filter(team, user, challenge_id)

    solves = BingoCellSolve.query.filter_by(**p_filter).all()
    solved_indices = [s.cell_index for s in solves]

    line_awards = BingoLineAward.query.filter_by(**p_filter).all()
    completed_lines = [la.line_id for la in line_awards]

    return jsonify({
        "success": True,
        "data": {
            "solved_cells": solved_indices,
            "completed_lines": completed_lines,
        }
    })

@bingo_bp.route("/api/v1/challenges/<int:challenge_id>/bingo/attempt_cell", methods=["POST"])
@authed_only
def attempt_bingo_cell(challenge_id):
    if not ctf_started() and not is_admin():
        return jsonify({"success": False, "message": "Competition has not started yet"}), 403

    if ctf_ended() and not is_admin():
        return jsonify({"success": False, "message": "Competition has ended"}), 403

    chal = BingoChallenge.query.filter_by(id=challenge_id).first_or_404()
    if chal.state == "hidden" and not is_admin():
        return jsonify({"success": False, "message": "Challenge is not available"}), 404

    user = get_current_user()
    team = get_current_team()
    p_filter = get_participant_filter(team, user, challenge_id)

    data = request.get_json() or request.form
    try:
        cell_index = int(data.get("cell_index"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid cell index"}), 400

    submission_flag = (data.get("flag") or "").strip()
    if not submission_flag:
        return jsonify({"success": False, "message": "Flag input required"}), 400

    # Load cell definition
    cells = []
    try:
        cells = json.loads(chal.cells_json or "[]")
    except Exception:
        pass

    target_cell = next((c for c in cells if c.get("index") == cell_index), None)
    if not target_cell:
        return jsonify({"success": False, "message": "Cell definition not found"}), 404

    expected_flag = (target_cell.get("flag") or "").strip()

    def _normalize(val):
        val = (val or "").strip().lower()
        if val.startswith("flag{") and val.endswith("}"):
            val = val[5:-1].strip()
        val = val.replace("_", " ").replace("-", " ")
        return " ".join(val.split())

    sub_raw = submission_flag.strip().lower()
    exp_raw = expected_flag.strip().lower()
    sub_norm = _normalize(submission_flag)
    exp_norm = _normalize(expected_flag)

    is_match = False
    if expected_flag:
        if hmac.compare_digest(sub_raw.encode("utf-8"), exp_raw.encode("utf-8")):
            is_match = True
        elif hmac.compare_digest(sub_norm.encode("utf-8"), exp_norm.encode("utf-8")):
            is_match = True
        elif hmac.compare_digest(f"flag{{{sub_norm.replace(' ', '_')}}}".encode("utf-8"), exp_raw.encode("utf-8")):
            is_match = True
        elif hmac.compare_digest(sub_norm.encode("utf-8"), _normalize(exp_raw).encode("utf-8")):
            is_match = True

    if not is_match:
        return jsonify({"success": False, "status": "incorrect", "message": "Incorrect flag for this tile"}), 200


    # Award subject: in team mode all Awards are attributed to the team
    # (user_id=None) so teammates cannot re-trigger cell points or line/blackout
    # bonuses. In user mode they are attributed to the user.
    award_user_id = None if team else user.id
    award_team_id = team.id if team else None

    # Flag is correct! Check if already solved
    existing_solve = BingoCellSolve.query.filter_by(cell_index=cell_index, **p_filter).first()
    if not existing_solve:
        new_solve = BingoCellSolve(
            challenge_id=challenge_id,
            user_id=user.id,
            team_id=team.id if team else None,
            cell_index=cell_index,
            solved_at=datetime.utcnow()
        )
        db.session.add(new_solve)

        # Award points for individual cell if specified
        cell_pts = target_cell.get("points", 0)
        if cell_pts > 0:
            cell_award = Awards(
                user_id=award_user_id,
                team_id=award_team_id,
                name=f"Bingo Tile #{cell_index+1} [{chal.name}]",
                description=f"Solved tile '{target_cell.get('title')}' in {chal.name}",
                value=cell_pts,
                category=chal.category
            )
            db.session.add(cell_award)

        db.session.commit()

    # Recalculate all solved cells to check pattern completions
    all_solves = BingoCellSolve.query.filter_by(**p_filter).all()
    solved_set = {s.cell_index for s in all_solves}

    existing_lines = {la.line_id for la in BingoLineAward.query.filter_by(**p_filter).all()}
    new_lines_awarded = []

    N = chal.grid_size or 5
    line_bonus = chal.line_bonus or 50

    # 1. Check rows
    for r in range(N):
        line_id = f"row_{r}"
        if line_id not in existing_lines:
            row_cells = {r * N + c for c in range(N)}
            if row_cells.issubset(solved_set):
                award = Awards(
                    user_id=award_user_id,
                    team_id=award_team_id,
                    name=f"Bingo Row {r+1} Completion [{chal.name}]",
                    description=f"Completed row {r+1} in {chal.name}",
                    value=line_bonus,
                    category=chal.category
                )
                db.session.add(award)
                db.session.flush()

                bla = BingoLineAward(
                    challenge_id=challenge_id,
                    user_id=user.id,
                    team_id=team.id if team else None,
                    line_id=line_id,
                    award_id=award.id
                )
                db.session.add(bla)
                new_lines_awarded.append(f"Row {r+1}")

    # 2. Check columns
    for c in range(N):
        line_id = f"col_{c}"
        if line_id not in existing_lines:
            col_cells = {r * N + c for r in range(N)}
            if col_cells.issubset(solved_set):
                award = Awards(
                    user_id=award_user_id,
                    team_id=award_team_id,
                    name=f"Bingo Column {c+1} Completion [{chal.name}]",
                    description=f"Completed column {c+1} in {chal.name}",
                    value=line_bonus,
                    category=chal.category
                )
                db.session.add(award)
                db.session.flush()

                bla = BingoLineAward(
                    challenge_id=challenge_id,
                    user_id=user.id,
                    team_id=team.id if team else None,
                    line_id=line_id,
                    award_id=award.id
                )
                db.session.add(bla)
                new_lines_awarded.append(f"Column {c+1}")

    # 3. Check Main Diagonal
    if "diag_main" not in existing_lines:
        diag_main = {i * N + i for i in range(N)}
        if diag_main.issubset(solved_set):
            award = Awards(
                user_id=award_user_id,
                team_id=award_team_id,
                name=f"Bingo Diagonal Completion [{chal.name}]",
                description=f"Completed main diagonal in {chal.name}",
                value=line_bonus,
                category=chal.category
            )
            db.session.add(award)
            db.session.flush()
            bla = BingoLineAward(
                challenge_id=challenge_id,
                user_id=user.id,
                team_id=team.id if team else None,
                line_id="diag_main",
                award_id=award.id
            )
            db.session.add(bla)
            new_lines_awarded.append("Main Diagonal")

    # 4. Check Anti-Diagonal
    if "diag_anti" not in existing_lines:
        diag_anti = {i * N + (N - 1 - i) for i in range(N)}
        if diag_anti.issubset(solved_set):
            award = Awards(
                user_id=award_user_id,
                team_id=award_team_id,
                name=f"Bingo Anti-Diagonal Completion [{chal.name}]",
                description=f"Completed anti-diagonal in {chal.name}",
                value=line_bonus,
                category=chal.category
            )
            db.session.add(award)
            db.session.flush()
            bla = BingoLineAward(
                challenge_id=challenge_id,
                user_id=user.id,
                team_id=team.id if team else None,
                line_id="diag_anti",
                award_id=award.id
            )
            db.session.add(bla)
            new_lines_awarded.append("Anti-Diagonal")

    # 5. Check Full Board Blackout
    total_cells = N * N
    if len(solved_set) == total_cells and "blackout" not in existing_lines:
        blackout_bonus = chal.blackout_bonus or 250
        award = Awards(
            user_id=award_user_id,
            team_id=award_team_id,
            name=f"Bingo Full Card Blackout [{chal.name}]",
            description=f"Completed entire Bingo board in {chal.name}",
            value=blackout_bonus,
            category=chal.category
        )
        db.session.add(award)
        db.session.flush()
        bla = BingoLineAward(
            challenge_id=challenge_id,
            user_id=user.id,
            team_id=team.id if team else None,
            line_id="blackout",
            award_id=award.id
        )
        db.session.add(bla)

        # Mark challenge solved in Solves table
        existing_chal_solve = Solves.query.filter_by(challenge_id=challenge_id, **({"team_id": team.id} if team else {"user_id": user.id})).first()
        if not existing_chal_solve:
            chal_solve = Solves(
                user_id=user.id,
                team_id=team.id if team else None,
                challenge_id=challenge_id,
                ip=request.remote_addr,
                provided="[Bingo Blackout Solved]"
            )
            db.session.add(chal_solve)

        new_lines_awarded.append("FULL BLACKOUT")

    db.session.commit()
    clear_standings()

    msg = f"Tile #{cell_index+1} solved successfully!"
    if new_lines_awarded:
        line_names = [l for l in new_lines_awarded if l != "FULL BLACKOUT"]
        parts = []
        if line_names:
            parts.append(f"Bonus lines completed: {', '.join(line_names)} (+{line_bonus} pts each)")
        if "FULL BLACKOUT" in new_lines_awarded:
            parts.append(f"FULL BLACKOUT (+{chal.blackout_bonus or 250} pts)")
        msg += " [BONUS] " + "; ".join(parts) + "!"

    return jsonify({
        "success": True,
        "status": "correct",
        "message": msg,
        "new_lines": new_lines_awarded,
        "solved_cells": list(solved_set)
    })
