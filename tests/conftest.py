
import pytest

from passkey_demo import create_app
from passkey_demo.extensions import db


@pytest.fixture()
def app():
    flask_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "CSRF_PROTECT": False,
        "RATE_LIMIT_ENABLED": False,
    })

    with flask_app.app_context():
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
