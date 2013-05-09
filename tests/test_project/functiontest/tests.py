from django.contrib import auth
from django.core import exceptions
from django.db import connection
from django.test import TestCase

import models

from django_postgres.function import create_function


class FunctionTestCase(TestCase):
    """Test the Function API.
    """
    def test_get_counter(self):
        """Must run call on the manager before querying the result.
        """
        foo_user = auth.models.User.objects.create(
            username='foo', is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        foo_superuser = models.UserTypeCounter.objects.call(
            (True, ))

        self.assertEqual(foo_superuser.get().my_count, 1)

    def test_uncalled(self):
        """Cannot execute the statement unless you explicitly call it first
        """
        foo_user = auth.models.User.objects.create(
            username='foo', is_superuser=True)
        foo_user.set_password('blah')
        foo_user.save()

        self.assertRaises(
            exceptions.ObjectDoesNotExist,
            models.UserTypeCounter.objects.filter,
            pk=1)

    def test_create_function(self):
        """Create a function with the low-level create_function API.
        """
        field = ('a_field integer', )
        definition = 'SELECT 1 from auth_user WHERE id = $1'
        name = 'my_function (integer)'
        created = create_function(connection, name, field, definition)

        self.assertEqual(created, 'CREATED')
