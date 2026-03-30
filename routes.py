import math
import re
from datetime import timezone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from flask import Blueprint, render_template, request, jsonify
from CTFd.utils.decorators import admins_only, authed_only, require_verified_emails
from CTFd.utils import get_config, set_config
from CTFd.utils.user import get_current_user, get_current_team
from CTFd.models import db, Challenges, Submissions, Teams, Awards, Users

from .discord import notify_request, _is_valid_discord_webhook
from .models import (
    ExcludedChallenge,
    SingleAttemptLog,
    SingleAttemptRequest,
    UnblockLog,
    UnblockRequest,
)


def _iso(dt):
    """Serialize a UTC datetime (naive or aware) to ISO 8601 with a Z suffix."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


# ── User routes ───────────────────────────────────────────────────────────────

@api_bp.route("/my_requests", methods=["GET"])
@authed_only
@require_verified_emails
def get_my_requests():
    team = get_current_team()
    if not team:
        return jsonify([])
    requests_ = UnblockRequest.query.filter_by(team_id=team.id).all()
    return jsonify([{
        "challenge_id": r.challenge_id,
        "challenge_name": r.challenge.name,
        "challenge_value": r.challenge.value,
        "timestamp": _iso(r.timestamp),
    } for r in requests_])


@api_bp.route("/my_history", methods=["GET"])
@authed_only
@require_verified_emails
def get_my_unblock_history():
    team = get_current_team()
    if not team:
        return jsonify([])

    full_logs = UnblockLog.query.filter_by(team_id=team.id).all()
    single_logs = SingleAttemptLog.query.filter_by(team_id=team.id).all()

    result = []

    for l in full_logs:
        award = Awards.query.filter_by(
            team_id=team.id,
            name=f"Challenge Unblock - {l.challenge.name}",
        ).order_by(Awards.date.desc()).first()
        result.append({
            "challenge_name": l.challenge.name,
            "timestamp": _iso(l.timestamp),
            "cost": abs(award.value) if award else 0,
            "admin_name": l.admin.name,
            "type": "full",
        })

    for l in single_logs:
        award = Awards.query.filter_by(
            team_id=team.id,
            name=f"Extra Attempt - {l.challenge.name}",
        ).order_by(Awards.date.desc()).first()
        result.append({
            "challenge_name": l.challenge.name,
            "timestamp": _iso(l.timestamp),
            "cost": abs(award.value) if award else 0,
            "admin_name": l.admin.name,
            "type": "single",
        })

    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(result)


@api_bp.route("/my_single_requests", methods=["GET"])
@authed_only
@require_verified_emails
def get_my_single_requests():
    team = get_current_team()
    if not team:
        return jsonify([])
    requests_ = SingleAttemptRequest.query.filter_by(team_id=team.id).all()
    return jsonify([{
        "challenge_id": r.challenge_id,
        "challenge_name": r.challenge.name,
        "challenge_value": r.challenge.value,
        "timestamp": _iso(r.timestamp),
    } for r in requests_])


@api_bp.route("/request_support", methods=["POST"])
@authed_only
@require_verified_emails
def request_support():
    data = request.get_json()
    challenge_id = data.get("challenge_id")
    team = get_current_team()

    if not team or not challenge_id:
        return jsonify(success=False, error="Team or challenge missing"), 400

    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify(success=False, error="Challenge not found"), 404

    if ExcludedChallenge.query.filter_by(challenge_id=challenge.id).first():
        return jsonify(success=False, error="This challenge is excluded from the unblock system"), 403

    existing_full = UnblockRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
    existing_single = SingleAttemptRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()

    if existing_full:
        return jsonify(success=False, error="A full unblock request has already been submitted."), 400
    if existing_single:
        return jsonify(success=False, error="A single attempt request has already been submitted."), 400

    req = UnblockRequest(team_id=team.id, challenge_id=challenge.id)
    db.session.add(req)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="A request already exists"), 400

    notify_request(team.name, challenge.name, challenge.value, "full")
    return jsonify(success=True)


@api_bp.route("/blocked", methods=["GET"])
@authed_only
@require_verified_emails
def user_blocked_challenges():
    team = get_current_team()
    user = get_current_user()
    if not team and not user:
        return jsonify([])

    is_team_mode = team is not None
    id_used = team.id if is_team_mode else user.id

    excluded_ids = [e.challenge_id for e in ExcludedChallenge.query.all()]

    q = Challenges.query.filter(Challenges.max_attempts > 0)
    if excluded_ids:
        q = q.filter(Challenges.id.notin_(excluded_ids))
    challenges = q.all()

    blocked = []
    for chal in challenges:
        solved_query = Submissions.query.filter_by(challenge_id=chal.id, type="correct")
        solved_query = solved_query.filter_by(team_id=id_used) if is_team_mode else solved_query.filter_by(user_id=id_used)
        if solved_query.first() is not None:
            continue

        fail_query = Submissions.query.filter_by(challenge_id=chal.id, type="incorrect")
        fail_query = fail_query.filter_by(team_id=id_used) if is_team_mode else fail_query.filter_by(user_id=id_used)
        count = fail_query.count()

        if count >= chal.max_attempts:
            blocked.append({
                "challenge_id": chal.id,
                "challenge_name": chal.name,
                "value": chal.value,
                "fail_count": count,
                "max_attempts": chal.max_attempts,
            })
    return jsonify(blocked)


@api_bp.route("/config", methods=["GET"])
@authed_only
@require_verified_emails
def get_config_route():
    return jsonify({
        "mode": get_config("attempts_remover:mode") or "fixed",
        "fixed_cost": int(get_config("attempts_remover:fixed_cost") or 100),
        "percent_cost": int(get_config("attempts_remover:percent_cost") or 10),

        "single_attempt_enabled": bool(get_config("attempts_remover:single_attempt_enabled") or False),
        "single_attempt_mode": get_config("attempts_remover:single_attempt_mode") or "fixed",
        "single_attempt_fixed_cost": int(get_config("attempts_remover:single_attempt_fixed_cost") or 50),
        "single_attempt_percent_cost": int(get_config("attempts_remover:single_attempt_percent_cost") or 5),

        "highlight_blocked_challenges": bool(get_config("attempts_remover:highlight_blocked_challenges") or False),
    })


@api_bp.route("/request_single_attempt", methods=["POST"])
@authed_only
@require_verified_emails
def request_single_attempt():
    data = request.get_json()
    challenge_id = data.get("challenge_id")
    team = get_current_team()

    if not team or not challenge_id:
        return jsonify(success=False, error="Team or challenge missing"), 400

    if not bool(get_config("attempts_remover:single_attempt_enabled")):
        return jsonify(success=False, error="Feature disabled"), 400

    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify(success=False, error="Challenge not found"), 404

    if ExcludedChallenge.query.filter_by(challenge_id=challenge.id).first():
        return jsonify(success=False, error="This challenge is excluded from the unblock system"), 403

    existing_full = UnblockRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
    existing_single = SingleAttemptRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()

    if existing_full:
        return jsonify(success=False, error="A full unblock request has already been submitted."), 400
    if existing_single:
        return jsonify(success=False, error="A single attempt request has already been submitted."), 400

    req = SingleAttemptRequest(team_id=team.id, challenge_id=challenge.id)
    db.session.add(req)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error="A request already exists"), 400

    notify_request(team.name, challenge.name, challenge.value, "single")
    return jsonify(success=True)


@remover_bp.route("/unblock")
@authed_only
@require_verified_emails
def unblock_page():
    return render_template("ctfd_attempts_remover_unblock.html")


# ── Admin routes ──────────────────────────────────────────────────────────────

@api_bp.route("/config", methods=["POST"])
@admins_only
def set_config_route():
    data = request.get_json()

    mode = data.get("mode", "fixed")
    single_attempt_mode = data.get("single_attempt_mode", "fixed")
    if mode not in ("fixed", "percent"):
        return jsonify(success=False, error="Invalid mode, must be 'fixed' or 'percent'"), 400
    if single_attempt_mode not in ("fixed", "percent"):
        return jsonify(success=False, error="Invalid single_attempt_mode, must be 'fixed' or 'percent'"), 400

    try:
        fixed_cost               = int(data.get("fixed_cost", 100))
        percent_cost             = int(data.get("percent_cost", 10))
        single_attempt_fixed_cost   = int(data.get("single_attempt_fixed_cost", 50))
        single_attempt_percent_cost = int(data.get("single_attempt_percent_cost", 5))
    except (TypeError, ValueError):
        return jsonify(success=False, error="Cost values must be integers"), 400

    if not (0 <= fixed_cost <= 100000):
        return jsonify(success=False, error="fixed_cost must be between 0 and 100000"), 400
    if not (0 <= percent_cost <= 100):
        return jsonify(success=False, error="percent_cost must be between 0 and 100"), 400
    if not (0 <= single_attempt_fixed_cost <= 100000):
        return jsonify(success=False, error="single_attempt_fixed_cost must be between 0 and 100000"), 400
    if not (0 <= single_attempt_percent_cost <= 100):
        return jsonify(success=False, error="single_attempt_percent_cost must be between 0 and 100"), 400

    set_config("attempts_remover:mode", mode)
    set_config("attempts_remover:fixed_cost", fixed_cost)
    set_config("attempts_remover:percent_cost", percent_cost)
    set_config("attempts_remover:single_attempt_enabled", data.get("single_attempt_enabled", False))
    set_config("attempts_remover:single_attempt_mode", single_attempt_mode)
    set_config("attempts_remover:single_attempt_fixed_cost", single_attempt_fixed_cost)
    set_config("attempts_remover:single_attempt_percent_cost", single_attempt_percent_cost)
    set_config("attempts_remover:highlight_blocked_challenges", data.get("highlight_blocked_challenges", False))
    return jsonify(success=True)


@api_bp.route("/unblock_logs", methods=["GET"])
@admins_only
def get_unblock_logs():
    full_logs = UnblockLog.query.all()
    single_logs = SingleAttemptLog.query.all()

    all_logs = []

    for l in full_logs:
        # Look up the penalty award created at unblock time.
        award = Awards.query.filter_by(
            team_id=l.team_id,
            name=f"Challenge Unblock - {l.challenge.name}",
        ).order_by(Awards.date.desc()).first()
        all_logs.append({
            "timestamp": _iso(l.timestamp),
            "admin_name": l.admin.name,
            "team_name": l.team.name,
            "challenge_name": l.challenge.name,
            "type": "full",
            "cost": abs(award.value) if award else 0,
        })

    for l in single_logs:
        award = Awards.query.filter_by(
            team_id=l.team_id,
            name=f"Extra Attempt - {l.challenge.name}",
        ).order_by(Awards.date.desc()).first()
        all_logs.append({
            "timestamp": _iso(l.timestamp),
            "admin_name": l.admin.name,
            "team_name": l.team.name,
            "challenge_name": l.challenge.name,
            "type": "single",
            "cost": abs(award.value) if award else 0,
        })

    all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(all_logs[:50])


@api_bp.route("/admin_blocked", methods=["GET"])
@admins_only
def get_all_blocked_teams():
    # Pre-load excluded IDs and pending requests before the loops
    excluded_ids = {e.challenge_id for e in ExcludedChallenge.query.all()}
    full_requests = {
        (r.team_id, r.challenge_id)
        for r in UnblockRequest.query.all()
    }
    single_requests = {
        (r.team_id, r.challenge_id)
        for r in SingleAttemptRequest.query.all()
    }

    challenges = Challenges.query.filter(Challenges.max_attempts > 0).all()
    teams = Teams.query.all()

    # Batch query: incorrect submission count per (team_id, challenge_id).
    # Avoids an N*M loop of individual COUNT queries.
    count_rows = (
        db.session.query(
            Submissions.team_id,
            Submissions.challenge_id,
            func.count().label("fail_count"),
        )
        .filter_by(type="incorrect")
        .group_by(Submissions.team_id, Submissions.challenge_id)
        .all()
    )
    count_map = {(r.team_id, r.challenge_id): r.fail_count for r in count_rows}

    # Batch query: earliest incorrect submission date per (team_id, challenge_id).
    first_fail_rows = (
        db.session.query(
            Submissions.team_id,
            Submissions.challenge_id,
            func.min(Submissions.date).label("first_fail"),
        )
        .filter_by(type="incorrect")
        .group_by(Submissions.team_id, Submissions.challenge_id)
        .all()
    )
    first_fail_map = {(r.team_id, r.challenge_id): r.first_fail for r in first_fail_rows}

    all_blocks = []
    for team in teams:
        for chal in challenges:
            fail_count = count_map.get((team.id, chal.id), 0)
            if fail_count < chal.max_attempts:
                continue

            first_fail_date = first_fail_map.get((team.id, chal.id))
            all_blocks.append({
                "team_id": team.id,
                "team_name": team.name,
                "challenge_id": chal.id,
                "challenge_name": chal.name,
                "fail_count": fail_count,
                "max_attempts": chal.max_attempts,
                "value": chal.value,
                "requested": (team.id, chal.id) in full_requests,
                "single_attempt_requested": (team.id, chal.id) in single_requests,
                "is_excluded": chal.id in excluded_ids,
                "blocked_date": _iso(first_fail_date) if first_fail_date else None,
            })

    return jsonify(all_blocks)


@api_bp.route("/admin_unblock", methods=["POST"])
@admins_only
def force_unblock_team():
    data = request.get_json()
    team_id = data.get("team_id")
    challenge_id = data.get("challenge_id")

    if not team_id or not challenge_id:
        return jsonify(success=False, error="Missing parameters"), 400

    team = Teams.query.filter_by(id=team_id).first()
    challenge = Challenges.query.filter_by(id=challenge_id).first()

    if not team or not challenge:
        return jsonify(success=False, error="Team or challenge not found"), 404

    already_solved = Submissions.query.filter_by(
        team_id=team.id,
        challenge_id=challenge.id,
        type="correct",
    ).first()
    if already_solved:
        return jsonify(success=False, error="This challenge is already solved by this team"), 400

    fails = Submissions.query.filter_by(
        challenge_id=challenge.id,
        team_id=team.id,
        type="incorrect",
    ).all()
    if not fails:
        return jsonify(success=False, error="No incorrect attempts to remove"), 400

    for f in fails:
        db.session.delete(f)

    mode = get_config("attempts_remover:mode") or "fixed"
    fixed_cost = int(get_config("attempts_remover:fixed_cost") or 100)
    percent_cost = int(get_config("attempts_remover:percent_cost") or 10)
    cost = fixed_cost if mode == "fixed" else max(1, math.ceil(abs(challenge.value) * percent_cost / 100))

    user = Users.query.filter_by(team_id=team.id).first()
    if not user:
        return jsonify(success=False, error="No member found for this team"), 400

    db.session.add(Awards(
        team_id=team.id,
        user_id=user.id,
        name=f"Challenge Unblock - {challenge.name}",
        value=-cost,
        category="Malus",
        icon="shield",
    ))

    admin = get_current_user()
    if admin:
        db.session.add(UnblockLog(
            team_id=team.id,
            challenge_id=challenge.id,
            admin_id=admin.id,
        ))

    existing_request = UnblockRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
    if existing_request:
        db.session.delete(existing_request)

    db.session.commit()
    return jsonify(success=True, removed=len(fails), cost=cost, challenge=challenge.name)


@api_bp.route("/admin_grant_single_attempt", methods=["POST"])
@admins_only
def grant_single_attempt():
    data = request.get_json()
    team_id = data.get("team_id")
    challenge_id = data.get("challenge_id")

    if not team_id or not challenge_id:
        return jsonify(success=False, error="Missing parameters"), 400

    team = Teams.query.filter_by(id=team_id).first()
    challenge = Challenges.query.filter_by(id=challenge_id).first()

    if not team or not challenge:
        return jsonify(success=False, error="Team or challenge not found"), 404

    already_solved = Submissions.query.filter_by(
        team_id=team.id,
        challenge_id=challenge.id,
        type="correct",
    ).first()
    if already_solved:
        return jsonify(success=False, error="This challenge is already solved by this team"), 400

    last_fail = Submissions.query.filter_by(
        challenge_id=challenge.id,
        team_id=team.id,
        type="incorrect",
    ).order_by(Submissions.date.desc()).first()
    if not last_fail:
        return jsonify(success=False, error="No incorrect attempt to remove"), 400

    db.session.delete(last_fail)

    single_mode = get_config("attempts_remover:single_attempt_mode") or "fixed"
    single_fixed_cost = int(get_config("attempts_remover:single_attempt_fixed_cost") or 50)
    single_percent_cost = int(get_config("attempts_remover:single_attempt_percent_cost") or 5)
    cost = single_fixed_cost if single_mode == "fixed" else max(1, math.ceil(abs(challenge.value) * single_percent_cost / 100))

    user = Users.query.filter_by(team_id=team.id).first()
    if not user:
        return jsonify(success=False, error="No member found for this team"), 400

    db.session.add(Awards(
        team_id=team.id,
        user_id=user.id,
        name=f"Extra Attempt - {challenge.name}",
        value=-cost,
        category="Malus",
        icon="shield",
    ))

    existing_request = SingleAttemptRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
    if existing_request:
        db.session.delete(existing_request)

    admin = get_current_user()
    if admin:
        db.session.add(SingleAttemptLog(
            team_id=team.id,
            challenge_id=challenge.id,
            admin_id=admin.id,
        ))

    db.session.commit()
    return jsonify(success=True, cost=cost, challenge=challenge.name)


@api_bp.route("/excluded_challenges", methods=["GET"])
@admins_only
def get_excluded_challenges():
    excluded = ExcludedChallenge.query.all()
    return jsonify([{
        "id": e.id,
        "challenge_id": e.challenge_id,
        "challenge_name": e.challenge.name,
        "challenge_value": e.challenge.value,
        "excluded_at": _iso(e.excluded_at),
        "excluded_by": e.admin.name,
    } for e in excluded])


@api_bp.route("/exclude_challenge", methods=["POST"])
@admins_only
def exclude_challenge():
    data = request.get_json()
    challenge_id = data.get("challenge_id")

    if not challenge_id:
        return jsonify(success=False, error="Challenge ID missing"), 400

    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify(success=False, error="Challenge not found"), 404

    if ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first():
        return jsonify(success=False, error="Challenge already excluded"), 400

    admin = get_current_user()
    db.session.add(ExcludedChallenge(challenge_id=challenge_id, excluded_by=admin.id))
    db.session.commit()
    return jsonify(success=True, message=f"Challenge '{challenge.name}' successfully excluded")


@api_bp.route("/include_challenge", methods=["POST"])
@admins_only
def include_challenge():
    data = request.get_json()
    challenge_id = data.get("challenge_id")

    if not challenge_id:
        return jsonify(success=False, error="Challenge ID missing"), 400

    exclusion = ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first()
    if not exclusion:
        return jsonify(success=False, error="Challenge not excluded"), 404

    db.session.delete(exclusion)
    db.session.commit()
    return jsonify(success=True, message="Challenge successfully re-included")


@api_bp.route("/all_challenges", methods=["GET"])
@admins_only
def get_all_challenges():
    excluded_ids = {e.challenge_id for e in ExcludedChallenge.query.all()}
    challenges = Challenges.query.all()
    return jsonify([{
        "id": c.id,
        "name": c.name,
        "value": c.value,
        "category": c.category,
        "max_attempts": c.max_attempts,
        "excluded": c.id in excluded_ids,
    } for c in challenges])


@api_bp.route("/discord_config", methods=["GET"])
@admins_only
def get_discord_config():
    return jsonify({
        "webhook_url": get_config("attempts_remover:discord_webhook_url") or "",
        "role_id": get_config("attempts_remover:discord_role_id") or "",
    })


@api_bp.route("/discord_config", methods=["POST"])
@admins_only
def set_discord_config():
    data = request.get_json()
    webhook_url = (data.get("webhook_url") or "").strip()
    # Reject non-Discord URLs to prevent SSRF via the webhook call in discord.py.
    if webhook_url and not _is_valid_discord_webhook(webhook_url):
        return jsonify(success=False, error="Invalid Discord webhook URL. Must point to discord.com or discordapp.com."), 400
    role_id = (data.get("role_id") or "").strip()
    if role_id and not re.fullmatch(r"\d{17,20}", role_id):
        return jsonify(success=False, error="Invalid Discord role ID, must be a 17-20 digit snowflake"), 400

    set_config("attempts_remover:discord_webhook_url", webhook_url)
    set_config("attempts_remover:discord_role_id", role_id)
    return jsonify(success=True)


@api_bp.route("/discord_test", methods=["POST"])
@admins_only
def test_discord_config():
    from .discord import send_test_message
    send_test_message()
    return jsonify(success=True)


@remover_bp.route("/admin")
@admins_only
def admin_page():
    return render_template("ctfd_attempts_remover_admin.html")
