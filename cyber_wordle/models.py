import json
from datetime import datetime
from CTFd.models import Challenges, db


class WordleChallenge(Challenges):
    __mapper_args__ = {"polymorphic_identity": "wordle"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    target_word = db.Column(db.String(32), default="CYBER")
    word_length = db.Column(db.Integer, default=5)
    max_attempts = db.Column(db.Integer, default=6)
    dictionary_enforced = db.Column(db.Boolean, default=False)
    dynamic_scoring = db.Column(db.Boolean, default=True)
    reveal_hint_after = db.Column(db.Integer, default=4)
    hint_text = db.Column(db.Text, default="")

    def __init__(self, *args, **kwargs):
        self.target_word = (kwargs.pop("target_word", "CYBER") or "CYBER").upper().strip()
        self.word_length = int(kwargs.pop("word_length", len(self.target_word)) or len(self.target_word))
        self.max_attempts = int(kwargs.pop("max_attempts", 6) or 6)
        self.dictionary_enforced = kwargs.pop("dictionary_enforced", False)
        if isinstance(self.dictionary_enforced, str):
            self.dictionary_enforced = self.dictionary_enforced.lower() in ("true", "1", "yes", "on")
        self.dynamic_scoring = kwargs.pop("dynamic_scoring", True)
        if isinstance(self.dynamic_scoring, str):
            self.dynamic_scoring = self.dynamic_scoring.lower() in ("true", "1", "yes", "on")
        self.reveal_hint_after = int(kwargs.pop("reveal_hint_after", 4) or 4)
        self.hint_text = kwargs.pop("hint_text", "")
        super(WordleChallenge, self).__init__(**kwargs)


class WordleGuess(db.Model):
    __tablename__ = "wordle_guesses"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    guess_number = db.Column(db.Integer, nullable=False)
    guess_word = db.Column(db.String(32), nullable=False)
    result_json = db.Column(db.Text, nullable=False)  # JSON array of 'correct', 'present', 'absent'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("challenge_id", "user_id", "guess_number", name="uq_wordle_user_guess"),
    )

    @property
    def evaluation(self):
        try:
            return json.loads(self.result_json)
        except Exception:
            return []
