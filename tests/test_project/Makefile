export DJANGO_SETTINGS_MODULE=test_project.settings
export PYTHONPATH=$(pwd)

.PHONY: test

test: .venv/bin/django-admin.py
	. .venv/bin/activate; django-admin.py test

.venv/bin/python:
	virtualenv --distribute .venv
	. .venv/bin/activate; easy_install pip

.venv/bin/django-admin.py: .venv/bin/python requirements.txt
	. .venv/bin/activate; pip install -r requirements.txt
	. .venv/bin/activate; cd ../../; python setup.py develop
