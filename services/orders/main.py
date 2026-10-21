"""Orders service: creates orders by calling the products service over HTTP
and persisting them in Redis.

Clients are created at startup and shared across requests; tests inject
fakes through app.state before startup (see test_main.py), which the
lifespan detects and leaves alone.
"""
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import redis.asyncio as aredis
from fastapi import Depends, FastAPI, HTTPException, Request
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

PRODUCTS_URL = os.environ.get("PRODUCTS_URL", "http://localhost:8000")
REDIS_URL = os.environ.get("REDIS_URL", "localhost:6379")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # tests pre-populate app.state with fakes before the app starts
    if not hasattr(app.state, "http"):
        app.state.http = httpx.AsyncClient(
            base_url=PRODUCTS_URL, timeout=httpx.Timeout(3.0)
        )
    if not hasattr(app.state, "redis"):
        app.state.redis = aredis.from_url(
            f"redis://{REDIS_URL}", decode_responses=True
        )
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()


app = FastAPI(title="orders", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)  # /metrics for Prometheus


def get_products(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_redis(request: Request) -> aredis.Redis:
    return request.app.state.redis


class OrderIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/orders", status_code=201)
async def create_order(
    order: OrderIn, http: httpx.AsyncClient = Depends(get_products), r=Depends(get_redis)
):
    try:
        resp = await http.get(f"/products/{order.product_id}")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="products service unavailable")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="product not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="products service error")
    product = resp.json()

    try:
        order_id = await r.incr("order_seq")
        record = {
            "id": order_id,
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": order.quantity,
            "total_price": round(product["price"] * order.quantity, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await r.rpush("orders", order_id)
        await r.set(f"order:{order_id}", json.dumps(record))
    except aredis.RedisError:
        raise HTTPException(status_code=503, detail="storage unavailable")
    return record


@app.get("/orders")
async def list_orders(r=Depends(get_redis)):
    try:
        ids = await r.lrange("orders", 0, -1)
        if not ids:
            return []
        values = await r.mget([f"order:{i}" for i in ids])
    except aredis.RedisError:
        raise HTTPException(status_code=503, detail="storage unavailable")
    return [json.loads(v) for v in values if v]


@app.get("/orders/{order_id}")
async def get_order(order_id: int, r=Depends(get_redis)):
    try:
        raw = await r.get(f"order:{order_id}")
    except aredis.RedisError:
        raise HTTPException(status_code=503, detail="storage unavailable")
    if raw is None:
        raise HTTPException(status_code=404, detail="order not found")
    return json.loads(raw)
