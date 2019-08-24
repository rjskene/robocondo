web: gunicorn robocondo.wsgi --log-file -
worker: celery -A robocondo worker -l info --concurrency=50