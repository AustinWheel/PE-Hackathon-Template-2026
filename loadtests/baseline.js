import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const healthLatency = new Trend("health_latency", true);
const productsLatency = new Trend("products_latency", true);
const usersLatency = new Trend("users_latency", true);
const urlsLatency = new Trend("urls_latency", true);

// Bronze: 50 concurrent users for 30 seconds
export const options = {
  stages: [
    { duration: "10s", target: 50 }, // ramp up to 50 users
    { duration: "30s", target: 50 }, // hold at 50 users
    { duration: "10s", target: 0 },  // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<5000"], // p95 under 5s for baseline
    errors: ["rate<0.1"],             // error rate under 10%
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:5001";

export default function () {
  // GET /health
  let res = http.get(`${BASE_URL}/health`);
  healthLatency.add(res.timings.duration);
  check(res, { "health 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // GET /products
  res = http.get(`${BASE_URL}/products`);
  productsLatency.add(res.timings.duration);
  check(res, { "products 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // GET /users (paginated)
  res = http.get(`${BASE_URL}/users?page=1&per_page=10`);
  usersLatency.add(res.timings.duration);
  check(res, { "users 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // GET /urls
  res = http.get(`${BASE_URL}/urls`);
  urlsLatency.add(res.timings.duration);
  check(res, { "urls 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // GET /metrics
  res = http.get(`${BASE_URL}/metrics`);
  check(res, { "metrics 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // Simulate think time between requests
  sleep(1);
}
