import django_pgviews


class Superusers(django_pgviews.View):
    projection = ['auth.User.*']
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
