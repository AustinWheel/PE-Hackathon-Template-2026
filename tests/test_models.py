"""Tests for database models."""
from datetime import datetime

from app.models.user import User
from app.models.url import Url
from app.models.event import Event
from app.models.product import Product


def test_create_user():
    user = User.create(username="alice", email="alice@test.com", created_at=datetime.now())
    assert user.id is not None
    assert user.username == "alice"
    assert user.email == "alice@test.com"


def test_create_product():
    product = Product.create(name="Laptop", category="Electronics", price=999.99, stock=10)
    assert product.id is not None
    assert product.name == "Laptop"
    assert float(product.price) == 999.99


def test_create_url(sample_user):
    url = Url.create(
        user=sample_user,
        short_code="xyz789",
        original_url="https://google.com",
        title="Google",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert url.id is not None
    assert url.short_code == "xyz789"
    assert url.user.id == sample_user.id


def test_create_event(sample_user, sample_url):
    event = Event.create(
        url=sample_url,
        user=sample_user,
        event_type="click",
        timestamp=datetime.now(),
        details="Test click event",
    )
    assert event.id is not None
    assert event.event_type == "click"


def test_user_url_relationship(sample_user):
    Url.create(
        user=sample_user,
        short_code="aaa",
        original_url="https://a.com",
        title="A",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Url.create(
        user=sample_user,
        short_code="bbb",
        original_url="https://b.com",
        title="B",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    urls = list(sample_user.urls)
    assert len(urls) == 2


def test_product_fields():
    p = Product.create(name="Book", category="Education", price=12.50, stock=0)
    fetched = Product.get_by_id(p.id)
    assert fetched.name == "Book"
    assert fetched.category == "Education"
    assert fetched.stock == 0
