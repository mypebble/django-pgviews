from contextlib import closing

from django.contrib import auth
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from . import models


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
            self.assertEqual(count, 3)

            cur.execute('''SELECT COUNT(*) FROM pg_matviews
                        WHERE matviewname LIKE 'viewtest_%';''')

            count, = cur.fetchone()
            self.assertEqual(count, 1)

    def test_clear_views(self):
        """Check the PG View table to see that th eviews were removed.
        """
        call_command('clear_pgviews', *[], **{})
        with closing(connection.cursor()) as cur:
            cur.execute('''SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';''')

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
