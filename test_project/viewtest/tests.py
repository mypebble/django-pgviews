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
        with closing(connection.cursor()) as cur:
            cur.execute('''SELECT COUNT(*) FROM pg_views
                        WHERE viewname LIKE 'viewtest_%';''')
            count, = cur.fetchone()
            assert count == 3

    def test_wildcard_projection(self):
        foo_user = auth.models.User.objects.create(username='foo',
                                                   is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_superuser = models.Superusers.objects.get(username='foo')

        assert foo_user.id == foo_superuser.id
        assert foo_user.password == foo_superuser.password

    def test_limited_projection(self):
        foo_user = auth.models.User.objects.create(username='foo',
                                                   is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_simple = models.SimpleUser.objects.get(username='foo')
        assert foo_simple.username == foo_user.username
        assert foo_simple.password == foo_user.password
        assert not hasattr(foo_simple, 'date_joined')

    def test_queryset_based_view(self):
        foo_user = auth.models.User.objects.create(username='foo',
                                                   is_staff=True)

        assert models.Staffness.objects.filter(username='foo').exists()


class ViewArgTestCase(ViewTestCase):
    """Pass module arguments to the View. Run the exact same tests.
    """

    def setUp(self):
        apps = ['viewtests']
        call_command('sync_pgviews', *apps)

