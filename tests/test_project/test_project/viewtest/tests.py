from contextlib import closing

from django.contrib import auth
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

import models


class ViewTestCase(TestCase):

    def setUp(self):
        call_command('sync_pgviews', *[], **{})

    def test_views_have_been_created(self):
        """Look at the PG View table to ensure views were created.
        """
        with closing(connection.cursor()) as cur:
            cur.execute('''SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';''')

            count, = cur.fetchone()
            self.assertEqual(count, 2)

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
