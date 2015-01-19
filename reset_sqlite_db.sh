rm project/db.sqlite3
./venv/bin/python project/manage.py syncdb --noinput
./venv/bin/python project/python manage.py createsuperuser --username=tree --email=o@c.com
./venv/bin/python project/python manage.py runserver
