from django.contrib.auth import get_user_model
from django.core.management.commands import migrate
from django.db import connections


class Command(migrate.Command):
    def handle(self, *args, **options):
        # Get the database we're operating from
        db = options['database']
        connection = connections[db]

        # Hook for backends needing any database preparation
        connection.prepare_database()

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(1)")
            try:
                super(Command, self).handle(*args, **options)
            finally:
                cursor.execute("SELECT pg_advisory_unlock(1)")

        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(2)")
            try:
                User = get_user_model()
                if not User.objects.exists():
                    manager = User._default_manager.db_manager(db)
                    manager.create_superuser('admin', 'jon.braswell@gmail.com', 'changeme')
            finally:
                cursor.execute("SELECT pg_advisory_unlock(2)")