# API Gateway Patterns

## Overview

API Gateways serve as the single entry point for client requests in microservices architectures, handling cross-cutting concerns and simplifying client interactions.

---

## Gateway Responsibilities

### Core Functions

| Function | Description | Implementation |
|----------|-------------|----------------|
| **Routing** | Direct requests to appropriate services | Path-based, header-based, query-based |
| **Composition** | Aggregate multiple service responses | Fan-out/fan-in, parallel calls |
| **Protocol Translation** | Convert between protocols | REST↔gRPC, HTTP↔WebSocket |
| **Load Balancing** | Distribute traffic across instances | Round-robin, least connections, weighted |

### Request Lifecycle

```
Client Request → Authentication → Rate Limiting → Routing →
Service Call → Response Transformation → Client Response
```

---

## Industry API Gateways

### Kong

**Best for**: Plugin ecosystem, declarative configuration, Kubernetes-native

```yaml
# Kong Declarative Configuration
_format_version: "3.0"
services:
  - name: user-service
    url: http://user-service:8080
    routes:
      - name: user-routes
        paths:
          - /api/v1/users
        strip_path: true
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          policy: local
      - name: jwt
        config:
          claims_to_verify:
            - exp
      - name: correlation-id
        config:
          header_name: X-Correlation-ID
          generator: uuid
```

**Key Plugins**:
- `rate-limiting`: Token bucket/sliding window
- `jwt`/`oauth2`: Authentication
- `request-transformer`: Header/body modification
- `prometheus`: Metrics export
- `zipkin`: Distributed tracing

### AWS API Gateway

**Best for**: Serverless architectures, AWS ecosystem integration

```yaml
# AWS SAM Template
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  ApiGateway:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: CognitoAuthorizer
        Authorizers:
          CognitoAuthorizer:
            UserPoolArn: !GetAtt UserPool.Arn
      Cors:
        AllowOrigin: "'https://example.com'"
        AllowMethods: "'GET,POST,PUT,DELETE'"
      ThrottlingBurstLimit: 500
      ThrottlingRateLimit: 1000

  UserFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.users
      Events:
        GetUsers:
          Type: Api
          Properties:
            RestApiId: !Ref ApiGateway
            Path: /users
            Method: GET
```

**Features**:
- Usage plans and API keys
- Request validation (JSON Schema)
- Caching with TTL
- Custom domain names
- VPC Link for private integrations

### Envoy

**Best for**: Service mesh ingress, high-performance proxying, xDS dynamic configuration

```yaml
# Envoy Configuration
static_resources:
  listeners:
    - name: http_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api/users"
                          route:
                            cluster: user_service
                            timeout: 30s
                            retry_policy:
                              retry_on: "5xx,reset,connect-failure"
                              num_retries: 3
                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
    - name: user_service
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: user_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: user-service
                      port_value: 8080
      health_checks:
        - timeout: 5s
          interval: 10s
          unhealthy_threshold: 3
          healthy_threshold: 2
          http_health_check:
            path: /health
```

### NGINX

**Best for**: Traditional reverse proxy, high concurrency, mature ecosystem

```nginx
# NGINX Configuration
upstream user_service {
    least_conn;
    server user-service-1:8080 weight=5;
    server user-service-2:8080 weight=5;
    keepalive 32;
}

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;
    server_name api.example.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location /api/v1/users {
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;

        # JWT validation (with nginx-jwt module)
        auth_jwt "API";
        auth_jwt_key_file /etc/nginx/jwt_key.pem;

        # Proxy settings
        proxy_pass http://user_service;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;

        # Caching
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_key $scheme$request_method$host$request_uri;
    }
}
```

### Traefik

**Best for**: Auto-discovery, Docker/Kubernetes native, middleware chains

```yaml
# Traefik Dynamic Configuration
http:
  routers:
    user-router:
      rule: "PathPrefix(`/api/users`)"
      service: user-service
      middlewares:
        - rate-limit
        - auth-jwt
        - strip-prefix
      entryPoints:
        - web
        - websecure
      tls:
        certResolver: letsencrypt

  services:
    user-service:
      loadBalancer:
        servers:
          - url: "http://user-service:8080"
        healthCheck:
          path: /health
          interval: "10s"
          timeout: "3s"

  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 50
        period: 1m

    auth-jwt:
      plugin:
        jwt:
          secret: "${JWT_SECRET}"

    strip-prefix:
      stripPrefix:
        prefixes:
          - "/api"
```

---

## Custom Gateway Patterns

### Backend-for-Frontend (BFF)

Dedicated gateway per client type optimizes API for specific needs.

```
┌─────────┐     ┌───────────┐
│ Web App │────▶│  Web BFF  │──┐
└─────────┘     └───────────┘  │
                               │    ┌──────────────┐
┌─────────┐     ┌───────────┐  ├───▶│ User Service │
│Mobile   │────▶│Mobile BFF │──┤    └──────────────┘
└─────────┘     └───────────┘  │
                               │    ┌──────────────┐
┌─────────┐     ┌───────────┐  ├───▶│Order Service │
│ IoT     │────▶│  IoT BFF  │──┘    └──────────────┘
└─────────┘     └───────────┘
```

**Implementation**:

```python
# Mobile BFF - Optimized responses
from fastapi import FastAPI, Depends
from typing import Optional

app = FastAPI()

@app.get("/mobile/dashboard")
async def mobile_dashboard(user_id: str):
    """Aggregate data optimized for mobile screens."""
    # Parallel calls to services
    user, orders, notifications = await asyncio.gather(
        user_service.get_user_summary(user_id),  # Minimal fields
        order_service.get_recent_orders(user_id, limit=5),
        notification_service.get_unread_count(user_id)
    )

    return {
        "user": {
            "name": user.name,
            "avatar_url": user.avatar_thumbnail  # Small image for mobile
        },
        "recent_orders": [
            {"id": o.id, "status": o.status, "total": o.total}
            for o in orders
        ],
        "unread_notifications": notifications.count
    }
```

**When to Use BFF**:
- Different clients have significantly different data needs
- Mobile needs optimized payloads (bandwidth constraints)
- Web needs rich data for complex UIs
- Third-party API compatibility requirements

### Gateway Aggregation Pattern

Combine multiple service calls into single client request.

```python
from fastapi import FastAPI, BackgroundTasks
import asyncio
import httpx

app = FastAPI()

@app.get("/api/v1/product/{product_id}/details")
async def get_product_details(product_id: str):
    """Aggregate product information from multiple services."""
    async with httpx.AsyncClient() as client:
        # Fan-out: parallel requests
        results = await asyncio.gather(
            client.get(f"http://product-service/products/{product_id}"),
            client.get(f"http://inventory-service/stock/{product_id}"),
            client.get(f"http://review-service/products/{product_id}/summary"),
            client.get(f"http://pricing-service/products/{product_id}/price"),
            return_exceptions=True
        )

        product, inventory, reviews, pricing = results

        # Fan-in: combine responses
        return {
            "product": product.json() if not isinstance(product, Exception) else None,
            "stock": inventory.json() if not isinstance(inventory, Exception) else {"available": "unknown"},
            "reviews": reviews.json() if not isinstance(reviews, Exception) else {"average": None},
            "pricing": pricing.json() if not isinstance(pricing, Exception) else None,
            "_partial": any(isinstance(r, Exception) for r in results)
        }
```

### Gateway Offloading

Move cross-cutting concerns from services to gateway.

| Concern | Gateway Handles | Service Benefit |
|---------|-----------------|-----------------|
| SSL Termination | TLS handshake, certificate management | Reduced CPU, simpler config |
| Compression | gzip/brotli responses | Cleaner service code |
| Caching | Response caching, cache invalidation | Reduced load |
| CORS | Cross-origin headers | No CORS code in services |
| Request Logging | Access logs, audit trail | Centralized logging |

---

## Cross-Cutting Concerns

### Authentication at the Edge

```python
# Gateway authentication middleware
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def authenticate(request: Request):
    """Validate JWT and inject user context."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        # Inject user info for downstream services
        request.state.user_id = payload["sub"]
        request.state.roles = payload.get("roles", [])
        # Forward as header to internal services
        request.headers.__dict__["_list"].append(
            (b"x-user-id", payload["sub"].encode())
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Rate Limiting Strategies

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = defaultdict(lambda: capacity)
        self.last_update = defaultdict(time.time)

    def allow(self, key: str) -> bool:
        now = time.time()
        elapsed = now - self.last_update[key]
        self.last_update[key] = now

        # Add tokens based on elapsed time
        self.tokens[key] = min(
            self.capacity,
            self.tokens[key] + elapsed * self.rate
        )

        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True
        return False

# Different limits per tier
rate_limiters = {
    "free": RateLimiter(rate=1, capacity=10),      # 1 req/s, burst 10
    "pro": RateLimiter(rate=10, capacity=100),     # 10 req/s, burst 100
    "enterprise": RateLimiter(rate=100, capacity=1000)
}

async def rate_limit_middleware(request: Request, call_next):
    tier = request.state.user_tier or "free"
    client_key = f"{request.state.user_id}:{request.url.path}"

    if not rate_limiters[tier].allow(client_key):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "1"}
        )
    return await call_next(request)
```

### API Versioning Strategies

| Strategy | Example | Pros | Cons |
|----------|---------|------|------|
| URL Path | `/api/v1/users` | Clear, cacheable | URL pollution |
| Header | `Accept: application/vnd.api.v1+json` | Clean URLs | Less discoverable |
| Query Param | `/api/users?version=1` | Easy to test | Not RESTful |

**Recommended: URL Path Versioning**

```python
from fastapi import FastAPI, APIRouter

# Version-specific routers
v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

@v1_router.get("/users/{user_id}")
async def get_user_v1(user_id: str):
    """V1: Returns flat user object."""
    return {"id": user_id, "name": "John", "email": "john@example.com"}

@v2_router.get("/users/{user_id}")
async def get_user_v2(user_id: str):
    """V2: Returns structured user object with metadata."""
    return {
        "data": {"id": user_id, "name": "John", "email": "john@example.com"},
        "meta": {"version": "2", "deprecated_fields": []}
    }

app = FastAPI()
app.include_router(v1_router)
app.include_router(v2_router)
```

### Request/Response Transformation

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

class TransformationMiddleware(BaseHTTPMiddleware):
    """Transform requests/responses for API compatibility."""

    async def dispatch(self, request: Request, call_next):
        # Request transformation: snake_case to camelCase for internal services
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body:
                data = json.loads(body)
                transformed = self._to_snake_case(data)
                # Modify request body (simplified)

        response = await call_next(request)

        # Response transformation: camelCase for external clients
        if response.headers.get("content-type") == "application/json":
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            data = json.loads(body)
            transformed = self._to_camel_case(data)
            return Response(
                content=json.dumps(transformed),
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        return response

    def _to_camel_case(self, data):
        if isinstance(data, dict):
            return {
                self._snake_to_camel(k): self._to_camel_case(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._to_camel_case(item) for item in data]
        return data

    def _snake_to_camel(self, name):
        components = name.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
```

---

## Gateway Anti-Patterns

### 1. God Gateway

**Problem**: Gateway contains business logic, becoming a monolith.

```python
# ANTI-PATTERN: Business logic in gateway
@app.post("/api/orders")
async def create_order(order: OrderCreate):
    # Validate inventory - WRONG: business logic
    if order.quantity > await inventory.get_stock(order.product_id):
        raise HTTPException(400, "Insufficient stock")

    # Calculate pricing - WRONG: business logic
    price = await pricing.get_price(order.product_id)
    total = price * order.quantity
    if order.coupon:
        total *= 0.9  # WRONG: discount logic in gateway

    # Create order
    return await order_service.create(order, total)
```

**Solution**: Gateway only routes; services own logic.

```python
# CORRECT: Gateway only routes
@app.post("/api/orders")
async def create_order(order: OrderCreate):
    return await order_service.create(order)  # Service handles all logic
```

### 2. Tight Service Coupling

**Problem**: Gateway knows internal service structure.

```python
# ANTI-PATTERN: Gateway knows service internals
@app.get("/api/dashboard")
async def dashboard():
    # Gateway knows exact service endpoints and data structure
    user = await httpx.get("http://user-service/internal/users/full")
    orders = await httpx.get("http://order-service/internal/orders/with-items")
    # Gateway transforms data - coupling to internal models
    return transform_for_dashboard(user, orders)
```

**Solution**: Services expose gateway-friendly endpoints.

```python
# CORRECT: Services provide aggregated endpoints
@app.get("/api/dashboard")
async def dashboard(user_id: str):
    return await dashboard_service.get_user_dashboard(user_id)
```

### 3. Missing Circuit Breakers

**Problem**: Gateway cascades failures to all clients.

```python
# ANTI-PATTERN: No failure isolation
@app.get("/api/product/{id}")
async def get_product(id: str):
    product = await product_service.get(id)  # If this hangs, gateway hangs
    reviews = await review_service.get(id)   # No timeout, no fallback
    return {**product, "reviews": reviews}
```

**Solution**: See resilience-patterns.md for circuit breaker implementation.

---

## Decision Matrix: Gateway Selection

| Factor | Kong | AWS API GW | Envoy | NGINX | Traefik | Custom |
|--------|------|------------|-------|-------|---------|--------|
| **Cloud Native** | High | AWS Only | High | Medium | High | - |
| **Plugin Ecosystem** | Excellent | Good | Good | Good | Good | Build |
| **Performance** | High | High | Very High | Very High | High | Varies |
| **Learning Curve** | Medium | Low | High | Low | Low | High |
| **Self-Hosted** | Yes | No | Yes | Yes | Yes | Yes |
| **Service Mesh** | Via Kuma | No | Yes (Istio) | No | Yes | No |
| **Cost** | Open/Enterprise | Pay-per-use | Free | Free/Plus | Free | Dev time |

### Selection Guide

```
Need serverless + AWS? → AWS API Gateway
Need plugin ecosystem + K8s? → Kong
Need service mesh? → Envoy (with Istio)
Need simple reverse proxy? → NGINX
Need auto-discovery + Docker? → Traefik
Need full control + specific requirements? → Custom BFF
```

---

## Implementation Checklist

- [ ] **Routing**: Path-based routing to services configured
- [ ] **Authentication**: JWT/OAuth validation at edge
- [ ] **Rate Limiting**: Per-client/tier limits implemented
- [ ] **Circuit Breakers**: Failure isolation configured
- [ ] **Timeouts**: Request timeouts set appropriately
- [ ] **Logging**: Request/response logging enabled
- [ ] **Metrics**: Prometheus metrics exposed
- [ ] **Health Checks**: Gateway and upstream health monitored
- [ ] **CORS**: Cross-origin policies configured
- [ ] **SSL/TLS**: Certificates managed, TLS termination configured
