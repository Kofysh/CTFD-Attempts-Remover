from CTFd.models import db
from CTFd.plugins import register_plugin_assets_directory, register_plugin_script

from .models import (  # noqa: F401 — registers the tables with SQLAlchemy
    ExcludedChallenge,
    SingleAttemptLog,
    SingleAttemptRequest,
    UnblockLog,
    UnblockRequest,
)
from .routes import api_bp, remover_bp


def load(app):
    with app.app_context():
        db.create_all()

    app.register_blueprint(remover_bp)
    app.register_blueprint(api_bp)
    register_plugin_assets_directory(app, base_path="/plugins/ctfd-attempts-remover/assets")
    register_plugin_script("/plugins/ctfd-attempts-remover/assets/remover_i18n.js")
    register_plugin_script("/plugins/ctfd-attempts-remover/assets/settingsremover.js")
