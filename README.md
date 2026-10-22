PASSKEY DEMO + PIN OPTION — INSTALLATION NOTES

Files in this bundle:
  passkey_demo/models.py
  passkey_demo/routes.py
  templates/index.html

IMPORTANT BACKUP
1. Stop Flask (Ctrl+C in the terminal running it).
2. From E:\passkey-demo, back up the database file used by DATABASE_URL. If using the default SQLite URL, locate the actual passkey_demo.db file before copying it. Also copy the current models.py, routes.py, and templates\index.html to a backup folder.
3. Do not delete the database or the migrations folder.

COPY THE FILES
From the extracted bundle, copy the included passkey_demo\models.py to E:\passkey-demo\passkey_demo\models.py.
Copy passkey_demo\routes.py to E:\passkey-demo\passkey_demo\routes.py.
Copy templates\index.html to E:\passkey-demo\templates\index.html.
These are complete replacements, not snippets. Leave security.py, config.py, __init__.py, and extensions.py unchanged.

DATABASE MIGRATION
Open PowerShell in E:\passkey-demo and run:
  flask --app "passkey_demo:create_app" db migrate -m "Add PIN authentication"
Review the generated migration under migrations\versions\ and confirm it only adds the nullable pin_hash column to user. If it proposes dropping or rebuilding existing tables, do not apply it; restore backups and ask for help.
Then run:
  flask --app "passkey_demo:create_app" db upgrade

If Flask cannot locate the app, or the generated migration does not look like a simple add-column migration, stop and share the exact error/output rather than deleting migrations or using db stamp.

RUN LOCALLY
  $env:WEBAUTHN_RP_ID = "localhost"
  $env:WEBAUTHN_ORIGIN = "http://localhost:5000"
  python app.py
Open http://localhost:5000/ (use localhost, not 127.0.0.1, for WebAuthn origin matching).

TEST
1. Create a new PIN account with a new username and six digits.
2. Sign in with that username and PIN; dashboard session should update.
3. Sign out, create a passkey for a separate test username, and verify passkey sign-in still works.
4. For an existing passkey account, sign in with its passkey first and use Set or Change PIN to add the PIN option.
5. Sign out and test PIN sign-in for that account.

SECURITY NOTE
This PIN feature is intended for a local classroom demo, not a production authentication service. Six-digit PINs are low entropy. The existing per-endpoint rate limiter is helpful but in-memory and not sufficient for a public service. Use HTTPS, a strong FLASK_SECRET_KEY, persistent distributed rate limiting, lockout/monitoring, and a stronger authentication policy before exposing this app publicly.
