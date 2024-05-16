from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'circle_test',
        'USER': 'postgres',
        'PASSWORD': ':',
        'HOST': 'localhost',
        'PORT': '5432',
    },
}
