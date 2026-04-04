import os
from urllib.parse import urlparse

from peewee import DatabaseProxy, Model, PostgresqlDatabase
from playhouse.db_url import connect

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # DigitalOcean / production — use the connection string
        parsed = urlparse(database_url)
        sslmode = os.environ.get("DATABASE_SSLMODE", "require")
        database = PostgresqlDatabase(
            parsed.path.lstrip("/"),
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            sslmode=sslmode,
        )
    else:
        # Local development — use individual env vars
        database = PostgresqlDatabase(
            os.environ.get("DATABASE_NAME", "hackathon_db"),
            host=os.environ.get("DATABASE_HOST", "localhost"),
            port=int(os.environ.get("DATABASE_PORT", 5432)),
            user=os.environ.get("DATABASE_USER", "postgres"),
            password=os.environ.get("DATABASE_PASSWORD", "postgres"),
        )

    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()
