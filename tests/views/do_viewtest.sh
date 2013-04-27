#!/bin/bash

set -e  # die on errors
set -x  # echo commands as they run

django-admin.py startproject test__views
cd test__views

virtualenv .venv
. .venv/bin/activate
pip install -r /dev/stdin <<EOF
Django
psycopg2
dj-database-url
south
EOF
(cd ../../../; python setup.py develop)

export PYTHONPATH="$(pwd):$PYTHONPATH"
export DJANGO_SETTINGS_MODULE=test__views.settings
export DATABASE_URL="postgresql://localhost/django_postgres_viewtest"
cat >> test__views/settings.py <<EOF
import dj_database_url
DATABASES = {'default': dj_database_url.config()}
INSTALLED_APPS += type(INSTALLED_APPS)(['django_postgres', 'south', 'view_myapp'])
EOF

django-admin.py startapp view_myapp
django-admin.py syncdb --noinput
cat > view_myapp/models.py <<EOF
from django.db import models
import django_postgres

class MyModel(models.Model):
    field1 = models.CharField(max_length=50, default=' ')
    field2 = models.CharField(max_length=49, default=' ')


class MyView(django_postgres.View):
    projection = ['view_myapp.MyModel.*']
    sql = '''SELECT * FROM view_myapp_mymodel'''
EOF
django-admin.py schemamigration --initial view_myapp
django-admin.py migrate view_myapp
django-admin.py sync_pgviews

# Make a breaking change
sed -i '' -E 's/field2/field3/' view_myapp/models.py

django-admin.py schemamigration --auto view_myapp
django-admin.py migrate view_myapp
django-admin.py sync_pgviews

psql -d "$DATABASE_URL" -P tuples_only -c 'SELECT * FROM view_myapp_myview;'
