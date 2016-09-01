from setuptools import setup, find_packages

LONG_DESCRIPTION = ''
try:
    LONG_DESCRIPTION = open('README.txt').read()
except:
    pass

setup(
    name='django-pgviews',
    version='0.2.0',
    description="Create and manage Postgres SQL Views in Django",
    long_description=LONG_DESCRIPTION,
    author='Scott Walton',
    author_email='scott.walton@mypebble.co.uk',
    license='Public Domain',
    packages=find_packages(),
    url='https://github.com/mypebble/django-pgviews'
)
