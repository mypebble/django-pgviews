from django.db import models
import django_postgres


class UserTypeCounter(django_postgres.Function):
    """A simple class that tests the function. Can be called with
    either True or False as arguments
    """
    sql = """SELECT COUNT(*) AS my_count, CAST(1 AS BIGINT)
        FROM auth_user WHERE
        is_superuser = $1"""

    my_count = models.IntegerField()
    id = models.IntegerField(primary_key=True)

    class Meta:
        db_table = 'user_type (BOOLEAN)'
