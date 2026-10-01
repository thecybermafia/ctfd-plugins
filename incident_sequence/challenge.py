import json
import random
from CTFd.models import Fails, Flags, Solves, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.incident_sequence.models import IncidentSequenceChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def get_default_sample_steps():
    return [
        {
            "id": "step_1",
            "order": 1,
            "text": "Identify anomaly via SIEM alert and confirm IOCs on endpoint.",
            "explanation": "Detection & Analysis: Initial detection and validation of suspicious behavior."
        },
        {
            "id": "step_2",
            "order": 2,
            "text": "Isolate host from enterprise network to prevent lateral movement.",
            "explanation": "Containment: Rapid isolation prevents attacker spreading to critical domain assets."
        },
        {
            "id": "step_3",
            "order": 3,
            "text": "Capture volatile RAM image and volatile system artifacts.",
            "explanation": "Forensic Preservation: Memory dumps must be gathered prior to powering off or rebooting."
        },
        {
            "id": "step_4",
            "order": 4,
            "text": "Acquire dead-box bitstream disk image for forensic analysis.",
            "explanation": "Disk Acquisition: Bit-for-bit disk image preserves filesystem timestamps and unallocated space."
        },
        {
            "id": "step_5",
            "order": 5,
            "text": "Eradicate malware, re-image system from golden image, and rotate credentials.",
            "explanation": "Eradication & Recovery: Wipe malicious persistence and safely restore production capability."
        }
    ]


def get_default_sample_distractors():
    return [
        {
            "id": "dist_1",
            "text": "Immediately reboot the endpoint to clear RAM-resident malware.",
            "explanation": "Rebooting destroys volatile RAM evidence, active network connections, and unwritten file buffers."
        },
        {
            "id": "dist_2",
            "text": "Email the attacker using the ransom note contact address to negotiate payment.",
            "explanation": "Violates corporate IR policy and legal requirements, and alerts adversaries to containment efforts."
        }
    ]


class IncidentSequenceChallengeType(BaseChallenge):
    id = "incident_sequence"
    name = "incident_sequence"
    templates = {
        "create": "/plugins/incident_sequence/assets/create.html",
        "update": "/plugins/incident_sequence/assets/update.html",
        "view": "/plugins/incident_sequence/assets/view.html",
    }
    scripts = {
        "create": "/plugins/incident_sequence/assets/create.js",
        "update": "/plugins/incident_sequence/assets/update.js",
        "view": "/plugins/incident_sequence/assets/view.js",
    }
    route = "/plugins/incident_sequence/assets/"
    challenge_model = IncidentSequenceChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = IncidentSequenceChallenge.query.filter_by(id=challenge.id).first()
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

        raw_steps = c.steps_data
        raw_distractors = c.distractors_data

        # If not solved, shuffle cards and hide order/explanation
        if is_solved:
            sanitized_steps = sorted(raw_steps, key=lambda s: int(s.get("order", 0)))
            sanitized_distractors = raw_distractors
        else:
            sanitized_steps = c.get_shuffled_cards()
            sanitized_distractors = []

        data.update({
            "cards_data": sanitized_steps,
            "steps_data": sanitized_steps if is_solved else [],
            "distractors_data": sanitized_distractors if is_solved else [],
            "allow_distractor_bin": bool(c.allow_distractor_bin),
            "total_steps": len(raw_steps),
            "total_distractors": len(raw_distractors),
            "is_solved": is_solved,
            "attempts_used": attempts_used,
            "explanation": c.explanation if is_solved else "",
        })

        if is_admin():
            data["steps_json"] = c.steps_json
            data["distractors_json"] = c.distractors_json

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = IncidentSequenceChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.allow_distractor_bin = str(data.get("allow_distractor_bin", "true")).lower() in ("true", "1", "yes", "on")
            c.explanation = data.get("explanation", "").strip()

            steps_json_val = data.get("steps_json", "").strip()
            if not steps_json_val:
                steps_json_val = json.dumps(get_default_sample_steps(), indent=2)
            c.steps_json = steps_json_val

            dist_json_val = data.get("distractors_json", "").strip()
            if not dist_json_val:
                dist_json_val = json.dumps(get_default_sample_distractors(), indent=2)
            c.distractors_json = dist_json_val

            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        challenge = super().update(challenge, request)

        if "explanation" in data:
            challenge.explanation = data["explanation"].strip()

        if "allow_distractor_bin" in data:
            challenge.allow_distractor_bin = str(data["allow_distractor_bin"]).lower() in ("true", "1", "yes", "on", "checked")
        elif request.form and "name" in request.form:
            challenge.allow_distractor_bin = False

        if "steps_json" in data:
            challenge.steps_json = data["steps_json"].strip()

        if "distractors_json" in data:
            challenge.distractors_json = data["distractors_json"].strip()

        db.session.commit()
        return challenge

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        c = IncidentSequenceChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Check standard Flags
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="Incident Response Playbook Sequence Verified via Flag!")
            except Exception:
                pass

        # Submission expected: {"sequence": ["step_1", "step_2", ...], "distractors": ["dist_1", ...]}
        # Or array of step IDs: ["step_1", "step_2", ...]
        # Or comma-separated string "step_1,step_2,..."
        submitted_sequence = []
        submitted_distractors = []

        try:
            if submission.startswith("{") and submission.endswith("}"):
                obj = json.loads(submission)
                submitted_sequence = obj.get("sequence", [])
                submitted_distractors = obj.get("distractors", [])
            elif submission.startswith("[") and submission.endswith("]"):
                submitted_sequence = json.loads(submission)
            elif "," in submission:
                submitted_sequence = [s.strip() for s in submission.split(",") if s.strip()]
            elif submission:
                submitted_sequence = [submission]
        except Exception:
            return ChallengeResponse(status="incorrect", message="Invalid playbook sequence format.")

        expected_steps = sorted(c.steps_data, key=lambda s: int(s.get("order", 0)))
        expected_step_ids = [str(s.get("id")) for s in expected_steps]
        distractor_ids = set([str(d.get("id")) for d in c.distractors_data])

        submitted_sequence = [str(s) for s in submitted_sequence]
        submitted_distractors = [str(d) for d in submitted_distractors]

        # Verify no distractors are included in the sequence
        for s_id in submitted_sequence:
            if s_id in distractor_ids:
                return ChallengeResponse(
                    status="incorrect",
                    message="Prohibited / non-process step included in the incident response timeline!"
                )

        # Check sequence length
        if len(submitted_sequence) < len(expected_step_ids):
            missing = len(expected_step_ids) - len(submitted_sequence)
            return ChallengeResponse(
                status="incorrect",
                message=f"Playbook incomplete. {missing} mandatory step(s) missing from timeline."
            )

        # Check sequence exact ordering
        if submitted_sequence == expected_step_ids:
            # If distractor bin is enforced, check that distractors were rejected
            if c.allow_distractor_bin and distractor_ids:
                if set(submitted_distractors) != distractor_ids and len(submitted_distractors) < len(distractor_ids):
                    return ChallengeResponse(
                        status="incorrect",
                        message="Playbook order is correct, but unclassified prohibited actions remain!"
                    )

            return ChallengeResponse(
                status="correct",
                message="Incident Response Playbook Sequence Verified! All containment and eradication procedures in correct order."
            )
        else:
            return ChallengeResponse(
                status="incorrect",
                message="Incorrect sequence ordering. Re-evaluate procedural dependencies."
            )
