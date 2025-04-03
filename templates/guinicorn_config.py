import os

workers = int(os.environ.get('GUNICORN_WORKERS', 4))
threads = int(os.environ.get('GUNICORN_THREADS', 2))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))
bind = "0.0.0.0:" + os.environ.get('PORT', '5000')