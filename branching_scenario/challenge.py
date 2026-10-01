import json
from CTFd.models import Fails, Flags, Solves, db
from CTFd.plugins.challenges import BaseChallenge, ChallengeResponse
from CTFd.plugins.flags import get_flag_class
from CTFd.plugins.branching_scenario.models import BranchingScenarioChallenge
from CTFd.utils.user import get_current_user, get_current_team, is_admin


def get_default_sample_nodes():
    return {
        "start": {
            "title": "Incident Alert: Suspicious VIP Call",
            "text": "Your desk phone rings. An authoritative voice claiming to be the CFO states they are finalizing an emergency acquisition and need an immediate wire transfer override of $450,000.",
            "media_type": "audio",
            "media_url": "",
            "transcript": "Caller: 'Hello, this is Richard from Executive Finance. We need that offshore vendor authorization confirmed immediately or the contract defaults.'",
            "options": [
                {
                    "text": "Ask for urgent wire details and immediately process the override.",
                    "next_node": "bad_ending_wired",
                    "consequence": "You bypassed corporate multi-party authorization protocols."
                },
                {
                    "text": "Politely place caller on hold and initiate out-of-band verification via internal directory.",
                    "next_node": "investigate_call",
                    "consequence": "Standard operational security procedure: never trust inbound caller ID."
                }
            ]
        },
        "investigate_call": {
            "title": "Out-of-Band Channel Verification",
            "text": "You call the CFO's verified internal executive assistant. The assistant confirms the CFO is currently on an international flight with no connectivity and did not order any wire transfer.",
            "options": [
                {
                    "text": "Report the deepfake voice vishing incident to the SOC and log caller metadata.",
                    "next_node": "win",
                    "consequence": "Excellent response! SOC blocks the spoofed VoIP trunk and alerts the enterprise."
                },
                {
                    "text": "Ignore the call and resume regular work without notifying anyone.",
                    "next_node": "bad_ending_unreported",
                    "consequence": "The attacker proceeds to target another employee who falls for the pretext."
                }
            ]
        },
        "win": {
            "title": "Attack Neutralized: Enterprise Preserved",
            "text": "By following out-of-band verification and promptly notifying the SOC, you prevented a $450,000 fraud attempt. Threat intel identifies the campaign as advanced AI voice clone vishing.",
            "is_ending": True,
            "is_win": True
        },
        "bad_ending_wired": {
            "title": "Compromise: Fraud Succeeded",
            "text": "The funds were transferred to an untraceable offshore mule account. Internal Audit initiates a forensic inquiry.",
            "is_ending": True,
            "is_win": False
        },
        "bad_ending_unreported": {
            "title": "Secondary Compromise: Lateral Victim",
            "text": "Because the vishing campaign was not reported to the SOC, the attackers targeted a junior accountant 30 minutes later who approved the transfer.",
            "is_ending": True,
            "is_win": False
        }
    }


class BranchingScenarioChallengeType(BaseChallenge):
    id = "branching_scenario"
    name = "branching_scenario"
    templates = {
        "create": "/plugins/branching_scenario/assets/create.html",
        "update": "/plugins/branching_scenario/assets/update.html",
        "view": "/plugins/branching_scenario/assets/view.html",
    }
    scripts = {
        "create": "/plugins/branching_scenario/assets/create.js",
        "update": "/plugins/branching_scenario/assets/update.js",
        "view": "/plugins/branching_scenario/assets/view.js",
    }
    route = "/plugins/branching_scenario/assets/"
    challenge_model = BranchingScenarioChallenge

    @classmethod
    def read(cls, challenge):
        data = super().read(challenge)
        c = BranchingScenarioChallenge.query.filter_by(id=challenge.id).first()
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

        data.update({
            "nodes_data": c.nodes_data,
            "start_node_id": c.start_node_id or "start",
            "winning_nodes": c.winning_nodes or "win",
            "allow_restart": bool(c.allow_restart),
            "show_feedback": bool(c.show_feedback),
            "is_solved": is_solved,
            "attempts_used": attempts_used,
            "explanation": c.explanation if (is_solved or is_admin()) else "",
        })

        if is_admin():
            data["nodes_json"] = c.nodes_json

        return data

    @classmethod
    def create(cls, request):
        challenge = super().create(request)
        data = request.form or request.get_json() or {}

        c = BranchingScenarioChallenge.query.filter_by(id=challenge.id).first()
        if c:
            c.start_node_id = (data.get("start_node_id") or "start").strip()
            c.winning_nodes = (data.get("winning_nodes") or "win").strip()
            c.allow_restart = str(data.get("allow_restart", "true")).lower() in ("true", "1", "yes", "on")
            c.show_feedback = str(data.get("show_feedback", "true")).lower() in ("true", "1", "yes", "on")
            c.explanation = data.get("explanation", "").strip()

            nodes_json_val = data.get("nodes_json", "").strip()
            if not nodes_json_val:
                nodes_json_val = json.dumps(get_default_sample_nodes(), indent=2)
            c.nodes_json = nodes_json_val

            db.session.commit()

        return challenge

    @classmethod
    def update(cls, challenge, request):
        data = request.form or request.get_json() or {}

        for attr in ("start_node_id", "winning_nodes", "explanation"):
            if attr in data:
                setattr(challenge, attr, data[attr].strip())

        if "allow_restart" in data:
            challenge.allow_restart = str(data["allow_restart"]).lower() in ("true", "1", "yes", "on")

        if "show_feedback" in data:
            challenge.show_feedback = str(data["show_feedback"]).lower() in ("true", "1", "yes", "on")

        if "nodes_json" in data:
            challenge.nodes_json = data["nodes_json"].strip()

        return super().update(challenge, request)

    @classmethod
    def attempt(cls, challenge, request):
        data = request.form or request.get_json() or {}
        submission = (data.get("submission") or "").strip()

        c = BranchingScenarioChallenge.query.filter_by(id=challenge.id).first()
        if not c:
            return ChallengeResponse(status="incorrect", message="Challenge not found.")

        # Check standard Flags
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()
        for flag in flags:
            try:
                flag_class = get_flag_class(flag.type)
                if flag_class.compare(flag, submission):
                    return ChallengeResponse(status="correct", message="Scenario Completed Successfully via Flag!")
            except Exception:
                pass

        # Submission expected:
        # JSON: {"node_id": "win", "path": ["start", "investigate_call", "win"]}
        # Or simple node string: "win"
        submitted_node = ""
        submitted_path = []

        try:
            if submission.startswith("{") and submission.endswith("}"):
                obj = json.loads(submission)
                submitted_node = obj.get("node_id") or obj.get("current_node") or ""
                submitted_path = obj.get("path") or []
            elif submission.startswith("[") and submission.endswith("]"):
                submitted_path = json.loads(submission)
                if submitted_path:
                    submitted_node = submitted_path[-1]
            elif "," in submission:
                submitted_path = [s.strip() for s in submission.split(",") if s.strip()]
                if submitted_path:
                    submitted_node = submitted_path[-1]
            else:
                submitted_node = submission
        except Exception:
            return ChallengeResponse(status="incorrect", message="Invalid scenario submission format.")

        winning_set = set([w.strip().lower() for w in (c.winning_nodes or "win").split(",") if w.strip()])
        nodes = c.nodes_data

        # Enforce that if scenario nodes are defined, a valid path from start_node_id must be traversed
        if nodes:
            start_id = c.start_node_id or "start"
            if not submitted_path:
                # If only submitted_node was provided without path, allow only if start_node is already a winning node
                if submitted_node and submitted_node.lower() in winning_set and start_id.lower() in winning_set:
                    submitted_path = [start_id]
                else:
                    return ChallengeResponse(
                        status="incorrect",
                        message="A verified decision path from the incident start is required to resolve the crisis."
                    )

            if submitted_path[0] != start_id:
                return ChallengeResponse(
                    status="incorrect",
                    message="Path must begin at the designated starting scenario node."
                )

            for i in range(len(submitted_path) - 1):
                from_node = nodes.get(submitted_path[i])
                to_node_id = submitted_path[i + 1]
                if not from_node:
                    return ChallengeResponse(status="incorrect", message=f"Invalid node '{submitted_path[i]}' in path.")
                valid_nexts = [opt.get("next_node") for opt in from_node.get("options", [])]
                if to_node_id not in valid_nexts:
                    return ChallengeResponse(status="incorrect", message=f"Illegal transition from '{submitted_path[i]}' to '{to_node_id}'.")

            submitted_node = submitted_path[-1]

        if not submitted_node:
            return ChallengeResponse(status="incorrect", message="No final decision node reached.")

        if submitted_node.lower() in winning_set:
            return ChallengeResponse(
                status="correct",
                message="Scenario Completed Successfully! Crisis averted and threat eradicated."
            )
        else:
            return ChallengeResponse(
                status="incorrect",
                message=f"Incident outcome was sub-optimal ('{submitted_node}'). Restart and select safer countermeasures."
            )
