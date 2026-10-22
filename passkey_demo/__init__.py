import os
from pathlib import Path
from typing import Any

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import db, migrate
from .security import register_security_hooks

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(config_overrides: dict[str, Any] | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_path=str(BASE_DIR / "instance"),
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    Config.validate(app.config)

    if app.config["TRUST_PROXY_HEADERS"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    register_security_hooks(app)

    from .routes import bp

    app.register_blueprint(bp)

    return app
