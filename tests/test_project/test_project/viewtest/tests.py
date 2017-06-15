from contextlib import closing

from django.contrib import auth
from django.core.management import call_command
from django.db import connection
from django.db.models import signals
from django.dispatch import receiver
from django.test import TestCase
from django_pgviews.signals import view_synced, all_views_synced

from . import models


@receiver(signals.post_migrate)
def create_test_schema(sender, app_config, **kwargs):
        command = 'CREATE SCHEMA IF NOT EXISTS {};'.format('test_schema')
        with connection.cursor() as cursor:
            cursor.execute(command)


class ViewTestCase(TestCase):
    """Run the tests to ensure the post_migrate hooks were called.
    """

    def test_views_have_been_created(self):
        """Look at the PG View table to ensure views were created.
        """
        with closing(connection.cursor()) as cur:
            cur.execute('''SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';''')

            count, = cur.fetchone()
            self.assertEqual(count, 4)

            cur.execute('''SELECT COUNT(*) FROM pg_matviews
                        WHERE matviewname LIKE 'viewtest_%';''')

            count, = cur.fetchone()
            self.assertEqual(count, 3)

            cur.execute('''SELECT COUNT(*) FROM information_schema.views
                        WHERE table_schema = 'test_schema';''')

            count, = cur.fetchone()
            self.assertEqual(count, 1)

    def test_clear_views(self):
        """Check the PG View table to see that the views were removed.
        """
        call_command('clear_pgviews', *[], **{})
        with closing(connection.cursor()) as cur:
            cur.execute('''SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';''')

            count, = cur.fetchone()
            self.assertEqual(count, 0)

            cur.execute('''SELECT COUNT(*) FROM information_schema.views
                        WHERE table_schema = 'test_schema';''')

            count, = cur.fetchone()
            self.assertEqual(count, 0)

    def test_wildcard_projection(self):
        """Wildcard projections take all fields from a projected model.
        """
        foo_user = auth.models.User.objects.create(
            username='foo', is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_superuser = models.Superusers.objects.get(username='foo')

        self.assertEqual(foo_user.id, foo_superuser.id)
        self.assertEqual(foo_user.password, foo_superuser.password)

    def test_limited_projection(self):
        """A limited projection only creates the projected fields.
        """
        foo_user = auth.models.User.objects.create(
            username='foo', is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_simple = models.SimpleUser.objects.get(username='foo')

        self.assertEqual(foo_simple.username, foo_user.username)
        self.assertEqual(foo_simple.password, foo_user.password)
        self.assertFalse(getattr(foo_simple, 'date_joined', False))

    def test_related_delete(self):
        """Test views do not interfere with deleting the models
        """
        tm = models.TestModel()
        tm.name = "Bob"
        tm.save()
        tm.delete()

    def test_materialized_view(self):
        """Test a materialized view works correctly
        """
        self.assertEqual(models.MaterializedRelatedView.objects.count(), 0,
            'Materialized view should not have anything')

        tm = models.TestModel()
        tm.name = "Bob"
        tm.save()

        self.assertEqual(models.MaterializedRelatedView.objects.count(), 0,
            'Materialized view should not have anything')

        models.MaterializedRelatedView.refresh()

        self.assertEqual(models.MaterializedRelatedView.objects.count(), 1,
            'Materialized view should have updated')

        models.MaterializedRelatedViewWithIndex.refresh(concurrently=True)

        self.assertEqual(models.MaterializedRelatedViewWithIndex.objects.count(), 1,
            'Materialized view should have updated concurrently')

    def test_signals(self):
        expected = {
            models.MaterializedRelatedView: {
                'status': 'CREATED',
                'has_changed': True,
            },
            models.Superusers: {
                'status': 'EXISTS',
                'has_changed': False,
            }
        }
        synced_views = []
        all_views_were_synced = [False]

        @receiver(view_synced)
        def on_view_synced(sender, **kwargs):
            synced_views.append(sender)
            if sender in expected:
                expected_kwargs = expected.pop(sender)
                self.assertEqual(
                    dict(expected_kwargs,
                         update=False, force=False, signal=view_synced),
                    kwargs)

        @receiver(all_views_synced)
        def on_all_views_synced(sender, **kwargs):
            all_views_were_synced[0] = True

        call_command('sync_pgviews', update=False)

        self.assertEqual(len(synced_views), 8)  # All views went through syncing
        self.assertEqual(all_views_were_synced[0], True)
        self.assertFalse(expected)


class DependantViewTestCase(TestCase):
    def test_sync_depending_views(self):
        """Test the sync_pgviews command for views that depend on other views.

        This test drops `viewtest_dependantview` and its dependencies
        and recreates them manually, thereby simulating an old state
        of the views in the db before changes to the view model's sql is made.
        Then we sync the views again and verify that everything was updated.
        """

        with closing(connection.cursor()) as cur:
            cur.execute("DROP VIEW viewtest_relatedview CASCADE;")

            cur.execute("""CREATE VIEW viewtest_relatedview as
                        SELECT id AS model_id, name FROM viewtest_testmodel;""")

            cur.execute("""CREATE VIEW viewtest_dependantview as
                        SELECT name from viewtest_relatedview;""")

            cur.execute("""SELECT name from viewtest_relatedview;""")
            cur.execute("""SELECT name from viewtest_dependantview;""")

        call_command('sync_pgviews', '--force')

        with closing(connection.cursor()) as cur:
            cur.execute("""SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';""")

            count, = cur.fetchone()
            self.assertEqual(count, 4)

            with self.assertRaises(Exception):
                cur.execute("""SELECT name from viewtest_relatedview;""")

            with self.assertRaises(Exception):
                cur.execute("""SELECT name from viewtest_dependantview;""")

    def test_sync_depending_materialized_views(self):
        """Test the sync_pgviews command for views that depend on other materialized views."""

        with closing(connection.cursor()) as cur:
            cur.execute("DROP MATERIALIZED VIEW viewtest_materializedrelatedview CASCADE;")

            cur.execute("""CREATE MATERIALIZED VIEW viewtest_materializedrelatedview as
                        SELECT id AS model_id, name FROM viewtest_testmodel;""")

            cur.execute("""CREATE MATERIALIZED VIEW viewtest_dependantmaterializedview as
                        SELECT name from viewtest_materializedrelatedview;""")

            cur.execute("""SELECT name from viewtest_materializedrelatedview;""")
            cur.execute("""SELECT name from viewtest_dependantmaterializedview;""")

        call_command('sync_pgviews', '--force')

        with closing(connection.cursor()) as cur:
            cur.execute("""SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';""")

            count, = cur.fetchone()
            self.assertEqual(count, 4)

            with self.assertRaises(Exception):
                cur.execute("""SELECT name from viewtest_materializedrelatedview;""")

            with self.assertRaises(Exception):
                cur.execute("""SELECT name from viewtest_dependantmaterializedview;""")
