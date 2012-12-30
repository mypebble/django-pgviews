from setuptools import setup, find_packages

setup(
    name='django-postgres',
    version='0.0.2',
    description="First-class Postgres feature support for the Django ORM.",
    author='Zachary Voase',
    author_email='z@zacharyvoase.com',
    license='Public Domain',
    packages=find_packages(),
    install_requires=[
        'bitstring',
        'Django>=1.3',
    ],
)
