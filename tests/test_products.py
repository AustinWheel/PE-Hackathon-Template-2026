"""Tests for the /products endpoint."""


def test_products_returns_200(client):
    resp = client.get("/products")
    assert resp.status_code == 200


def test_products_returns_list(client):
    data = client.get("/products").get_json()
    assert isinstance(data, list)


def test_products_empty_when_no_data(client):
    data = client.get("/products").get_json()
    assert data == []


def test_products_returns_product(client, sample_product):
    data = client.get("/products").get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Widget"
    assert data[0]["category"] == "Tools"
    assert float(data[0]["price"]) == 9.99
    assert data[0]["stock"] == 100


def test_products_returns_multiple(client, sample_product):
    from app.models.product import Product
    Product.create(name="Gadget", category="Electronics", price=19.99, stock=50)
    data = client.get("/products").get_json()
    assert len(data) == 2
