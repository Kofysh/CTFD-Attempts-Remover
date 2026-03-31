from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from CTFd.models import db


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UnblockRequest(db.Model):

    __tablename__ = "attempts_remover_requests"
    __table_args__ = (
        db.UniqueConstraint("team_id", "challenge_id", name="uq_unblock_req_team_challenge"),
        db.Index("ix_unblock_req_team_id", "team_id"),
        db.Index("ix_unblock_req_challenge_id", "challenge_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    team_id      = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    timestamp    = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    team      = db.relationship("Teams",      backref=db.backref("unblock_requests",        lazy="dynamic", passive_deletes=True))
    challenge = db.relationship("Challenges", backref=db.backref("unblock_requests",        lazy="dynamic", passive_deletes=True))

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "challenge_id":    self.challenge_id,
            "challenge_name":  self.challenge.name,
            "challenge_value": self.challenge.value,
            "timestamp":       _iso(self.timestamp),
        }


class SingleAttemptRequest(db.Model):

    __tablename__ = "attempts_remover_single_requests"
    __table_args__ = (
        db.UniqueConstraint("team_id", "challenge_id", name="uq_single_req_team_challenge"),
        db.Index("ix_single_req_team_id",      "team_id"),
        db.Index("ix_single_req_challenge_id", "challenge_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    team_id      = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    timestamp    = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    team      = db.relationship("Teams",      backref=db.backref("single_attempt_requests", lazy="dynamic", passive_deletes=True))
    challenge = db.relationship("Challenges", backref=db.backref("single_attempt_requests", lazy="dynamic", passive_deletes=True))

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "challenge_id":    self.challenge_id,
            "challenge_name":  self.challenge.name,
            "challenge_value": self.challenge.value,
            "timestamp":       _iso(self.timestamp),
        }


class UnblockLog(db.Model):

    __tablename__ = "attempts_unblock_logs"
    __table_args__ = (
        db.Index("ix_unblock_log_team_id",      "team_id"),
        db.Index("ix_unblock_log_challenge_id", "challenge_id"),
        db.Index("ix_unblock_log_admin_id",     "admin_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    team_id      = db.Column(db.Integer, db.ForeignKey("teams.id",      ondelete="SET NULL"), nullable=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="SET NULL"), nullable=True)
    admin_id     = db.Column(db.Integer, db.ForeignKey("users.id",      ondelete="SET NULL"), nullable=True)
    cost         = db.Column(db.Integer, default=0, nullable=False)
    timestamp    = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    team      = db.relationship("Teams",      backref=db.backref("unblock_logs",      lazy="dynamic", passive_deletes=True))
    challenge = db.relationship("Challenges", backref=db.backref("unblock_logs",      lazy="dynamic", passive_deletes=True))
    admin     = db.relationship("Users",      backref=db.backref("admin_unblock_logs", lazy="dynamic", passive_deletes=True))

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "timestamp":       _iso(self.timestamp),
            "admin_name":      self.admin.name  if self.admin     else "—",
            "team_name":       self.team.name   if self.team      else "—",
            "challenge_name":  self.challenge.name if self.challenge else "—",
            "cost":            self.cost,
            "type":            "full",
        }


class SingleAttemptLog(db.Model):

    __tablename__ = "attempts_single_attempt_logs"
    __table_args__ = (
        db.Index("ix_single_log_team_id",      "team_id"),
        db.Index("ix_single_log_challenge_id", "challenge_id"),
        db.Index("ix_single_log_admin_id",     "admin_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    team_id      = db.Column(db.Integer, db.ForeignKey("teams.id",      ondelete="SET NULL"), nullable=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="SET NULL"), nullable=True)
    admin_id     = db.Column(db.Integer, db.ForeignKey("users.id",      ondelete="SET NULL"), nullable=True)
    cost         = db.Column(db.Integer, default=0, nullable=False)
    timestamp    = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    team      = db.relationship("Teams",      backref=db.backref("single_attempt_logs",       lazy="dynamic", passive_deletes=True))
    challenge = db.relationship("Challenges", backref=db.backref("single_attempt_logs",       lazy="dynamic", passive_deletes=True))
    admin     = db.relationship("Users",      backref=db.backref("admin_single_attempt_logs",  lazy="dynamic", passive_deletes=True))

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "timestamp":       _iso(self.timestamp),
            "admin_name":      self.admin.name     if self.admin     else "—",
            "team_name":       self.team.name      if self.team      else "—",
            "challenge_name":  self.challenge.name if self.challenge else "—",
            "cost":            self.cost,
            "type":            "single",
        }


class ExcludedChallenge(db.Model):

    __tablename__ = "attempts_remover_excluded_challenges"
    __table_args__ = (
        db.Index("ix_excluded_challenge_id", "challenge_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, unique=True)
    excluded_at  = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    excluded_by  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    challenge = db.relationship("Challenges", backref=db.backref("exclusion_entry", uselist=False, passive_deletes=True))
    admin     = db.relationship("Users",      backref=db.backref("excluded_challenges", lazy="dynamic", passive_deletes=True))

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "challenge_id":    self.challenge_id,
            "challenge_name":  self.challenge.name  if self.challenge else "—",
            "challenge_value": self.challenge.value if self.challenge else 0,
            "excluded_at":     _iso(self.excluded_at),
            "excluded_by":     self.admin.name if self.admin else "—",
        }


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
