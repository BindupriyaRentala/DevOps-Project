from flask import current_app, jsonify, request


def current_origin() -> str:
    configured_origin = current_app.config.get("WEBAUTHN_ORIGIN")
    if configured_origin:
        return configured_origin.rstrip("/")

    proto = request.scheme
    host = request.host
    host_name = request.host.split(":", 1)[0]
    if host_name == "127.0.0.1":
        host = request.host.replace("127.0.0.1", "localhost", 1)
    return f"{proto}://{host}"


def current_rp_id() -> str:
    configured_rp_id = current_app.config.get("WEBAUTHN_RP_ID")
    if configured_rp_id:
        return configured_rp_id

    host_name = request.host.split(":", 1)[0]
    if host_name == "127.0.0.1":
        return "localhost"
    return host_name


def json_error(message: str, status_code: int = 400):
    return jsonify({"ok": False, "error": message}), status_code
