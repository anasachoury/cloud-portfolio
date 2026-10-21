# Run per service, like CI does (avoids same-name module clashes across services):
#   pytest services/orders
import httpx
import pytest
from fastapi.testclient import TestClient

try:
    from fakeredis import FakeAsyncRedis
except ImportError:  # older fakeredis
    from fakeredis.aioredis import FakeRedis as FakeAsyncRedis

import main


def catalogue(request: httpx.Request) -> httpx.Response:
    """Fake products service: knows product 1, 404s product 99."""
    if request.url.path == "/products/1":
        return httpx.Response(200, json={"id": 1, "name": "Laptop", "price": 999.0})
    if request.url.path == "/products/99":
        return httpx.Response(404, json={"detail": "product not found"})
    return httpx.Response(500, json={})


def broken(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("products is down")


def build_client(handler) -> TestClient:
    main.app.state.http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://products-test"
    )
    # decode_responses mirrors the real client from main.py's lifespan —
    # without it lrange returns bytes and f"order:{b'1'}" silently misses
    main.app.state.redis = FakeAsyncRedis(decode_responses=True)
    return TestClient(main.app)


@pytest.fixture
def client():
    with build_client(catalogue) as c:
        yield c


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_create_and_fetch_order(client):
    r = client.post("/orders", json={"product_id": 1, "quantity": 2})
    assert r.status_code == 201
    body = r.json()
    assert body["total_price"] == 1998.0
    assert body["product_name"] == "Laptop"

    r = client.get(f"/orders/{body['id']}")
    assert r.status_code == 200
    assert r.json()["quantity"] == 2


def test_create_order_unknown_product(client):
    assert client.post("/orders", json={"product_id": 99}).status_code == 404


def test_create_order_products_down():
    with build_client(broken) as c:
        assert c.post("/orders", json={"product_id": 1}).status_code == 503


def test_list_orders(client):
    client.post("/orders", json={"product_id": 1})
    client.post("/orders", json={"product_id": 1, "quantity": 3})
    r = client.get("/orders")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_missing_order(client):
    assert client.get("/orders/12345").status_code == 404


def test_quantity_validation(client):
    assert (
        client.post("/orders", json={"product_id": 1, "quantity": 0}).status_code
        == 422
    )
