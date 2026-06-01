"""WSGI entry for production servers (gunicorn, uwsgi)."""

from jacred_proxy import create_app

app = create_app()
