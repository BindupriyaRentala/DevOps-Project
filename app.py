"""Local development entry point for the Passkey Demo."""
from passkey_demo import create_app
from passkey_demo.extensions import db

app = create_app()


if __name__ == "__main__":
    # Keep a fresh local checkout runnable without requiring a separate migration command.
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=False)
