import json
from CTFd.models import Challenges, db


class BranchingScenarioChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "branching_scenario"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    nodes_json = db.Column(db.Text, default="{}")
    start_node_id = db.Column(db.String(64), default="start")
    winning_nodes = db.Column(db.String(256), default="win")
    allow_restart = db.Column(db.Boolean, default=True)
    show_feedback = db.Column(db.Boolean, default=True)
    explanation = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.nodes_json = kwargs.pop("nodes_json", "{}")
        self.start_node_id = kwargs.pop("start_node_id", "start")
        self.winning_nodes = kwargs.pop("winning_nodes", "win")
        self.allow_restart = kwargs.pop("allow_restart", True)
        if isinstance(self.allow_restart, str):
            self.allow_restart = self.allow_restart.lower() in ("true", "1", "yes", "on")
        self.show_feedback = kwargs.pop("show_feedback", True)
        if isinstance(self.show_feedback, str):
            self.show_feedback = self.show_feedback.lower() in ("true", "1", "yes", "on")
        self.explanation = kwargs.pop("explanation", "")
        super(BranchingScenarioChallenge, self).__init__(**kwargs)

    @property
    def nodes_data(self):
        try:
            return json.loads(self.nodes_json or "{}")
        except Exception:
            return {}

    @property
    def scenario_json(self):
        return self.nodes_json

    @property
    def scenario_text(self):
        try:
            nodes = json.loads(self.nodes_json or "{}")
            blocks = []
            for nid, nd in nodes.items():
                b = [f"[{nid}] {nd.get('title', '')}"]
                if nd.get("text"):
                    b.append(nd.get("text", ""))
                for opt in nd.get("options", []):
                    line = f"> {opt.get('text', '')} -> {opt.get('next_node', '')}"
                    if opt.get("consequence"):
                        line += f" | {opt.get('consequence', '')}"
                    b.append(line)
                blocks.append("\n".join(b))
            return "\n\n".join(blocks)
        except Exception:
            return ""
