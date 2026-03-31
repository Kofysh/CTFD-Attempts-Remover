from __future__ import annotations

import math
import re
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from CTFd.models import Awards, Challenges, Submissions, Teams, Users, db
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only, authed_only, require_verified_emails
from CTFd.utils.user import get_current_team, get_current_user

from .discord import _is_valid_discord_webhook, notify_unblock_done, notify_request, send_test_message
from .models import (
    ExcludedChallenge,
    SingleAttemptLog,
    SingleAttemptRequest,
    UnblockLog,
    UnblockRequest,
    _iso,
)

remover_bp = Blueprint(
    "attempts_remover",
    __name__,
    template_folder="templates",
    static_folder="assets",
    url_prefix="/plugins/ctfd-attempts-remover",
)

api_bp = Blueprint(
    "attempts_remover_api",
    __name__,
    url_prefix="/api/v1/attempts_remover",
)

def _get_plugin_config() -> dict[str, Any]:
    return {
        "mode":                       get_config("attempts_remover:mode") or "fixed",
        "fixed_cost":                 int(get_config("attempts_remover:fixed_cost") or 100),
        "percent_cost":               int(get_config("attempts_remover:percent_cost") or 10),
        "single_attempt_enabled":     bool(get_config("attempts_remover:single_attempt_enabled")),
        "single_attempt_mode":        get_config("attempts_remover:single_attempt_mode") or "fixed",
        "single_attempt_fixed_cost":  int(get_config("attempts_remover:single_attempt_fixed_cost") or 50),
        "single_attempt_percent_cost": int(get_config("attempts_remover:single_attempt_percent_cost") or 5),
        "highlight_blocked_challenges": bool(get_config("attempts_remover:highlight_blocked_challenges")),
        "notify_on_grant":            bool(get_config("attempts_remover:notify_on_grant")),
    }

def _compute_cost(challenge_value: int, mode: str, fixed: int, percent: int) -> int:
    if mode == "percent":
        return max(1, math.ceil(abs(challenge_value) * percent / 100))
    return fixed

def _apply_penalty(team: Teams, challenge: Challenges, label: str, cost: int) -> Awards:
    user = Users.query.filter_by(team_id=team.id).first()
    if not user:
        raise ValueError(f"No member found for team '{team.name}'")

    award = Awards(
        team_id=team.id,
        user_id=user.id,
        name=label,
        value=-cost,
        category="Penalty",
        icon="shield",
    )
    db.session.add(award)
    return award

def _get_excluded_ids() -> set[int]:
    return {e.challenge_id for e in ExcludedChallenge.query.all()}

def _check_existing_requests(team_id: int, challenge_id: int) -> tuple[bool, bool]:
    has_full   = UnblockRequest.query.filter_by(team_id=team_id, challenge_id=challenge_id).first() is not None
    has_single = SingleAttemptRequest.query.filter_by(team_id=team_id, challenge_id=challenge_id).first() is not None
    return has_full, has_single

def _delete_pending_request(model, team_id: int, challenge_id: int) -> None:
    row = model.query.filter_by(team_id=team_id, challenge_id=challenge_id).first()
    if row:
        db.session.delete(row)

@api_bp.route("/config", methods=["GET"])
@authed_only
@require_verified_emails
def get_config_route():
    return jsonify(_get_plugin_config())

@api_bp.route("/blocked", methods=["GET"])
@authed_only
@require_verified_emails
def user_blocked_challenges():
    team = get_current_team()
    user = get_current_user()
    if not team and not user:
        return jsonify([])

    is_team_mode = team is not None
    actor_id     = team.id if is_team_mode else user.id

    excluded_ids = _get_excluded_ids()
    challenges   = (
        Challenges.query
        .filter(Challenges.max_attempts > 0)
        .filter(Challenges.id.notin_(excluded_ids) if excluded_ids else True)
        .all()
    )
    chal_ids = [c.id for c in challenges]
    if not chal_ids:
        return jsonify([])

    base_q = (
        db.session.query(
            Submissions.challenge_id,
            func.count().label("cnt"),
        )
        .filter(
            Submissions.challenge_id.in_(chal_ids),
            Submissions.type == "incorrect",
        )
    )
    if is_team_mode:
        base_q = base_q.filter(Submissions.team_id == actor_id)
    else:
        base_q = base_q.filter(Submissions.user_id == actor_id)

    fail_map = {r.challenge_id: r.cnt for r in base_q.group_by(Submissions.challenge_id).all()}
    solved_q = (
        db.session.query(Submissions.challenge_id)
        .filter(
            Submissions.challenge_id.in_(chal_ids),
            Submissions.type == "correct",
        )
    )
    if is_team_mode:
        solved_q = solved_q.filter(Submissions.team_id == actor_id)
    else:
        solved_q = solved_q.filter(Submissions.user_id == actor_id)

    solved_ids = {r.challenge_id for r in solved_q.all()}

    blocked = []
    for chal in challenges:
        if chal.id in solved_ids:
            continue
        fail_count = fail_map.get(chal.id, 0)
        if fail_count >= chal.max_attempts:
            blocked.append({
                "challenge_id":   chal.id,
                "challenge_name": chal.name,
                "category":       chal.category,
                "value":          chal.value,
                "fail_count":     fail_count,
                "max_attempts":   chal.max_attempts,
            })

    return jsonify(blocked)

@api_bp.route("/my_requests", methods=["GET"])
@authed_only
@require_verified_emails
def get_my_requests():
    team = get_current_team()
    if not team:
        return jsonify([])
    return jsonify([r.to_dict() for r in UnblockRequest.query.filter_by(team_id=team.id).all()])

@api_bp.route("/my_single_requests", methods=["GET"])
@authed_only
@require_verified_emails
def get_my_single_requests():
    team = get_current_team()
    if not team:
        return jsonify([])
    return jsonify([r.to_dict() for r in SingleAttemptRequest.query.filter_by(team_id=team.id).all()])

@api_bp.route("/my_history", methods=["GET"])
@authed_only
@require_verified_emails
def get_my_unblock_history():
    team = get_current_team()
    if not team:
        return jsonify([])

    full_logs   = UnblockLog.query.filter_by(team_id=team.id).all()
    single_logs = SingleAttemptLog.query.filter_by(team_id=team.id).all()

    result = [log.to_dict() for log in full_logs] + [log.to_dict() for log in single_logs]
    result.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return jsonify(result)

@api_bp.route("/request_support", methods=["POST"])
@authed_only
@require_verified_emails
def request_support():
    data         = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    team         = get_current_team()

    if not team or not challenge_id:
        return jsonify(success=False, error="Team or challenge missing"), 400

    challenge = Challenges.query.get(challenge_id)
    if not challenge:
        return jsonify(success=False, error="Challenge not found"), 404

    if ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first():
        return jsonify(success=False, error="This challenge is excluded from the unblock system"), 403

    has_full, has_single = _check_existing_requests(team.id, challenge_id)
    if has_full:
        return jsonify(success=False, error="A full unblock request is already pending."), 409
    if has_single:
        return jsonify(success=False, error="A single attempt request is already pending."), 409

    db.session.add(UnblockRequest(team_id=team.id, challenge_id=challenge_id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Request already exists"), 409

    notify_request(team.name, challenge.name, challenge.value, "full")
    return jsonify(success=True)

@api_bp.route("/request_single_attempt", methods=["POST"])
@authed_only
@require_verified_emails
def request_single_attempt():
    data         = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    team         = get_current_team()

    if not team or not challenge_id:
        return jsonify(success=False, error="Team or challenge missing"), 400

    if not bool(get_config("attempts_remover:single_attempt_enabled")):
        return jsonify(success=False, error="Single attempt feature is disabled"), 403

    challenge = Challenges.query.get(challenge_id)
    if not challenge:
        return jsonify(success=False, error="Challenge not found"), 404

    if ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first():
        return jsonify(success=False, error="This challenge is excluded from the unblock system"), 403

    has_full, has_single = _check_existing_requests(team.id, challenge_id)
    if has_full:
        return jsonify(success=False, error="A full unblock request is already pending."), 409
    if has_single:
        return jsonify(success=False, error="A single attempt request is already pending."), 409

    db.session.add(SingleAttemptRequest(team_id=team.id, challenge_id=challenge_id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="Request already exists"), 409

    notify_request(team.name, challenge.name, challenge.value, "single")
    return jsonify(success=True)

@api_bp.route("/config", methods=["POST"])
@admins_only
def set_config_route():
    data = request.get_json(silent=True) or {}

    mode               = data.get("mode", "fixed")
    single_attempt_mode = data.get("single_attempt_mode", "fixed")
    if mode not in ("fixed", "percent"):
        return jsonify(success=False, error="Invalid mode: must be 'fixed' or 'percent'"), 400
    if single_attempt_mode not in ("fixed", "percent"):
        return jsonify(success=False, error="Invalid single_attempt_mode: must be 'fixed' or 'percent'"), 400

    try:
        fixed_cost                  = int(data.get("fixed_cost", 100))
        percent_cost                = int(data.get("percent_cost", 10))
        single_attempt_fixed_cost   = int(data.get("single_attempt_fixed_cost", 50))
        single_attempt_percent_cost = int(data.get("single_attempt_percent_cost", 5))
    except (TypeError, ValueError):
        return jsonify(success=False, error="Cost values must be integers"), 400

    validations = [
        (0 <= fixed_cost <= 100_000,               "fixed_cost must be between 0 and 100000"),
        (0 <= percent_cost <= 100,                  "percent_cost must be between 0 and 100"),
        (0 <= single_attempt_fixed_cost <= 100_000, "single_attempt_fixed_cost must be between 0 and 100000"),
        (0 <= single_attempt_percent_cost <= 100,   "single_attempt_percent_cost must be between 0 and 100"),
    ]
    for ok, msg in validations:
        if not ok:
            return jsonify(success=False, error=msg), 400

    set_config("attempts_remover:mode",                        mode)
    set_config("attempts_remover:fixed_cost",                  fixed_cost)
    set_config("attempts_remover:percent_cost",                percent_cost)
    set_config("attempts_remover:single_attempt_enabled",      bool(data.get("single_attempt_enabled", False)))
    set_config("attempts_remover:single_attempt_mode",         single_attempt_mode)
    set_config("attempts_remover:single_attempt_fixed_cost",   single_attempt_fixed_cost)
    set_config("attempts_remover:single_attempt_percent_cost", single_attempt_percent_cost)
    set_config("attempts_remover:highlight_blocked_challenges", bool(data.get("highlight_blocked_challenges", False)))
    set_config("attempts_remover:notify_on_grant",             bool(data.get("notify_on_grant", False)))

    return jsonify(success=True)

@api_bp.route("/admin_blocked", methods=["GET"])
@admins_only
def get_all_blocked_teams():
    excluded_ids   = _get_excluded_ids()
    full_requests  = {(r.team_id, r.challenge_id) for r in UnblockRequest.query.all()}
    single_requests = {(r.team_id, r.challenge_id) for r in SingleAttemptRequest.query.all()}

    challenges = Challenges.query.filter(Challenges.max_attempts > 0).all()
    teams      = Teams.query.all()
    count_rows = (
        db.session.query(
            Submissions.team_id,
            Submissions.challenge_id,
            func.count().label("fail_count"),
        )
        .filter(Submissions.type == "incorrect")
        .group_by(Submissions.team_id, Submissions.challenge_id)
        .all()
    )
    count_map = {(r.team_id, r.challenge_id): r.fail_count for r in count_rows}
    first_fail_rows = (
        db.session.query(
            Submissions.team_id,
            Submissions.challenge_id,
            func.min(Submissions.date).label("first_fail"),
        )
        .filter(Submissions.type == "incorrect")
        .group_by(Submissions.team_id, Submissions.challenge_id)
        .all()
    )
    first_fail_map = {(r.team_id, r.challenge_id): r.first_fail for r in first_fail_rows}
    solved_rows = (
        db.session.query(Submissions.team_id, Submissions.challenge_id)
        .filter(Submissions.type == "correct")
        .distinct()
        .all()
    )
    solved_set = {(r.team_id, r.challenge_id) for r in solved_rows}

    all_blocks = []
    for team in teams:
        for chal in challenges:
            if (team.id, chal.id) in solved_set:
                continue
            fail_count = count_map.get((team.id, chal.id), 0)
            if fail_count < chal.max_attempts:
                continue

            all_blocks.append({
                "team_id":                 team.id,
                "team_name":               team.name,
                "challenge_id":            chal.id,
                "challenge_name":          chal.name,
                "category":                chal.category,
                "fail_count":              fail_count,
                "max_attempts":            chal.max_attempts,
                "value":                   chal.value,
                "requested":               (team.id, chal.id) in full_requests,
                "single_attempt_requested": (team.id, chal.id) in single_requests,
                "is_excluded":             chal.id in excluded_ids,
                "blocked_date":            _iso(first_fail_map.get((team.id, chal.id))),
            })
    all_blocks.sort(key=lambda x: x["blocked_date"] or "", reverse=True)
    return jsonify(all_blocks)

@api_bp.route("/unblock_logs", methods=["GET"])
@admins_only
def get_unblock_logs():
    page     = max(1, request.args.get("page", 1, type=int))
    per_page = min(200, max(1, request.args.get("per_page", 50, type=int)))

    full_logs   = UnblockLog.query.order_by(UnblockLog.timestamp.desc()).all()
    single_logs = SingleAttemptLog.query.order_by(SingleAttemptLog.timestamp.desc()).all()

    all_logs = sorted(
        [l.to_dict() for l in full_logs] + [l.to_dict() for l in single_logs],
        key=lambda x: x["timestamp"] or "",
        reverse=True,
    )

    total  = len(all_logs)
    start  = (page - 1) * per_page
    end    = start + per_page
    return jsonify({
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    math.ceil(total / per_page) if total else 1,
        "logs":     all_logs[start:end],
    })

@api_bp.route("/stats", methods=["GET"])
@admins_only
def get_stats():
    total_blocked = (
        db.session.query(func.count())
        .select_from(Submissions)
        .filter(Submissions.type == "incorrect")
        .scalar()
    )
    total_full_unblocks   = UnblockLog.query.count()
    total_single_unblocks = SingleAttemptLog.query.count()
    pending_full          = UnblockRequest.query.count()
    pending_single        = SingleAttemptRequest.query.count()
    excluded_count        = ExcludedChallenge.query.count()

    total_penalties = (
        db.session.query(func.coalesce(func.sum(UnblockLog.cost), 0)).scalar()
        + db.session.query(func.coalesce(func.sum(SingleAttemptLog.cost), 0)).scalar()
    )

    return jsonify({
        "pending_full_requests":    pending_full,
        "pending_single_requests":  pending_single,
        "total_full_unblocks":      total_full_unblocks,
        "total_single_unblocks":    total_single_unblocks,
        "total_penalties_applied":  int(total_penalties),
        "excluded_challenges":      excluded_count,
    })

@api_bp.route("/admin_unblock", methods=["POST"])
@admins_only
def force_unblock_team():
    data         = request.get_json(silent=True) or {}
    team_id      = data.get("team_id")
    challenge_id = data.get("challenge_id")

    if not team_id or not challenge_id:
        return jsonify(success=False, error="Missing parameters: team_id and challenge_id required"), 400

    team      = Teams.query.get(team_id)
    challenge = Challenges.query.get(challenge_id)
    if not team or not challenge:
        return jsonify(success=False, error="Team or challenge not found"), 404

    if Submissions.query.filter_by(team_id=team_id, challenge_id=challenge_id, type="correct").first():
        return jsonify(success=False, error="Challenge already solved by this team"), 409

    fails = Submissions.query.filter_by(team_id=team_id, challenge_id=challenge_id, type="incorrect").all()
    if not fails:
        return jsonify(success=False, error="No incorrect attempts to remove"), 400

    for f in fails:
        db.session.delete(f)

    cfg  = _get_plugin_config()
    cost = _compute_cost(challenge.value, cfg["mode"], cfg["fixed_cost"], cfg["percent_cost"])

    try:
        _apply_penalty(team, challenge, f"Challenge Unblock - {challenge.name}", cost)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(success=False, error=str(exc)), 400

    admin = get_current_user()
    db.session.add(UnblockLog(
        team_id=team_id,
        challenge_id=challenge_id,
        admin_id=admin.id if admin else None,
        cost=cost,
    ))

    _delete_pending_request(UnblockRequest, team_id, challenge_id)
    db.session.commit()

    if cfg.get("notify_on_grant"):
        notify_unblock_done(
            admin_name=admin.name if admin else "Admin",
            team_name=team.name,
            challenge_name=challenge.name,
            cost=cost,
            unblock_type="full",
        )

    return jsonify(success=True, removed=len(fails), cost=cost, challenge=challenge.name)

@api_bp.route("/admin_grant_single_attempt", methods=["POST"])
@admins_only
def grant_single_attempt():
    data         = request.get_json(silent=True) or {}
    team_id      = data.get("team_id")
    challenge_id = data.get("challenge_id")

    if not team_id or not challenge_id:
        return jsonify(success=False, error="Missing parameters: team_id and challenge_id required"), 400

    team      = Teams.query.get(team_id)
    challenge = Challenges.query.get(challenge_id)
    if not team or not challenge:
        return jsonify(success=False, error="Team or challenge not found"), 404

    if Submissions.query.filter_by(team_id=team_id, challenge_id=challenge_id, type="correct").first():
        return jsonify(success=False, error="Challenge already solved by this team"), 409

    last_fail = (
        Submissions.query
        .filter_by(team_id=team_id, challenge_id=challenge_id, type="incorrect")
        .order_by(Submissions.date.desc())
        .first()
    )
    if not last_fail:
        return jsonify(success=False, error="No incorrect attempt to remove"), 400

    db.session.delete(last_fail)

    cfg  = _get_plugin_config()
    cost = _compute_cost(
        challenge.value,
        cfg["single_attempt_mode"],
        cfg["single_attempt_fixed_cost"],
        cfg["single_attempt_percent_cost"],
    )

    try:
        _apply_penalty(team, challenge, f"Extra Attempt - {challenge.name}", cost)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(success=False, error=str(exc)), 400

    admin = get_current_user()
    db.session.add(SingleAttemptLog(
        team_id=team_id,
        challenge_id=challenge_id,
        admin_id=admin.id if admin else None,
        cost=cost,
    ))

    _delete_pending_request(SingleAttemptRequest, team_id, challenge_id)
    db.session.commit()

    if cfg.get("notify_on_grant"):
        notify_unblock_done(
            admin_name=admin.name if admin else "Admin",
            team_name=team.name,
            challenge_name=challenge.name,
            cost=cost,
            unblock_type="single",
        )

    return jsonify(success=True, cost=cost, challenge=challenge.name)

@api_bp.route("/admin_deny_request", methods=["POST"])
@admins_only
def deny_request():
    data         = request.get_json(silent=True) or {}
    team_id      = data.get("team_id")
    challenge_id = data.get("challenge_id")
    req_type     = data.get("type", "full")  # "full" | "single"

    if not team_id or not challenge_id:
        return jsonify(success=False, error="Missing parameters"), 400

    model = UnblockRequest if req_type == "full" else SingleAttemptRequest
    row   = model.query.filter_by(team_id=team_id, challenge_id=challenge_id).first()
    if not row:
        return jsonify(success=False, error="Request not found"), 404

    db.session.delete(row)
    db.session.commit()
    return jsonify(success=True)

@api_bp.route("/all_challenges", methods=["GET"])
@admins_only
def get_all_challenges():
    excluded_ids = _get_excluded_ids()
    return jsonify([{
        "id":           c.id,
        "name":         c.name,
        "value":        c.value,
        "category":     c.category,
        "max_attempts": c.max_attempts,
        "excluded":     c.id in excluded_ids,
    } for c in Challenges.query.order_by(Challenges.category, Challenges.name).all()])

@api_bp.route("/excluded_challenges", methods=["GET"])
@admins_only
def get_excluded_challenges():
    return jsonify([e.to_dict() for e in ExcludedChallenge.query.all()])

@api_bp.route("/exclude_challenge", methods=["POST"])
@admins_only
def exclude_challenge():
    data         = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    if not challenge_id:
        return jsonify(success=False, error="challenge_id is required"), 400

    challenge = Challenges.query.get(challenge_id)
    if not challenge:
        return jsonify(success=False, error="Challenge not found"), 404

    if ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first():
        return jsonify(success=False, error="Challenge is already excluded"), 409

    admin = get_current_user()
    db.session.add(ExcludedChallenge(challenge_id=challenge_id, excluded_by=admin.id if admin else None))
    db.session.commit()
    return jsonify(success=True, message=f"Challenge '{challenge.name}' excluded")

@api_bp.route("/include_challenge", methods=["POST"])
@admins_only
def include_challenge():
    data         = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    if not challenge_id:
        return jsonify(success=False, error="challenge_id is required"), 400

    exclusion = ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first()
    if not exclusion:
        return jsonify(success=False, error="Challenge is not excluded"), 404

    db.session.delete(exclusion)
    db.session.commit()
    return jsonify(success=True, message="Challenge re-included")

@api_bp.route("/discord_config", methods=["GET"])
@admins_only
def get_discord_config():
    return jsonify({
        "webhook_url": get_config("attempts_remover:discord_webhook_url") or "",
        "role_id":     get_config("attempts_remover:discord_role_id") or "",
    })

@api_bp.route("/discord_config", methods=["POST"])
@admins_only
def set_discord_config():
    data        = request.get_json(silent=True) or {}
    webhook_url = (data.get("webhook_url") or "").strip()
    role_id     = (data.get("role_id") or "").strip()

    if webhook_url and not _is_valid_discord_webhook(webhook_url):
        return jsonify(
            success=False,
            error="Invalid Discord webhook URL. Must be https://discord.com/api/webhooks/…",
        ), 400

    if role_id and not re.fullmatch(r"\d{17,20}", role_id):
        return jsonify(success=False, error="Invalid Discord role ID (17–20 digit snowflake expected)"), 400

    set_config("attempts_remover:discord_webhook_url", webhook_url)
    set_config("attempts_remover:discord_role_id",     role_id)
    return jsonify(success=True)

@api_bp.route("/discord_test", methods=["POST"])
@admins_only
def test_discord_config():
    send_test_message()
    return jsonify(success=True)

@remover_bp.route("/unblock")
@authed_only
@require_verified_emails
def unblock_page():
    from flask import render_template
    return render_template("ctfd_attempts_remover_unblock.html")

@remover_bp.route("/admin")
@admins_only
def admin_page():
    from flask import render_template
    return render_template("ctfd_attempts_remover_admin.html")
