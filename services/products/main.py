"""Products service: static catalogue with health and metrics endpoints."""
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="products")
Instrumentator().instrument(app).expose(app)  # /metrics for Prometheus

PRODUCTS = [
    {"id": 1, "name": "Laptop", "price": 999.0},
    {"id": 2, "name": "Phone", "price": 599.0},
    {"id": 3, "name": "Headphones", "price": 149.0},
]


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/products")
def list_products():
    return PRODUCTS


@app.get("/products/{product_id}")
def get_product(product_id: int):
    for product in PRODUCTS:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="product not found")
