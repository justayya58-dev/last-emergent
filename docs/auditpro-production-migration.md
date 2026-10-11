# AuditPro production deployment and legacy-data gate

This checklist is mandatory before setting `APP_ENV=production`. A green CI run is not a production deployment certification.

## Required environment

Set secrets in the deployment secret manager; never commit real values:

- `APP_ENV=production`
- `AUDITPRO_ADMIN_USERNAME`: non-default administrator name
- `AUDITPRO_ADMIN_PASSWORD`: unique random password, at least 16 characters
- `AUDITPRO_SESSION_SECRET`: cryptographically random secret, at least 32 characters
- `COOKIE_SECURE=true`; terminate HTTPS at the trusted ingress
- `CORS_ORIGINS`: comma-separated exact HTTPS frontend origins only
- `MONGO_URL`: TLS-enabled MongoDB URI (`mongodb+srv://...` or explicit `tls=true`)
- `DB_NAME`: production database name
- `EMERGENT_LLM_KEY`: real provider key used by the Emergent integration SDK
- Never set `AUDITPRO_TEST_OCR=true` in production

The startup validator rejects missing/insecure settings. The provider key is required, but that alone does not prove provider reachability; run the smoke test below in the target environment.

## AI/OCR provider smoke test

1. Configure the actual provider key in the secret manager; do not paste it into issues or logs.
2. Upload a small, non-sensitive invoice fixture through the authenticated `/api/auditpro/documents/extract` route.
3. Confirm a provider-backed response, plausible extracted fields, and that the temporary upload file is removed on success and failure.
4. Test invalid/unsupported file type, oversized upload, provider timeout, invalid JSON response, and missing provider key. The API must fail safely without creating an approved/posted financial transaction.
5. Record provider/model, UTC time, result, and redacted request/correlation ID. Never record the key, full invoice content, tax identifiers, or bank details in logs.
6. Repeat after deploying the exact production image. CI uses deterministic test doubles and does not validate real provider credentials or network access.

## Legacy-data migration — non-destructive gate

Do not point a first production deployment at the only copy of the legacy database.

1. Freeze writes or take a consistent database snapshot.
2. Restore the snapshot to a staging database and verify row/document counts.
3. Export encrypted backups and test a restore before migration.
4. Inventory collections and schema versions; preserve original identifiers and timestamps.
5. Before enabling unique indexes, run the read-only duplicate scan from `backend/`: `python scripts/preflight_legacy_migration.py`. It reports duplicate groups without changing data. Scan every unique index in `backend/lib/db.py`, especially invoice identity, transaction/payment IDs, and tax `(source_type, source_id)`. Do not auto-delete duplicates.
6. Run a real provider smoke test against a non-sensitive fixture in staging: `python scripts/smoke_ai_ocr.py /secure/path/to/non-sensitive-invoice.pdf` with the real `EMERGENT_LLM_KEY` configured and `AUDITPRO_TEST_OCR` unset/false. This calls the configured Gemini integration, prints no extracted values, and does not replace manual field-by-field verification.
7. Produce a reconciliation report: duplicate key, document IDs, counts, and a proposed resolution owner. Resolve with an approved mapping; preserve an audit record.
8. Run index creation against staging first. The API intentionally fails startup if a required unique index cannot be created.
9. Compare counts and financial control totals before/after migration (invoice totals, paid invoice count, income/payment transaction totals, tax document counts). Investigate every variance.
10. Run the full backend suite and authenticated smoke tests against staging.
11. Schedule a maintenance window, take a fresh backup, apply the reviewed migration, verify control totals, then allow writes.
12. Keep rollback instructions and the pre-migration snapshot until sign-off. Never make an irreversible schema/data change without a tested restore path.

## Deployment controls

- HTTPS only; secure cookies; exact CORS origins.
- Private network access to MongoDB, least-privilege database credentials, TLS, backups and restore drills.
- Rotate credentials on exposure; no secrets in source control or CI logs.
- Restrict administrator access and monitor failed logins.
- This release has one administrator account, not roles or multi-user authorization.
- Have an operator verify production startup logs, index readiness, provider smoke test, and migration sign-off.

## Current evidence boundaries

GitHub Actions tests use a local MongoDB service and deterministic AI/OCR doubles. They verify application test paths, not live AI-provider connectivity, production secrets, deployment ingress, backups, or migrated legacy data. Those checks require the target environment and authorized operator.
