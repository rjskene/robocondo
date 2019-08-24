web: gunicorn robocondo.wsgi --log-file -
worker: celery -A robocondo worker -l debug --concurrency=2