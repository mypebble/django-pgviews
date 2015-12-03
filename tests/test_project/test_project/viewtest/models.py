from django.db import models

import django_pgviews.view as django_pgviews


class TestModel(models.Model):
    """Test model with some basic data for running migrate tests against.
    """
    name = models.CharField(max_length=100)


class Superusers(django_pgviews.View):
    projection = ['auth.User.*']
    dependencies = ('viewtest.RelatedView',)
    sql = """SELECT * FROM auth_user WHERE is_superuser = TRUE;"""


class SimpleUser(django_pgviews.View):
    projection = ['auth.User.username', 'auth.User.password']
    # The row_number() window function is needed so that Django sees some kind
    # of 'id' field. We could also grab the one from `auth.User`, but this
    # seemed like more fun :)
    sql = """
    SELECT
        username,
        password,
        row_number() OVER () AS id
    FROM auth_user;"""


class RelatedView(django_pgviews.ReadOnlyView):
    sql = """SELECT id AS model_id, id FROM viewtest_testmodel"""
    model = models.ForeignKey(TestModel)


class MaterializedRelatedView(django_pgviews.ReadOnlyMaterializedView):
    sql = """SELECT id AS model_id, id FROM viewtest_testmodel"""
    model = models.ForeignKey(TestModel)
