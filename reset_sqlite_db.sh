rm db.sqlite3
python manage.py syncdb --noinput
python manage.py createsuperuser --username=olivier --email=o@c.com
python manage.py runserver
