import os
from unittest.mock import patch

import pytest
from peewee import SqliteDatabase

from app.database import db
from app.models.user import User
from app.models.url import Url
from app.models.event import Event
from app.models.product import Product
from app.models.alert import Alert

MODELS = [User, Url, Event, Product, Alert]

# In-memory SQLite — no Postgres needed
test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def setup_test_db():
    """Bind all models to an in-memory SQLite DB for each test."""
    db.initialize(test_db)
    test_db.connect(reuse_if_open=True)
    test_db.create_tables(MODELS)
    yield
    test_db.drop_tables(MODELS)
    if not test_db.is_closed():
        test_db.close()


@pytest.fixture
def app():
    """Create a Flask app with the DB swapped to SQLite."""
    os.environ.pop("DATABASE_URL", None)

    # Patch init_db where create_app imports it from
    with patch("app.database.init_db"):
        from app import create_app
        application = create_app()

    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_product():
    return Product.create(name="Widget", category="Tools", price=9.99, stock=100)


@pytest.fixture
def sample_user():
    from datetime import datetime
    return User.create(username="testuser", email="test@example.com", created_at=datetime.now())


@pytest.fixture
def sample_url(sample_user):
    from datetime import datetime
    return Url.create(
        user=sample_user,
        short_code="abc123",
        original_url="https://example.com",
        title="Example",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
