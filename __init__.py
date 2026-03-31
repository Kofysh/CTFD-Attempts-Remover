from __future__ import annotations

import logging

from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory, register_plugin_script
from .models import (  # noqa: F401
    ExcludedChallenge,
    SingleAttemptLog,
    SingleAttemptRequest,
    UnblockLog,
    UnblockRequest,
)
from .routes import api_bp, remover_bp

logger = logging.getLogger(__name__)

_PLUGIN_NAME    = "ctfd-attempts-remover"
_ASSETS_BASE    = f"/plugins/{_PLUGIN_NAME}/assets"

def load(app) -> None:  # noqa: ANN001
    with app.app_context():
        db.create_all()
        logger.info("[%s] Database tables verified / created.", _PLUGIN_NAME)

    app.register_blueprint(remover_bp)
    app.register_blueprint(api_bp)

    register_plugin_assets_directory(app, base_path=_ASSETS_BASE)
    register_plugin_script(f"{_ASSETS_BASE}/remover_i18n.js")
    register_plugin_script(f"{_ASSETS_BASE}/settingsremover.js")

    logger.info("[%s] Plugin loaded successfully.", _PLUGIN_NAME)
