from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests as http_requests
from CTFd.utils import get_config

logger = logging.getLogger(__name__)

_COLOR_FULL    = 0xE67E22
_COLOR_SINGLE  = 0x3498DB
_COLOR_SUCCESS = 0x2ECC71
_COLOR_DANGER  = 0xE74C3C
_ALLOWED_DISCORD_HOSTS: frozenset[str] = frozenset({
    "discord.com",
    "discordapp.com",
    "canary.discord.com",
    "ptb.discord.com",
})

_MAX_RETRIES  = 3
_RETRY_DELAYS = (1, 2, 4)

def _is_valid_discord_webhook(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.netloc in _ALLOWED_DISCORD_HOSTS
            and parsed.path.startswith("/api/webhooks/")
        )
    except Exception:  # noqa: BLE001
        return False

def _get_webhook() -> str | None:
    url = str(get_config("attempts_remover:discord_webhook_url") or "").strip()
    return url if url and _is_valid_discord_webhook(url) else None

def _post_embed(webhook_url: str, payload: dict[str, Any]) -> None:
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            resp = http_requests.post(webhook_url, json=payload, timeout=5)

            if resp.status_code == 204:
                return  # Discord returns 204 No Content on success

            if resp.status_code == 200:
                return  # Some endpoints return 200

            if resp.status_code == 429:
                retry_after = float(resp.json().get("retry_after", delay))
                logger.warning(
                    "Discord rate-limited (attempt %d/%d), retrying in %.1fs",
                    attempt, _MAX_RETRIES, retry_after,
                )
                time.sleep(retry_after)
                continue

            if resp.status_code >= 500 and attempt < _MAX_RETRIES:
                logger.warning(
                    "Discord webhook server error %d (attempt %d/%d), retrying in %ds",
                    resp.status_code, attempt, _MAX_RETRIES, delay,
                )
                time.sleep(delay)
                continue

            logger.warning(
                "Discord webhook unexpected response %d: %s",
                resp.status_code, resp.text[:200],
            )
            return

        except http_requests.exceptions.Timeout:
            logger.warning("Discord webhook timed out (attempt %d/%d)", attempt, _MAX_RETRIES)
            if attempt < _MAX_RETRIES:
                time.sleep(delay)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Discord webhook failed (non-blocking): %s", exc)
            return

    logger.warning("Discord webhook failed after %d attempts, giving up.", _MAX_RETRIES)

def notify_request(
    team_name: str,
    challenge_name: str,
    challenge_value: int,
    request_type: str,
) -> None:
    webhook_url = _get_webhook()
    if not webhook_url:
        return

    role_id   = str(get_config("attempts_remover:discord_role_id") or "").strip()
    is_full   = request_type == "full"
    emoji     = "🔓" if is_full else "➕"
    color     = _COLOR_FULL if is_full else _COLOR_SINGLE
    type_label = "Full unblock" if is_full else "Single attempt"

    embed: dict[str, Any] = {
        "title":       f"{emoji} New unblock request — {type_label}",
        "description": (
            f"Team **{team_name}** is requesting a **{type_label}** "
            f"on challenge **{challenge_name}**."
        ),
        "color": color,
        "fields": [
            {"name": "💎 Points",  "value": f"{challenge_value} pts", "inline": True},
            {"name": "📋 Type",    "value": type_label,               "inline": True},
        ],
        "footer":    {"text": "Attempts Remover • CTFd"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload: dict[str, Any] = {"embeds": [embed]}
    if role_id:
        payload["content"] = f"<@&{role_id}>"

    _post_embed(webhook_url, payload)

def notify_unblock_done(
    admin_name: str,
    team_name: str,
    challenge_name: str,
    cost: int,
    unblock_type: str,
) -> None:
    webhook_url = _get_webhook()
    if not webhook_url:
        return

    is_full    = unblock_type == "full"
    emoji      = "✅" if is_full else "🎯"
    type_label = "Full unblock" if is_full else "Extra attempt"

    embed: dict[str, Any] = {
        "title":       f"{emoji} Unblock granted — {type_label}",
        "description": (
            f"**{admin_name}** granted a **{type_label}** to team **{team_name}** "
            f"on challenge **{challenge_name}**."
        ),
        "color": _COLOR_DANGER,
        "fields": [
            {"name": "💸 Penalty", "value": f"-{cost} pts",   "inline": True},
            {"name": "📋 Type",    "value": type_label,        "inline": True},
            {"name": "👮 Admin",   "value": admin_name,        "inline": True},
        ],
        "footer":    {"text": "Attempts Remover • CTFd"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _post_embed(webhook_url, {"embeds": [embed]})

def send_test_message() -> None:
    webhook_url = _get_webhook()
    if not webhook_url:
        logger.info("Discord test skipped — no valid webhook configured.")
        return

    embed: dict[str, Any] = {
        "title":       "🔌 Connection test — Attempts Remover ↔ Discord",
        "description": (
            "✅ The webhook is correctly configured and reachable.\n"
            "The **Attempts Remover** plugin is ready to send notifications."
        ),
        "color":     _COLOR_SUCCESS,
        "footer":    {"text": "Attempts Remover • CTFd"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _post_embed(webhook_url, {"embeds": [embed]})
