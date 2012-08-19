# django-postgres Test Project

To run the tests:

1.  Install Postgres. I use [Postgres.app](http://postgresapp.com/).

2.  Create a `django_postgres` database:

       $ psql
       psql (9.1.4)
       Type "help" for help.

       johndoe=# CREATE DATABASE django_postgres;
       CREATE DATABASE

3.  Run `./manage.py test`.
