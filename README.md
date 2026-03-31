# CTFd Attempts Remover — v4.0

> **CTFd plugin** — lets teams request a full challenge unblock or a single extra attempt on challenges where they've exhausted all attempts.  
> Admin panel with audit logs, configurable point penalties, per-challenge exclusions, and Discord webhook notifications.

---

## What's new in v4.0

### Backend (`models.py`)

| Before | After |
|--------|-------|
| No SQL indexes | Explicit indexes on every FK column (`team_id`, `challenge_id`, `admin_id`) — critical for large CTFs |
| `nullable=False` on FK columns that reference deletable rows | `ondelete="CASCADE"` / `ondelete="SET NULL"` where appropriate, avoiding orphan rows |
| Cost stored only in the `Awards` table — required a secondary query to display it | `cost` column on `UnblockLog` / `SingleAttemptLog` — one query to display everything |
| No `to_dict()` helpers | `to_dict()` on every model — routes just call it, no repeated serialisation logic |
| Naive `datetime` (no timezone info) | `DateTime(timezone=True)` — portable across SQLite and PostgreSQL |

### Backend (`routes.py`)

| Before | After |
|--------|-------|
| N+1 award query in `/unblock_logs` (one `Awards.query` per log row) | Cost written at action time — zero extra queries in the log endpoint |
| N×M loop with individual `COUNT` queries in `/admin_blocked` | Fully batched — 3 aggregate queries cover all teams × all challenges |
| No solved-challenge filter in `/admin_blocked` | Batch `DISTINCT` query excludes already-solved entries |
| Repeated `get_config` / `set_config` blocks | `_get_plugin_config()` helper — single source of truth |
| Repeated cost-calculation code | `_compute_cost()` helper |
| Repeated penalty-award creation | `_apply_penalty()` helper |
| `/unblock_logs` limited to last 50 records (hardcoded) | Paginated: `?page=1&per_page=50` (max 200) |
| No stats endpoint | `GET /api/v1/attempts_remover/stats` — totals for dashboard widgets |
| No deny endpoint | `POST /api/v1/attempts_remover/admin_deny_request` — reject without unblocking |
| `return jsonify([])` on unauthenticated calls without a clear error | Consistent `{"success": false, "error": "..."}` on all failures |
| `request.get_json()` raises on missing body | `request.get_json(silent=True) or {}` — never raises |
| HTTP 400 on duplicate request (IntegrityError) | HTTP 409 Conflict |
| `notify_on_grant` Discord notification missing | Optional `notify_on_grant` config key — fires `notify_unblock_done` on approval |

### Backend (`discord.py`)

| Before | After |
|--------|-------|
| Single HTTP attempt, no retry | Up to 3 attempts with exponential back-off (1 s → 2 s → 4 s) |
| No rate-limit handling | Reads `retry_after` from Discord 429 response and sleeps accordingly |
| `notify_request` only | Added `notify_unblock_done` — admin approval notification with penalty details |
| `send_test_message` / `notify_request` duplicated URL validation | Shared `_get_webhook()` helper — single validation path |
| Bare `logger.warning` with `exc` only | Structured messages with attempt counts |

### Frontend (`settingsremover.js`)

| Before | After |
|--------|-------|
| Script-level variables leaking to `window` | Wrapped in an IIFE — zero global pollution |
| `fetch` calls without error handling | Central `api()` helper — always resolves, never throws |
| CSS injected as a raw string inside a `style.innerHTML` assignment | `injectStyle(id, css)` helper — idempotent, never duplicates |
| Button re-created on each call | Guard: `document.getElementById("btn-unblock-wrapper")` check |
| Challenge matching by text content only | Matches by `data-challenge-id` first, then name (more robust) |
| `remover-blocked` class not namespaced | Class renamed `remover-blocked` to avoid collisions with CTFd styles |
| Old `blocked` class could conflict with Bootstrap | Namespaced to `remover-blocked` |
| `MutationObserver` always called `fetch` | Debounced schedule — max one API call per 800 ms burst |
| Cache invalidated only by time or button count | Cache also invalidated on forced refresh (`focus` event) |

---

## API reference (v4.0)

### User endpoints (authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/attempts_remover/config` | Plugin config (costs, features) |
| GET | `/api/v1/attempts_remover/blocked` | Challenges the current team is blocked on |
| GET | `/api/v1/attempts_remover/my_requests` | Pending full-unblock requests |
| GET | `/api/v1/attempts_remover/my_single_requests` | Pending single-attempt requests |
| GET | `/api/v1/attempts_remover/my_history` | Approved unblock history |
| POST | `/api/v1/attempts_remover/request_support` | Submit a full-unblock request |
| POST | `/api/v1/attempts_remover/request_single_attempt` | Submit a single-attempt request |

### Admin endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/v1/attempts_remover/config` | Read / write plugin configuration |
| GET | `/api/v1/attempts_remover/stats` | **NEW** Aggregate statistics |
| GET | `/api/v1/attempts_remover/admin_blocked` | All blocked (team, challenge) pairs |
| GET | `/api/v1/attempts_remover/unblock_logs` | Paginated audit log (`?page=&per_page=`) |
| POST | `/api/v1/attempts_remover/admin_unblock` | Grant full unblock |
| POST | `/api/v1/attempts_remover/admin_grant_single_attempt` | Grant single extra attempt |
| POST | `/api/v1/attempts_remover/admin_deny_request` | **NEW** Deny a pending request |
| GET | `/api/v1/attempts_remover/all_challenges` | All challenges with exclusion state |
| GET | `/api/v1/attempts_remover/excluded_challenges` | Currently excluded challenges |
| POST | `/api/v1/attempts_remover/exclude_challenge` | Exclude a challenge |
| POST | `/api/v1/attempts_remover/include_challenge` | Re-include a challenge |
| GET/POST | `/api/v1/attempts_remover/discord_config` | Discord webhook configuration |
| POST | `/api/v1/attempts_remover/discord_test` | Send a test Discord notification |

---

## Installation

```
CTFd/
└── plugins/
    └── ctfd-attempts-remover/   ← this directory
        ├── __init__.py
        ├── models.py
        ├── routes.py
        ├── discord.py
        ├── config.json
        ├── assets/
        │   ├── remover_i18n.js
        │   └── settingsremover.js
        └── templates/
            ├── ctfd_attempts_remover_admin.html
            └── ctfd_attempts_remover_unblock.html
```

Restart CTFd — `db.create_all()` in `load()` will create any missing tables automatically.

---

## Configuration keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `attempts_remover:mode` | `"fixed"` \| `"percent"` | `"fixed"` | Full-unblock cost mode |
| `attempts_remover:fixed_cost` | int | `100` | Fixed point penalty per full unblock |
| `attempts_remover:percent_cost` | int 0–100 | `10` | % of challenge value penalty |
| `attempts_remover:single_attempt_enabled` | bool | `false` | Enable the single-attempt feature |
| `attempts_remover:single_attempt_mode` | `"fixed"` \| `"percent"` | `"fixed"` | Single-attempt cost mode |
| `attempts_remover:single_attempt_fixed_cost` | int | `50` | Fixed penalty per extra attempt |
| `attempts_remover:single_attempt_percent_cost` | int 0–100 | `5` | % penalty per extra attempt |
| `attempts_remover:highlight_blocked_challenges` | bool | `false` | Red-highlight locked challenge buttons |
| `attempts_remover:notify_on_grant` | bool | `false` | **NEW** Send Discord notification when admin approves |
| `attempts_remover:discord_webhook_url` | str | `""` | Discord webhook URL |
| `attempts_remover:discord_role_id` | str | `""` | Discord role to mention on new requests |
