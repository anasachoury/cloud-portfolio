#!/usr/bin/env python3
"""Native end-to-end smoke test for the services — no docker, no cluster.

Boots on localhost:
  - a minimal RESP server (the ~9 redis commands orders actually uses:
    PING/INCR/RPUSH/LRANGE/SET/GET/MGET/DEL/EXISTS) on port 6399
  - products (uvicorn, :8001)
  - orders        (uvicorn, :8002, pointed at the other two)

then drives the full request path the cluster would see:
frontend->orders->products, orders->redis — minus nginx itself (its config
is rendered by the image from env vars; compose/the chart cover that part).

Usage:  .venv/bin/python scripts/smoke.py     (or `make smoke`)
Exit code 0 = all checks passed.
"""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRODUCTS_PORT, ORDERS_PORT, REDIS_PORT = 8001, 8002, 6399


# ── minimal RESP server ────────────────────────────────────────────────────
# Enough redis for services/orders/main.py: strings (SET/GET/INCR/MGET),
# lists (RPUSH/LRANGE), PING/DEL/EXISTS. Not a redis replacement — a test
# double that speaks the same protocol over a real socket.
class MiniRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.counters: dict[str, int] = {}

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                if not line.startswith(b"*"):
                    continue  # inline commands not used by redis-py
                n = int(line[1:].strip())
                args = []
                for _ in range(n):
                    hdr = await reader.readline()
                    ln = int(hdr[1:-2])
                    args.append((await reader.readexactly(ln + 2))[:-2])
                cmd = args[0].decode().upper()
                keys = [a.decode() for a in args[1:]]
                resp = self.dispatch(cmd, keys)
                writer.write(resp)
                await writer.drain()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()

    def dispatch(self, cmd: str, args: list[str]) -> bytes:
        def ok() -> bytes:
            return b"+OK\r\n"

        def integer(v: int) -> bytes:
            return f":{v}\r\n".encode()

        def bulk(s: str | None) -> bytes:
            if s is None:
                return b"$-1\r\n"
            return f"${len(s)}\r\n{s}\r\n".encode()

        def array(items: list[str]) -> bytes:
            out = f"*{len(items)}\r\n".encode()
            for it in items:
                out += bulk(it)
            return out

        if cmd == "PING":
            return b"+PONG\r\n"
        if cmd == "HELLO":
            # redis-py sends HELLO on connect; answer as a RESP2 server so it
            # stays on the protocol this mini-server speaks
            return array([
                "server", "miniredis", "version", "1.0.0",
                "proto", "2", "mode", "standalone", "role", "master",
            ])
        if cmd == "CLIENT":
            return ok()  # SETINFO / SETNAME best-effort
        if cmd == "COMMAND":  # redis-py probes capabilities on connect
            return array([])
        if cmd in ("INCR", "INCRBY", "DECR", "DECRBY"):
            k = args[0]
            delta = 1 if cmd in ("INCR", "DECR") else int(args[1])
            if cmd.startswith("DECR"):
                delta = -delta
            self.counters[k] = self.counters.get(k, 0) + delta
            self.strings[k] = str(self.counters[k])
            return integer(self.counters[k])
        if cmd in ("EXPIRE", "TTL", "PERSIST"):
            return integer(-1 if cmd == "TTL" else 1)
        if cmd == "RPUSH":
            k, *vals = args
            self.lists.setdefault(k, []).extend(vals)
            return integer(len(self.lists[k]))
        if cmd == "LRANGE":
            k, start, stop = args[0], int(args[1]), int(args[2])
            lst = self.lists.get(k, [])
            if stop == -1:
                stop = len(lst) - 1
            return array(lst[slice(start, stop + 1)])
        if cmd == "SET":
            k, v = args[0], args[1]
            self.strings[k] = v
            return ok()
        if cmd == "GET":
            return bulk(self.strings.get(args[0]))
        if cmd == "MGET":
            return array([self.strings.get(k) for k in args])
        if cmd == "DEL":
            n = sum(k in self.strings or k in self.lists for k in args)
            for k in args:
                self.strings.pop(k, None)
                self.lists.pop(k, None)
            return integer(n)
        if cmd == "EXISTS":
            return integer(sum(k in self.strings or k in self.lists for k in args))
        return f"-ERR unknown command '{cmd}'\r\n".encode()


# ── plumbing ───────────────────────────────────────────────────────────────
async def wait_health(client, url: str, tries: int = 60) -> bool:
    for _ in range(tries):
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return False


async def main() -> int:
    import httpx

    server = await asyncio.start_server(MiniRedis().handle, "127.0.0.1", REDIS_PORT)
    procs: list[subprocess.Popen] = []
    env = {
        **os.environ,
        "PRODUCTS_URL": f"http://127.0.0.1:{PRODUCTS_PORT}",
        "REDIS_URL": f"127.0.0.1:{REDIS_PORT}",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    py = sys.executable
    procs.append(subprocess.Popen(  # products
        [py, "-m", "uvicorn", "main:app", "--port", str(PRODUCTS_PORT), "--log-level", "warning"],
        cwd=REPO / "services" / "products", env=env,
    ))
    procs.append(subprocess.Popen(  # orders
        [py, "-m", "uvicorn", "main:app", "--port", str(ORDERS_PORT), "--log-level", "warning"],
        cwd=REPO / "services" / "orders", env=env,
    ))

    passed, failed = [], []

    def check(name: str, cond: bool, detail: str = "") -> None:
        (passed if cond else failed).append(name)
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not cond else ""))

    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            up = await wait_health(c, f"http://127.0.0.1:{PRODUCTS_PORT}/healthz")
            up = up and await wait_health(c, f"http://127.0.0.1:{ORDERS_PORT}/healthz")
            check("both services healthy within 30s", up)
            if not up:
                raise RuntimeError("services did not come up — see uvicorn stderr above")

            r = await c.get(f"http://127.0.0.1:{PRODUCTS_PORT}/products")
            check("GET /products -> 3 items", r.status_code == 200 and len(r.json()) == 3)
            r = await c.get(f"http://127.0.0.1:{PRODUCTS_PORT}/products/1")
            check("GET /products/1 -> Laptop", r.status_code == 200 and r.json()["name"] == "Laptop")

            base = f"http://127.0.0.1:{ORDERS_PORT}"
            r = await c.post(f"{base}/orders", json={"product_id": 2, "quantity": 3})
            body = r.json()
            check("POST /orders -> 201, id 1", r.status_code == 201 and body.get("id") == 1)
            check("  order priced from products (3 x Phone = 1797.0)",
                  body.get("total_price") == 1797.0 and body.get("product_name") == "Phone")
            r = await c.post(f"{base}/orders", json={"product_id": 1, "quantity": 1})
            check("second order -> id 2 (redis INCR seq)", r.status_code == 201 and r.json().get("id") == 2)
            r = await c.get(f"{base}/orders")
            check("GET /orders returns both (RPUSH+MGET path)", r.status_code == 200 and len(r.json()) == 2)
            r = await c.get(f"{base}/orders/1")
            check("GET /orders/1 -> stored record", r.status_code == 200 and r.json()["product_id"] == 2)
            r = await c.post(f"{base}/orders", json={"product_id": 99, "quantity": 1})
            check("unknown product -> 404", r.status_code == 404)

            r = await c.get(f"http://127.0.0.1:{PRODUCTS_PORT}/metrics")
            check("products exposes prometheus metrics", r.status_code == 200 and "http_requests_total" in r.text)

            # resilience: products down -> orders must answer 503, not hang
            procs[0].terminate()
            procs[0].wait(timeout=10)
            await asyncio.sleep(0.5)
            r = await c.post(f"{base}/orders", json={"product_id": 1, "quantity": 1})
            check("products down -> orders 503 (fast failure)", r.status_code == 503)
            r = await c.get(f"{base}/orders")
            check("products down -> history still served (redis is up)", r.status_code == 200 and len(r.json()) == 2)
    finally:
        for p in procs:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        deadline = time.time() + 10
        for p in procs:
            try:
                p.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                p.kill()
        server.close()
        await server.wait_closed()

    print(f"\n{len(passed)} passed, {len(failed)} failed")
    if failed:
        print("FAILED:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
