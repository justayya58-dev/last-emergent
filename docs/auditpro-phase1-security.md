# AuditPro Phase 1 — Secure runtime configuration

Do not expose the application publicly until these values are configured in the backend process environment.

Required:
- `MONGO_URL`: MongoDB connection string.
- `DB_NAME`: application database name.
- `AUDITPRO_ADMIN_USERNAME`: single administrator login name (defaults to `auditpro-admin`).
- `AUDITPRO_ADMIN_PASSWORD`: strong unique password of at least 16 characters.
- `AUDITPRO_SESSION_SECRET`: cryptographically random secret of at least 32 characters. Never reuse the password.
- `CORS_ORIGINS`: comma-separated exact browser origins, without wildcard. Example for local development: `http://localhost:3000,http://localhost:5173`.

Production:
- Set `COOKIE_SECURE=true` and serve only over HTTPS.
- Set `CORS_ORIGINS` to the exact production frontend origin(s); do not include localhost unless genuinely needed.
- Keep secrets in the deployment secret manager, not in Git, frontend environment variables, logs, or screenshots.
- Rotate the administrator password and session secret if exposed. Changing the session secret invalidates existing sessions.
- Back up MongoDB before deploying the stricter required unique indexes. Resolve duplicate legacy data before startup; the backend intentionally refuses to serve traffic if a required unique index cannot be created.

Authentication:
- The frontend login exchanges credentials for an 8-hour signed session cookie with HttpOnly and SameSite=Strict.
- Login credentials are not stored in localStorage/sessionStorage.
- Logout clears the browser cookie.
- This is a single-administrator gate, not multi-user roles or a replacement for network controls. Use HTTPS and restrict database/network access.

Validation:
- Configure the same credentials in the backend runtime and test environment.
- Integration tests use `AUDITPRO_ADMIN_USERNAME` and `AUDITPRO_ADMIN_PASSWORD` from the test process to log in before protected endpoint tests.
- Do not treat Phase 1 as production-ready until backend tests, frontend typecheck/build, concurrency regression tests, and deployment-origin checks have all passed.
