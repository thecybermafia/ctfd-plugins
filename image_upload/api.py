from datetime import datetime
import os
from flask import Blueprint, jsonify, render_template, request, url_for
from CTFd.cache import clear_standings
from CTFd.models import Challenges, Solves, Users, Teams, db
from CTFd.utils.dates import ctf_ended, ctf_started
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.uploads import upload_file
from CTFd.utils.user import authed, get_current_team, get_current_user, is_admin
from CTFd.plugins.image_upload.models import ImageUploadChallenge, ImageUploadSubmission

image_upload_bp = Blueprint(
    "image_upload",
    __name__,
    template_folder="templates",
    static_folder="assets",
)

SAFE_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
DANGEROUS_EXTENSIONS = {
    "svg", "html", "htm", "xhtml", "xml", "php", "phtml", "py", "sh", "exe",
    "js", "jsp", "asp", "aspx", "cgi", "pl", "rb", "bat", "cmd", "ps1"
}

@image_upload_bp.route("/api/v1/challenges/<int:challenge_id>/image_upload/submit", methods=["POST"])
@authed_only
def submit_image(challenge_id):
    if not ctf_started() and not is_admin():
        return jsonify({"success": False, "message": "Competition has not started yet"}), 403

    if ctf_ended() and not is_admin():
        return jsonify({"success": False, "message": "Competition has ended"}), 403

    chal = ImageUploadChallenge.query.filter_by(id=challenge_id).first_or_404()
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

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext in DANGEROUS_EXTENSIONS or ext not in SAFE_IMAGE_EXTENSIONS:
        return jsonify({
            "success": False,
            "message": "Disallowed file type. Only standard raster image formats (png, jpg, jpeg, webp, gif, bmp) are permitted."
        }), 400

    chal_allowed = [e.strip().lower() for e in (chal.allowed_extensions or "").split(",") if e.strip()]
    if chal_allowed and ext not in chal_allowed:
        return jsonify({"success": False, "message": f"File type '.{ext}' not allowed. Allowed: {chal.allowed_extensions}"}), 400

    # Inspect Magic Bytes / Signature to ensure genuine image file content
    file.seek(0)
    header = file.read(16)
    file.seek(0)

    is_valid_image = False
    if ext == "png" and header.startswith(b"\x89PNG\r\n\x1a\n"):
        is_valid_image = True
    elif ext in ("jpg", "jpeg") and header.startswith(b"\xff\xd8\xff"):
        is_valid_image = True
    elif ext == "gif" and (header.startswith(b"GIF87a") or header.startswith(b"GIF89a")):
        is_valid_image = True
    elif ext == "webp" and len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        is_valid_image = True
    elif ext == "bmp" and header.startswith(b"BM"):
        is_valid_image = True

    if not is_valid_image:
        return jsonify({"success": False, "message": "Corrupted or invalid image file content signature."}), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > chal.max_file_size_mb:
        return jsonify({"success": False, "message": f"File exceeds maximum size of {chal.max_file_size_mb} MB"}), 400

    # Save file using CTFd uploader
    saved_file = upload_file(file=file, type="image_upload")
    notes = request.form.get("notes", "")[:4000].strip()

    # Find existing pending submission or create new
    sub_filter = {"challenge_id": challenge_id}
    if team:
        sub_filter["team_id"] = team.id
    else:
        sub_filter["user_id"] = user.id

    existing_sub = ImageUploadSubmission.query.filter_by(**sub_filter).order_by(ImageUploadSubmission.id.desc()).first()
    if existing_sub and existing_sub.status == "pending":
        existing_sub.file_id = saved_file.id
        existing_sub.notes = notes
        existing_sub.created_at = datetime.utcnow()
    else:
        new_sub = ImageUploadSubmission(
            challenge_id=challenge_id,
            user_id=user.id,
            team_id=team.id if team else None,
            file_id=saved_file.id,
            notes=notes,
            status="pending",
            points_awarded=0,
            feedback="",
            created_at=datetime.utcnow()
        )
        db.session.add(new_sub)

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Image submitted successfully! Pending admin evaluation.",
        "status": "pending"
    })

@image_upload_bp.route("/api/v1/challenges/<int:challenge_id>/image_upload/my_status", methods=["GET"])
@authed_only
def get_submission_status(challenge_id):
    user = get_current_user()
    team = get_current_team()

    sub_filter = {"challenge_id": challenge_id}
    if team:
        sub_filter["team_id"] = team.id
    else:
        sub_filter["user_id"] = user.id

    sub = ImageUploadSubmission.query.filter_by(**sub_filter).order_by(ImageUploadSubmission.id.desc()).first()
    if not sub:
        return jsonify({"success": True, "data": None})

    file_url = url_for("views.files", path=sub.file.location) if sub.file else None
    return jsonify({
        "success": True,
        "data": {
            "id": sub.id,
            "status": sub.status,
            "notes": sub.notes,
            "points_awarded": sub.points_awarded,
            "feedback": sub.feedback,
            "created_at": sub.created_at.isoformat(),
            "file_url": file_url,
        }
    })

@image_upload_bp.route("/admin/image_uploads", methods=["GET"])
@admins_only
def admin_image_uploads():
    status_filter = request.args.get("status", "pending")
    query = ImageUploadSubmission.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)

    submissions = query.order_by(ImageUploadSubmission.created_at.desc()).all()
    sub_list = []
    for s in submissions:
        file_url = url_for("views.files", path=s.file.location) if s.file else None
        sub_list.append({
            "id": s.id,
            "challenge_id": s.challenge_id,
            "challenge_name": s.challenge.name if s.challenge else "Unknown",
            "challenge_value": s.challenge.value if s.challenge else 0,
            "user_name": s.user.name if s.user else "Unknown",
            "team_name": s.team.name if s.team else None,
            "status": s.status,
            "notes": s.notes,
            "points_awarded": s.points_awarded,
            "feedback": s.feedback,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "file_url": file_url,
        })

    return render_template(
        "admin/image_uploads.html",
        submissions=sub_list,
        current_status=status_filter
    )

@image_upload_bp.route("/api/v1/admin/image_uploads/<int:submission_id>/review", methods=["POST"])
@admins_only
def review_submission(submission_id):
    sub = ImageUploadSubmission.query.filter_by(id=submission_id).first_or_404()
    data = request.get_json() or request.form
    new_status = data.get("status")
    feedback = data.get("feedback", "").strip()

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
                provided=f"[Image Upload Verified: +{points} pts]"
            )
            db.session.add(solve)

        clear_standings()

    db.session.commit()
    return jsonify({"success": True, "message": f"Submission successfully {new_status}!"})
