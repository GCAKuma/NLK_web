"""Apply private API defaults and server-only runtime grants after migrations."""
import getpass
import re

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from psycopg import sql


class Command(BaseCommand):
    help = "Secure Django tables; optionally create/update a limited runtime login. Run with the migration role."

    def add_arguments(self, parser):
        parser.add_argument("--runtime-role", default=getattr(settings, "RUNTIME_DATABASE_ROLE", ""))
        parser.add_argument("--set-password", action="store_true")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This command requires PostgreSQL.")
        role = options["runtime_role"]
        if role and not re.fullmatch(r"[a-z][a-z0-9_]{0,40}", role):
            raise CommandError("Use a lowercase PostgreSQL role name.")
        if role in {"postgres", "anon", "authenticated", "service_role", "supabase_admin"}:
            raise CommandError("Choose a dedicated application role.")
        password = None
        if options["set_password"]:
            if not role:
                raise CommandError("Specify --runtime-role when setting a password.")
            password = getpass.getpass("New runtime database password (not displayed): ")
            if len(password) < 24 or password != getpass.getpass("Repeat password: "):
                raise CommandError("Passwords must match and contain at least 24 characters.")
        tables = {model._meta.db_table for model in apps.get_models(include_auto_created=True) if model._meta.managed}
        tables.add("django_migrations")
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            owner = cursor.fetchone()[0]
            if role == owner:
                raise CommandError("Runtime and migration roles must be different.")
            cursor.execute("SELECT rolname FROM pg_roles")
            roles = {row[0] for row in cursor.fetchall()}
            if role and role not in roles:
                if not password:
                    raise CommandError("Create the runtime role first with --set-password.")
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS").format(sql.Identifier(role)))
            if role:
                cursor.execute("SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=%s", [role])
                if any(cursor.fetchone()):
                    raise CommandError("The runtime role must not have administrative privileges.")
                cursor.execute("SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s)", [role])
                if cursor.fetchone():
                    raise CommandError("Use a runtime role without inherited role memberships.")
            if password:
                cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
            public_roles = [sql.SQL("PUBLIC")] + [sql.Identifier(r) for r in ("anon", "authenticated") if r in roles]
            role_list = sql.SQL(", ").join(public_roles)
            cursor.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(role_list))
            for object_type in ("TABLES", "SEQUENCES"):
                cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON {} FROM {}").format(sql.SQL(object_type), role_list))
            existing = set(connection.introspection.table_names(cursor))
            for table in sorted(tables & existing):
                identifier = sql.Identifier("public", table)
                cursor.execute(sql.SQL("REVOKE ALL ON {} FROM {}").format(identifier, role_list))
                cursor.execute(sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(identifier))
                if role:
                    cursor.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {} TO {}").format(identifier, sql.Identifier(role)))
                    # Django's server performs user authorization. This database role
                    # is never used by the browser/Data API and may access app rows.
                    policy = sql.Identifier(f"nlk_runtime_{role}")
                    cursor.execute(sql.SQL("DROP POLICY IF EXISTS {} ON {}").format(policy, identifier))
                    cursor.execute(sql.SQL("CREATE POLICY {} ON {} TO {} USING (true) WITH CHECK (true)").format(policy, identifier, sql.Identifier(role)))
            if role:
                cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
                cursor.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {} ").format(sql.Identifier(role)))
                # Only sequences owned by application-table columns are granted.
                cursor.execute("""SELECT s.relname, t.relname FROM pg_class s
                    JOIN pg_namespace n ON n.oid=s.relnamespace
                    JOIN pg_depend d ON d.objid=s.oid AND d.deptype IN ('a','i')
                    JOIN pg_class t ON t.oid=d.refobjid
                    WHERE s.relkind='S' AND n.nspname='public'""")
                for sequence, table in cursor.fetchall():
                    if table in tables:
                        cursor.execute(sql.SQL("REVOKE ALL ON SEQUENCE {} FROM {}").format(sql.Identifier("public", sequence), role_list))
                        cursor.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE {} TO {}").format(sql.Identifier("public", sequence), sql.Identifier(role)))
        self.stdout.write(self.style.SUCCESS("Application tables secured. Credentials were not displayed."))
