web: gunicorn -c gunicorn.py canvas_manage_course.wsgi:application
rq: python manage.py rqworker isites_file_migration --settings=canvas_manage_course.settings.isites_migration
