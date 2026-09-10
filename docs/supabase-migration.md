# Supabase database transfer

Completed 2026-09-09 from the original `nlkweb-db-1` PostgreSQL database.
The isolated SQLite redesign preview was not the source.

- Restored all 34 application tables, containing 309 records, into Supabase.
- Verified every table against the source with record counts and checksums,
  using UTF-8 and consistent text ordering.
- Preserved primary keys, relationships, account password hashes, sessions,
  migration history, and sequences. No pending Django migrations remained.
- Enabled row-level security on imported tables and removed grants to `anon`,
  `authenticated`, and `PUBLIC`. Django uses the server-side PostgreSQL
  connection; Supabase Auth does not replace Django authentication.
- The ignored local `.env` now points to Supabase and requires SSL.

The private backup directory is
`.venv/migration-backups/20260909-160624/`. It contains the original custom-format
PostgreSQL dump, its SHA-256 checksum, a ZIP of 95 uploaded files, counts, and a
verification report. These contain private data and must not be committed or
published. Keep a separate secure copy before removing the development machine.
The original Docker database remains available and was not deleted.

## Uploaded files

All 48 database file references resolve in the existing local `media/` directory.
The database transfer does not upload those files to Supabase Storage. Images,
invoices, and other uploads remain local and are also included in the backup.
Move them to persistent website storage when deploying the Django application.

## Running the application

Use normal Django settings (`config.settings.dev` locally); `ui_settings` is
the separate SQLite demo and continues to point there intentionally.
Existing Docker containers must be recreated to load the changed `.env`.
The current Compose files still start a local database dependency; it can be
removed in a dedicated deployment configuration once a hosting target is chosen.
Production uses `.env.prod` or host-provided environment variables, so configure
the Supabase `DATABASE_URL` there separately before deployment. Never put the
connection string into browser code or checked-in files.

Do not run Django's test suite against this hosted database. Use a separate
disposable database for tests. For future migrations, keep new Django tables
private from Supabase Data API roles as well.
