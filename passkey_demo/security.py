from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque

from flask import Flask, current_app, jsonify, request, session

_rate_limit_buckets: dict[str, deque[float]] = defaultdict(deque)


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def register_security_hooks(app: Flask) -> None:
    @app.before_request
    def protect_state_changing_requests():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if current_app.config["RATE_LIMIT_ENABLED"]:
                rate_limit_response = _check_rate_limit()
                if rate_limit_response is not None:
                    return rate_limit_response

            if current_app.config["CSRF_PROTECT"]:
                sent_token = request.headers.get("X-CSRF-Token")
                if not sent_token or not secrets.compare_digest(sent_token, session.get("csrf_token", "")):
                    return jsonify({"ok": False, "error": "CSRF token missing or invalid."}), 400

        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'self'",
        )
        if current_app.config["IS_PRODUCTION"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def _check_rate_limit():
    window_seconds = current_app.config["RATE_LIMIT_WINDOW_SECONDS"]
    request_limit = current_app.config["RATE_LIMIT_REQUESTS"]
    now = time.monotonic()
    remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",", 1)[0].strip()
    key = f"{remote_addr}:{request.endpoint or request.path}"
    bucket = _rate_limit_buckets[key]

    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= request_limit:
        return jsonify({"ok": False, "error": "Too many requests. Try again shortly."}), 429

    bucket.append(now)
    return None
