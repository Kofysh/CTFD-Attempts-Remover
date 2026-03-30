import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests as http_requests
from CTFd.utils import get_config

logger = logging.getLogger(__name__)

_COLOR_FULL   = 0xE67E22   # orange — full unblock
_COLOR_SINGLE = 0x3498DB   # blue   — single attempt

# Only allow requests to known Discord webhook hosts to prevent SSRF.
_ALLOWED_DISCORD_HOSTS = {"discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"}


def _is_valid_discord_webhook(url: str) -> bool:
    """Return True only if *url* points to a known Discord webhook endpoint."""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.netloc in _ALLOWED_DISCORD_HOSTS
            and parsed.path.startswith("/api/webhooks/")
        )
    except Exception:
        return False


def send_test_message() -> None:
    """Send a connectivity test embed to the configured Discord webhook."""
    try:
        webhook_url = str(get_config("attempts_remover:discord_webhook_url") or "").strip()
        if not webhook_url or not _is_valid_discord_webhook(webhook_url):
            return

        embed = {
            "title": "🔌 Connection test — plugin ↔ Discord - Attempts Remover",
            "description": "✅ The webhook is correctly configured and reachable.\nThe **Attempts Remover** plugin is ready to send notifications.",
            "color": 0x2ECC71,  # green
            "footer": {"text": "Attempts Remover • CTFd"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        resp = http_requests.post(webhook_url, json={"embeds": [embed]}, timeout=5)
        if not resp.ok:
            logger.warning("Discord test webhook unexpected response %s: %s", resp.status_code, resp.text[:200])

    except Exception as exc:  # noqa: BLE001
        logger.warning("Discord test webhook failed (non-blocking): %s", exc)


def notify_request(team_name: str, challenge_name: str, challenge_value: int, request_type: str) -> None:
    """
    Send a Discord embed notification for an unblock request.

    :param team_name:       Team name
    :param challenge_name:  Challenge name
    :param challenge_value: Challenge point value
    :param request_type:    "full" or "single"
    """
    try:
        webhook_url = str(get_config("attempts_remover:discord_webhook_url") or "").strip()
        role_id     = str(get_config("attempts_remover:discord_role_id")     or "").strip()

        # Skip silently if no URL is configured or if the URL is not a valid Discord webhook.
        if not webhook_url or not _is_valid_discord_webhook(webhook_url):
            return

        is_full    = request_type == "full"
        emoji      = "🔓" if is_full else "➕"
        color      = _COLOR_FULL if is_full else _COLOR_SINGLE
        type_label = "Full unblock" if is_full else "Single attempt"

        embed = {
            "title": f"{emoji} Unblock request",
            "description": (
                f"Team **{team_name}** is requesting a "
                f"**{type_label}** on **{challenge_name}** challenge."
            ),
            "color": color,
            "fields": [
                {"name": "💎 Value", "value": f"{challenge_value} pts", "inline": True},
                {"name": "📋 Type",  "value": type_label,               "inline": True},
            ],
            "footer":    {"text": "Attempts Remover • CTFd"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        payload = {"embeds": [embed]}
        if role_id:
            payload["content"] = f"<@&{role_id}>"

        resp = http_requests.post(webhook_url, json=payload, timeout=5)
        if not resp.ok:
            logger.warning("Discord webhook unexpected response %s: %s", resp.status_code, resp.text[:200])

    except Exception as exc:  # noqa: BLE001
        logger.warning("Discord webhook failed (non-blocking): %s", exc)
