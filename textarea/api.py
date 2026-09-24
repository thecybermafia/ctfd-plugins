from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from CTFd.models import Awards, Challenges, Solves, Users, db
from CTFd.plugins.textarea.models import TextareaChallenge, TextareaSubmission
from CTFd.utils.dates import ctf_ended, ctf_started
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_team, get_current_user, is_admin

textarea_bp = Blueprint(
    "textarea",
    __name__,
    template_folder="templates",
    static_folder="assets",
)

@textarea_bp.route("/api/v1/challenges/<int:challenge_id>/textarea/submit", methods=["POST"])
@authed_only
def submit_textarea(challenge_id):
    if not ctf_started() and not is_admin():
        return jsonify({"success": False, "message": "Competition has not started yet"}), 403

    if ctf_ended() and not is_admin():
        return jsonify({"success": False, "message": "Competition has ended"}), 403

    chal = TextareaChallenge.query.filter_by(id=challenge_id).first_or_404()
    if chal.state == "hidden" and not is_admin():
        return jsonify({"success": False, "message": "Challenge is not available"}), 404

    user = get_current_user()
    team = get_current_team()

    # Check if already solved
    solve_filter = {"challenge_id": challenge_id}
    if team:
        solve_filter["team_id"] = team.id
    else:
        solve_filter["user_id"] = user.id

    if Solves.query.filter_by(**solve_filter).first():
        return jsonify({"success": False, "message": "Challenge already solved"}), 400

    data = request.get_json() or request.form or {}
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"success": False, "message": "Submission text cannot be empty"}), 400

    # Enforce minimum & maximum length constraints
    min_len = chal.min_chars or 0
    max_len = chal.max_chars or 5000

    if len(content) < min_len:
        return jsonify({
            "success": False,
            "message": f"Submission is too short. Minimum {min_len} characters required (current: {len(content)})."
        }), 400

    if len(content) > max_len:
        return jsonify({
            "success": False,
            "message": f"Submission exceeds maximum length of {max_len} characters (current: {len(content)})."
        }), 400

    # Hard ceiling clamp to prevent database DoS
    content = content[:50000]

    # Find existing pending submission or create new
    sub_filter = {"challenge_id": challenge_id}
    if team:
        sub_filter["team_id"] = team.id
    else:
        sub_filter["user_id"] = user.id

    existing_sub = TextareaSubmission.query.filter_by(**sub_filter).order_by(TextareaSubmission.id.desc()).first()
    if existing_sub and existing_sub.status == "pending":
        existing_sub.content = content
        existing_sub.created_at = datetime.utcnow()
    else:
        new_sub = TextareaSubmission(
            challenge_id=challenge_id,
            user_id=user.id,
            team_id=team.id if team else None,
            content=content,
            status="pending",
            points_awarded=0,
            feedback="",
            created_at=datetime.utcnow()
        )
        db.session.add(new_sub)

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Writeup submitted successfully! Pending Mission Control review.",
        "status": "pending"
    })

@textarea_bp.route("/api/v1/challenges/<int:challenge_id>/textarea/my_status", methods=["GET"])
@authed_only
def get_submission_status(challenge_id):
    user = get_current_user()
    team = get_current_team()

    sub_filter = {"challenge_id": challenge_id}
    if team:
        sub_filter["team_id"] = team.id
    else:
        sub_filter["user_id"] = user.id

    sub = TextareaSubmission.query.filter_by(**sub_filter).order_by(TextareaSubmission.id.desc()).first()
    if not sub:
        return jsonify({"success": True, "status": "none", "data": None})

    return jsonify({
        "success": True,
        "status": sub.status,
        "data": {
            "id": sub.id,
            "status": sub.status,
            "content": sub.content,
            "points_awarded": sub.points_awarded,
            "feedback": sub.feedback,
            "created_at": sub.created_at.strftime("%Y-%m-%d %H:%M:%S") if sub.created_at else None,
        }
    })

@textarea_bp.route("/admin/textarea_submissions", methods=["GET"])
@admins_only
def admin_submissions():
    status_filter = request.args.get("status", "pending")
    chal_filter = request.args.get("challenge_id")

    query = TextareaSubmission.query
    if status_filter and status_filter != "all":
        query = query.filter_by(status=status_filter)
    if chal_filter:
        query = query.filter_by(challenge_id=int(chal_filter))

    submissions = query.order_by(TextareaSubmission.created_at.desc()).all()
    sub_list = []
    for s in submissions:
        sub_list.append({
            "id": s.id,
            "challenge_id": s.challenge_id,
            "challenge_name": s.challenge.name if s.challenge else f"Challenge #{s.challenge_id}",
            "challenge_value": s.challenge.value if s.challenge else 0,
            "user_id": s.user_id,
            "user_name": s.user.name if s.user else "Unknown",
            "team_id": s.team_id,
            "team_name": s.team.name if s.team else None,
            "status": s.status,
            "content": s.content,
            "points_awarded": s.points_awarded,
            "feedback": s.feedback,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
        })

    return render_template(
        "admin/textarea_submissions.html",
        submissions=sub_list,
        current_status=status_filter
    )

@textarea_bp.route("/api/v1/admin/textarea_submissions/<int:submission_id>/review", methods=["POST"])
@admins_only
def review_submission(submission_id):
    sub = TextareaSubmission.query.filter_by(id=submission_id).first_or_404()
    data = request.get_json() or request.form
    new_status = data.get("status")
    feedback = str(data.get("feedback", "")).strip()[:4000]

    if new_status not in ("approved", "rejected"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    admin_user = get_current_user()
    sub.status = new_status
    sub.feedback = feedback
    sub.reviewer_id = admin_user.id

    if new_status == "approved":
        default_points = sub.challenge.value if sub.challenge else 0
        raw_points = data.get("points")
        if raw_points is None or raw_points == "":
            points = default_points
        else:
            try:
                points = int(raw_points)
            except (TypeError, ValueError):
                return jsonify({"success": False, "message": "Points must be an integer"}), 400

        # Never award negative points or excessive overflow
        points = max(0, min(100000, points))
        sub.points_awarded = points

        # Insert solve if not already present
        solve_filter = {"challenge_id": sub.challenge_id}
        if sub.team_id:
            solve_filter["team_id"] = sub.team_id
        else:
            solve_filter["user_id"] = sub.user_id

        existing_solve = Solves.query.filter_by(**solve_filter).first()
        if not existing_solve:
            solve = Solves(
                user_id=sub.user_id,
                team_id=sub.team_id,
                challenge_id=sub.challenge_id,
                ip=request.remote_addr,
                provided=sub.content[:100]
            )
            db.session.add(solve)

            # If custom points awarded differs from default challenge value, add differential award
            if points != default_points:
                diff = points - default_points
                award = Awards(
                    user_id=sub.user_id,
                    team_id=sub.team_id,
                    type="standard",
                    name=f"Manual Grading Adjustment: {sub.challenge.name if sub.challenge else 'Challenge'}",
                    description=feedback or "Manual review score adjustment",
                    value=diff,
                    category="Manual Review",
                    date=datetime.utcnow()
                )
                db.session.add(award)
    elif new_status == "rejected":
        sub.points_awarded = 0
        # If there was a previous solve from this challenge, do not delete unless desired
        # but mark submission rejected so user can resubmit

    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"Submission {new_status} successfully!",
        "status": new_status,
        "points_awarded": sub.points_awarded
    })
