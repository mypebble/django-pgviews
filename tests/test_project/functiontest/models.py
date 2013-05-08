from django.db import models
import django_postgres


class UserTypeCounter(django_postgres.Statement):
    """A simple class that tests the prepared statement. Can be called with
    either True or False as arguments
    """
    sql = """SELECT COUNT(*) AS my_count FROM auth_user WHERE
        is_superuser = $1;"""

    my_count = models.IntegerField()

    class Meta:
        db_table = 'user_type (BOOLEAN)'
