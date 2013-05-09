from django.contrib import auth
from django.core import exceptions
from django.test import TestCase

import models


class FunctionTestCase(TestCase):

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
