from datetime import datetime, timezone

from CTFd.models import db


def _now():
    return datetime.now(timezone.utc)


class UnblockLog(db.Model):
    __tablename__ = "attempts_unblock_logs"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=_now)

    team = db.relationship("Teams", backref="unblock_logs")
    challenge = db.relationship("Challenges", backref="unblock_logs")
    admin = db.relationship("Users", backref="unblock_logs")


class UnblockRequest(db.Model):
    __tablename__ = "attempts_remover_requests"
    __table_args__ = (
        db.UniqueConstraint('team_id', 'challenge_id', name='unique_team_challenge_request'),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=_now)

    team = db.relationship("Teams", backref="attempts_remover_requests")
    challenge = db.relationship("Challenges", backref="attempts_remover_requests")


class ExcludedChallenge(db.Model):
    __tablename__ = "attempts_remover_excluded_challenges"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False, unique=True)
    excluded_at = db.Column(db.DateTime, default=_now)
    excluded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    challenge = db.relationship("Challenges", backref="exclusion_logs")
    admin = db.relationship("Users", backref="exclusion_logs")


class SingleAttemptRequest(db.Model):
    __tablename__ = "attempts_remover_single_requests"
    __table_args__ = (
        db.UniqueConstraint('team_id', 'challenge_id', name='unique_team_challenge_single_request'),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=_now)

    team = db.relationship("Teams", backref="single_attempt_requests")
    challenge = db.relationship("Challenges", backref="single_attempt_requests")


class SingleAttemptLog(db.Model):
    __tablename__ = "attempts_single_attempt_logs"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=_now)

    team = db.relationship("Teams", backref="single_attempt_logs")
    challenge = db.relationship("Challenges", backref="single_attempt_logs")
    admin = db.relationship("Users", backref="single_attempt_logs")
