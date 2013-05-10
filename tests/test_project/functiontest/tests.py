from django.contrib import auth
from django.core import exceptions
from django.db import connection
from django.test import TestCase

import models

from django_postgres.function import (create_function, create_functions,
    _function_exists)


class FunctionModelTestCase(TestCase):
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


class LowLeveFunctionTestCase(TestCase):
    """Low level tests for function creation.
    """
    def test_create_function(self):
        """Create a function with the low-level create_function API.
        """
        field = ('a_field integer', )
        definition = 'SELECT 1 from auth_user WHERE id = $1'
        name = 'my_function (integer)'
        created = create_function(connection, name, field, definition)

        self.assertEqual(created, 'CREATED')

    def test_update_function(self):
        """Update a function with create_function. Functions can only be
        updated if their signature matches the existing function.
        """
        field = ('a_field integer', )
        definition = 'SELECT 1 from auth_user WHERE id = $1'
        name = 'my_function (integer)'
        create_function(connection, name, field, definition)

        definition = 'SELECT 2 from auth_user WHERE id = $1'

        updated = create_function(connection, name, field, definition)

        self.assertEqual(updated, 'UPDATED')

    def test_error_function(self):
        """Error out if the user tried to update a function with an
        incompatible signature.
        """
        field = ('a_field integer', )
        definition = 'SELECT 1 from auth_user WHERE id = $1'
        name = 'my_function (integer)'
        create_function(connection, name, field, definition)

        name = 'my_function (integer, integer)'
        definition = 'SELECT 1 from auth_user WHERE id > $1 and id < $2'

        updated = create_function(connection, name, field, definition)

        self.assertEqual(updated, 'ERROR: Manually Drop This Function')

    def test_create_functions_from_models(self):
        """Create functions using the create_functions and passing the models
        module.
        """
        create_result = create_functions(models)

        for status, _, _ in create_result:
            self.assertEqual(status, 'CREATED')

        # Now check it was created
        cursor_wrapper = connection.cursor()
        cursor = cursor_wrapper.cursor
        self.assertEqual(_function_exists(cursor, 'user_type'), True)
