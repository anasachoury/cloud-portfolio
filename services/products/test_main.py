# Run per service, like CI does (avoids same-name module clashes across services):
#   pytest services/products
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_products():
    r = client.get("/products")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Laptop" in names and "Phone" in names


def test_get_product():
    r = client.get("/products/1")
    assert r.status_code == 200
    assert r.json() == {"id": 1, "name": "Laptop", "price": 999.0}


def test_get_product_missing():
    assert client.get("/products/99").status_code == 404


def test_metrics_exposed():
    assert client.get("/metrics").status_code == 200
