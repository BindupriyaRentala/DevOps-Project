import os
from urllib.parse import urlparse


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class Config:
    IS_PRODUCTION = env_bool("FLASK_PRODUCTION")
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or "passkey-demo-secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///passkey_demo.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", IS_PRODUCTION)
    TRUST_PROXY_HEADERS = env_bool("TRUST_PROXY_HEADERS", False)
    WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID") or None
    WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Secure Passkey Auth")
    WEBAUTHN_ORIGIN = os.environ.get("WEBAUTHN_ORIGIN") or None
    CSRF_PROTECT = env_bool("CSRF_PROTECT", True)
    RATE_LIMIT_ENABLED = env_bool("RATE_LIMIT_ENABLED", True)
    RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "30"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", "1048576"))
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("PERMANENT_SESSION_LIFETIME", "3600"))

    @staticmethod
    def validate(config: dict) -> None:
        if config["IS_PRODUCTION"] and config["SECRET_KEY"] == "passkey-demo-secret":
            raise RuntimeError("Set FLASK_SECRET_KEY before running in production.")
        origin = config.get("WEBAUTHN_ORIGIN")
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise RuntimeError("WEBAUTHN_ORIGIN must be a full origin like https://example.com.")
