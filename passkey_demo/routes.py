import json
from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .extensions import db
from .models import PasskeyCredential, User, find_credential, find_user
from .security import get_csrf_token
from .webauthn_utils import current_origin, current_rp_id, json_error

bp = Blueprint("main", __name__)


def _valid_pin(pin: object) -> bool:
    return isinstance(pin, str) and len(pin) == 6 and pin.isascii() and pin.isdigit()


@bp.get("/")
def index():
    return render_template("index.html", csrf_token=get_csrf_token(), page="home")


@bp.get("/register")
def register_page():
    return render_template("index.html", csrf_token=get_csrf_token(), page="register")


@bp.get("/login")
def login_page():
    return render_template("index.html", csrf_token=get_csrf_token(), page="login")


@bp.get("/dashboard")
def dashboard_page():
    return render_template("index.html", csrf_token=get_csrf_token(), page="dashboard")


@bp.get("/health")
def health():
    return jsonify({"ok": True, "status": "healthy"})


@bp.post("/register/options")
def register_options():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    if not username:
        return json_error("Enter a username before creating a passkey.")
    if len(username) > 120:
        return json_error("Username must be 120 characters or fewer.")

    user = find_user(username)
    if not user:
        user = User(webauthn_user_id=uuid4().bytes, username=username, display_name=username)
        db.session.add(user)
        db.session.commit()

    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
        for c in user.credentials
    ]
    options = generate_registration_options(
        rp_id=current_rp_id(),
        rp_name=current_app.config["WEBAUTHN_RP_NAME"],
        user_id=user.webauthn_user_id,
        user_name=user.username,
        user_display_name=user.display_name,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    session["register_username"] = username
    session["register_challenge"] = options.challenge.hex()
    return jsonify(json.loads(options_to_json(options)))


@bp.post("/register/verify")
def register_verify():
    payload = request.get_json(silent=True) or {}
    username = session.get("register_username")
    challenge_hex = session.get("register_challenge")
    if not username or not challenge_hex:
        return json_error("Registration session expired. Start passkey creation again.")
    user = find_user(username)
    if not user:
        return json_error("User record was not found.", 404)

    try:
        verification = verify_registration_response(
            credential=payload,
            expected_challenge=bytes.fromhex(challenge_hex),
            expected_rp_id=current_rp_id(),
            expected_origin=current_origin(),
            require_user_verification=True,
        )
    except Exception:
        current_app.logger.exception("Passkey registration verification failed")
        session.pop("register_challenge", None)
        return json_error("Registration verification failed.")

    credential_id = payload.get("id")
    if not credential_id:
        return json_error("Registration response did not include a credential ID.")
    if find_credential(credential_id):
        return json_error("This passkey is already registered.", 409)

    credential = PasskeyCredential(
        credential_id=credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        device_type=str(verification.credential_device_type),
        backed_up=verification.credential_backed_up,
        user=user,
    )
    credential.transports = payload.get("response", {}).get("transports", [])
    db.session.add(credential)
    db.session.commit()
    session.pop("register_challenge", None)
    return jsonify({"ok": True, "message": f"Passkey registered for {username}.",
                    "username": username, "credentialId": credential_id})


@bp.post("/login/options")
def login_options():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    if not username:
        return json_error("Enter a username before signing in.")
    user = find_user(username)
    if not user or not user.credentials:
        return json_error("No passkey found for this username yet.", 404)

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
        for c in user.credentials
    ]
    options = generate_authentication_options(
        rp_id=current_rp_id(), allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    session["login_username"] = username
    session["login_challenge"] = options.challenge.hex()
    return jsonify(json.loads(options_to_json(options)))


@bp.post("/login/verify")
def login_verify():
    payload = request.get_json(silent=True) or {}
    username = session.get("login_username")
    challenge_hex = session.get("login_challenge")
    if not username or not challenge_hex:
        return json_error("Login session expired. Start sign-in again.")
    user = find_user(username)
    if not user:
        return json_error("User record was not found.", 404)

    credential_id = payload.get("id")
    stored_credential = find_credential(credential_id) if credential_id else None
    if not stored_credential:
        return json_error("Stored credential details are missing.", 404)
    if stored_credential.user_id != user.id:
        return json_error("That passkey is not registered for this user.", 404)

    try:
        verification = verify_authentication_response(
            credential=payload,
            expected_challenge=bytes.fromhex(challenge_hex),
            expected_rp_id=current_rp_id(),
            expected_origin=current_origin(),
            credential_public_key=stored_credential.public_key,
            credential_current_sign_count=stored_credential.sign_count,
            require_user_verification=True,
        )
    except Exception:
        current_app.logger.exception("Passkey authentication verification failed")
        session.pop("login_challenge", None)
        return json_error("Authentication verification failed.")

    stored_credential.sign_count = verification.new_sign_count
    stored_credential.device_type = str(verification.credential_device_type)
    stored_credential.backed_up = verification.credential_backed_up
    stored_credential.last_used_at = datetime.now(timezone.utc)
    db.session.commit()
    session["signed_in_as"] = username
    session.pop("login_challenge", None)
    return jsonify({"ok": True, "message": f"Signed in as {username}.", "username": username})


@bp.post("/pin/register")
def pin_register():
    """Create a new PIN-only demo account."""
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    pin = payload.get("pin")
    if not username or len(username) > 120:
        return json_error("Enter a username of 1–120 characters.")
    if not _valid_pin(pin):
        return json_error("PIN must contain exactly 6 digits.")
    if find_user(username):
        return json_error("That username already exists. Sign in first, then set a PIN.", 409)

    user = User(
        webauthn_user_id=uuid4().bytes,
        username=username,
        display_name=username,
        pin_hash=generate_password_hash(pin),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"ok": True, "message": f"PIN account created for {username}. You can now sign in.",
                    "username": username}), 201


@bp.post("/pin/login")
def pin_login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    pin = payload.get("pin")
    if not username or not _valid_pin(pin):
        return json_error("Enter a username and a valid 6-digit PIN.")
    user = find_user(username)
    if not user or not user.pin_hash or not check_password_hash(user.pin_hash, pin):
        return json_error("Invalid username or PIN.", 401)
    # Preserve the CSRF token used by the already-open page.
    session["signed_in_as"] = username
    session.pop("login_challenge", None)
    return jsonify({"ok": True, "message": f"Signed in as {username} using PIN.", "username": username})


@bp.post("/pin/set")
def pin_set():
    username = session.get("signed_in_as")
    if not username:
        return json_error("Sign in with a passkey or PIN before setting a PIN.", 401)
    user = find_user(username)
    if not user:
        session.clear()
        return json_error("User record was not found.", 404)
    payload = request.get_json(silent=True) or {}
    pin = payload.get("pin")
    if not _valid_pin(pin):
        return json_error("PIN must contain exactly 6 digits.")
    user.pin_hash = generate_password_hash(pin)
    db.session.commit()
    return jsonify({"ok": True, "message": "PIN saved successfully.", "username": username})


@bp.get("/state")
def state():
    signed_in_as = session.get("signed_in_as")
    users = db.session.execute(db.select(User).order_by(User.username)).scalars()
    stored_users = {
        user.username: {"credential_count": len(user.credentials), "has_pin": bool(user.pin_hash)}
        for user in users
    }
    return jsonify({"ok": True, "signedInAs": signed_in_as, "users": stored_users})


@bp.get("/passkeys")
def passkeys():
    username = session.get("signed_in_as")
    if not username:
        return json_error("Sign in before managing passkeys.", 401)
    user = find_user(username)
    if not user:
        session.pop("signed_in_as", None)
        return json_error("User record was not found.", 404)
    return jsonify({"ok": True, "username": username,
                    "passkeys": [_serialize_passkey(c) for c in user.credentials]})


@bp.delete("/passkeys/<int:credential_id>")
def delete_passkey(credential_id: int):
    username = session.get("signed_in_as")
    if not username:
        return json_error("Sign in before managing passkeys.", 401)
    user = find_user(username)
    if not user:
        session.pop("signed_in_as", None)
        return json_error("User record was not found.", 404)
    credential = db.session.get(PasskeyCredential, credential_id)
    if not credential or credential.user_id != user.id:
        return json_error("Passkey was not found.", 404)
    # A PIN-enabled user may still sign in without a passkey; preserve the existing last-key rule.
    if len(user.credentials) <= 1:
        return json_error("Add another passkey before deleting the last one.", 400)
    db.session.delete(credential)
    db.session.commit()
    return jsonify({"ok": True, "message": "Passkey deleted."})


@bp.post("/logout")
def logout():
    session.pop("signed_in_as", None)
    session.pop("login_username", None)
    session.pop("login_challenge", None)
    session.pop("register_username", None)
    session.pop("register_challenge", None)
    # Keep csrf_token so this page can continue making protected requests.
    return jsonify({"ok": True, "message": "Signed out."})


def _serialize_passkey(credential: PasskeyCredential) -> dict:
    return {
        "id": credential.id,
        "credentialId": credential.credential_id,
        "shortId": credential.credential_id[:12],
        "deviceType": credential.device_type,
        "backedUp": credential.backed_up,
        "transports": credential.transports,
        "createdAt": credential.created_at.isoformat() if credential.created_at else None,
        "lastUsedAt": credential.last_used_at.isoformat() if credential.last_used_at else None,
    }
