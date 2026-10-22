
from uuid import uuid4

import pytest

from passkey_demo import create_app
from passkey_demo.extensions import db
from passkey_demo.models import (
    PasskeyCredential,
    User,
    find_credential,
    find_user,
)
from passkey_demo.webauthn_utils import current_origin, current_rp_id


def test_index_returns_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"<html" in response.data.lower()
    assert "X-Content-Type-Options" in response.headers


@pytest.mark.parametrize(
    ("path", "page_name"),
    [
        ("/", "home"),
        ("/register", "register"),
        ("/login", "login"),
        ("/dashboard", "dashboard"),
    ],
)
def test_main_pages_render(client, path, page_name):
    response = client.get(path)

    assert response.status_code == 200
    assert f"page-{page_name}".encode() in response.data
    assert b'href="/register"' in response.data
    assert b'href="/login"' in response.data
    assert b'href="/dashboard"' in response.data


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"ok": True, "status": "healthy"}


def test_state_returns_empty_session_and_users(client):
    response = client.get("/state")

    assert response.status_code == 200
    assert response.json == {
        "ok": True,
        "signedInAs": None,
        "users": {},
    }


def test_logout_clears_auth_related_session(client):
    with client.session_transaction() as session:
        session["signed_in_as"] = "demo-user"
        session["login_username"] = "demo-user"
        session["login_challenge"] = "abc"
        session["register_username"] = "demo-user"
        session["register_challenge"] = "def"

    response = client.post("/logout")

    assert response.status_code == 200
    assert response.json == {"ok": True, "message": "Signed out."}

    with client.session_transaction() as session:
        assert "signed_in_as" not in session
        assert "login_username" not in session
        assert "login_challenge" not in session
        assert "register_username" not in session
        assert "register_challenge" not in session


def test_csrf_protects_json_posts_when_enabled():
    flask_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "CSRF_PROTECT": True,
        "RATE_LIMIT_ENABLED": False,
    })

    with flask_app.app_context():
        db.create_all()

    try:
        response = flask_app.test_client().post("/logout", json={})

        assert response.status_code == 400
        assert response.json == {
            "ok": False,
            "error": "CSRF token missing or invalid.",
        }
    finally:
        with flask_app.app_context():
            db.session.remove()
            db.drop_all()


def test_register_options_requires_username(client):
    response = client.post("/register/options", json={"username": "  "})

    assert response.status_code == 400
    assert response.json == {
        "ok": False,
        "error": "Enter a username before creating a passkey.",
    }


def test_login_options_requires_username(client):
    response = client.post("/login/options", json={})

    assert response.status_code == 400
    assert response.json == {
        "ok": False,
        "error": "Enter a username before signing in.",
    }


def test_login_options_returns_not_found_without_passkey(client, app):
    with app.app_context():
        db.session.add(
            User(
                webauthn_user_id=uuid4().bytes,
                username="demo-user",
                display_name="demo-user",
            )
        )
        db.session.commit()

    response = client.post("/login/options", json={"username": "demo-user"})

    assert response.status_code == 404
    assert response.json == {
        "ok": False,
        "error": "No passkey found for this username yet.",
    }


def test_user_and_credential_models_persist(app):
    with app.app_context():
        user = User(
            webauthn_user_id=uuid4().bytes,
            username="demo-user",
            display_name="Demo User",
        )

        credential = PasskeyCredential(
            credential_id="credential-1",
            public_key=b"public-key",
            sign_count=7,
            device_type="single_device",
            backed_up=False,
            user=user,
        )

        credential.transports = ["internal", "usb"]

        db.session.add(user)
        db.session.add(credential)
        db.session.commit()

        stored_user = find_user("demo-user")
        stored_credential = find_credential("credential-1")

        assert stored_user is not None
        assert stored_user.username == "demo-user"
        assert len(stored_user.credentials) == 1

        assert stored_credential is not None
        assert stored_credential.public_key == b"public-key"
        assert stored_credential.sign_count == 7
        assert stored_credential.transports == ["internal", "usb"]
        assert stored_credential.created_at is not None
        assert stored_credential.last_used_at is None


def test_passkey_management_requires_login(client):
    response = client.get("/passkeys")

    assert response.status_code == 401
    assert response.json == {
        "ok": False,
        "error": "Sign in before managing passkeys.",
    }


def test_passkey_management_lists_signed_in_users_credentials(client, app):
    with app.app_context():
        user = User(
            webauthn_user_id=uuid4().bytes,
            username="demo-user",
            display_name="Demo User",
        )

        credential = PasskeyCredential(
            credential_id="credential-1",
            public_key=b"public-key",
            sign_count=7,
            device_type="single_device",
            backed_up=True,
            user=user,
        )

        credential.transports = ["internal"]

        db.session.add(user)
        db.session.add(credential)
        db.session.commit()

    with client.session_transaction() as session:
        session["signed_in_as"] = "demo-user"

    response = client.get("/passkeys")

    assert response.status_code == 200
    assert response.json["ok"] is True
    assert response.json["username"] == "demo-user"
    assert response.json["passkeys"][0]["credentialId"] == "credential-1"
    assert response.json["passkeys"][0]["backedUp"] is True


def test_delete_passkey_keeps_last_passkey(client, app):
    with app.app_context():
        user = User(
            webauthn_user_id=uuid4().bytes,
            username="demo-user",
            display_name="Demo User",
        )

        credential = PasskeyCredential(
            credential_id="credential-1",
            public_key=b"public-key",
            sign_count=7,
            device_type="single_device",
            backed_up=False,
            user=user,
        )

        db.session.add(user)
        db.session.add(credential)
        db.session.commit()

        credential_id = credential.id

    with client.session_transaction() as session:
        session["signed_in_as"] = "demo-user"

    response = client.delete(f"/passkeys/{credential_id}")

    assert response.status_code == 400
    assert response.json == {
        "ok": False,
        "error": "Add another passkey before deleting the last one.",
    }


def test_production_requires_real_secret_key():
    with pytest.raises(RuntimeError, match="Set FLASK_SECRET_KEY"):
        create_app({
            "IS_PRODUCTION": True,
            "SECRET_KEY": "passkey-demo-secret",
        })


def test_webauthn_origin_and_rp_id_can_be_configured():
    flask_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WEBAUTHN_ORIGIN": "https://auth.example.com",
        "WEBAUTHN_RP_ID": "example.com",
    })

    with flask_app.test_request_context(
        "/",
        base_url="https://ignored.test",
    ):
        assert current_origin() == "https://auth.example.com"
        assert current_rp_id() == "example.com"
