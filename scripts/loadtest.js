// scripts/loadtest.js — k6 load test for the demo and the README numbers.
//
// Usage:
//   k6 run -e TARGET=http://localhost:8080 scripts/loadtest.js     (compose)
//   k6 run -e TARGET=http://<LB-address> scripts/loadtest.js       (EKS/ingress)
// or: make load-test TARGET=http://<LB>
//
// Traffic mix mirrors the storefront: ~80% browsing (products reads),
// ~20% buying (order writes). Ramps so the HPA story is visible in
// Grafana ("HPA replicas" panel): 2 -> 20 -> 60 -> 0 over ~4 minutes.
//
// Thresholds are the demo claims: p95 under 500ms, error rate under 1%.

import http from 'k6/http';
import { check, sleep } from 'k6';

const TARGET = __ENV.TARGET || 'http://localhost:8080';

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // warm-up, single pod keeps up
    { duration: '1m', target: 20 },   // HPA should take notice here
    { duration: '90s', target: 60 },  // replicas climb; watch Grafana
    { duration: '30s', target: 0 },   // cool-down back to min
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],   // the demo claim: < 1% errors
    http_req_duration: ['p(95)<500'], // and: p95 < 500ms under load
  },
};

export default function () {
  if (Math.random() < 0.8) {
    // browse: product catalogue (also the cheapest endpoint — realistic mix)
    const r = http.get(`${TARGET}/api/products`);
    check(r, { 'products 200': (res) => res.status === 200 });
  } else {
    // buy: create an order (hits orders -> products -> redis)
    const pid = 1 + Math.floor(Math.random() * 3);
    const qty = 1 + Math.floor(Math.random() * 3);
    const r = http.post(`${TARGET}/api/orders`, JSON.stringify({ product_id: pid, quantity: qty }), {
      headers: { 'Content-Type': 'application/json' },
    });
    check(r, { 'order 201': (res) => res.status === 201 });
  }
  sleep(0.4); // ~2.5 requests/s per VU; 60 VUs ~= 150 rps at peak
}
