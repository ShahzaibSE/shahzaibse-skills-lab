# Resilience Patterns

## Overview

Resilience patterns enable microservices to handle failures gracefully, prevent cascade failures, and maintain system stability under adverse conditions.

---

## Circuit Breaker Pattern

Prevents cascade failures by stopping requests to failing services.

### States

```
        ┌─────────────────────────────────────────┐
        │                                         │
        ▼                                         │
    ┌───────┐  failure threshold   ┌──────┐      │
    │ CLOSED │────────────────────▶│ OPEN │      │
    └───────┘                      └──────┘      │
        ▲                              │         │
        │                              │ timeout │
        │    success threshold         ▼         │
        │                         ┌─────────┐    │
        └─────────────────────────│HALF-OPEN│────┘
                                  └─────────┘  failure
```

| State | Behavior | Transition |
|-------|----------|------------|
| **CLOSED** | Requests pass through, failures counted | → OPEN when failure threshold reached |
| **OPEN** | Requests fail immediately (fast fail) | → HALF-OPEN after timeout period |
| **HALF-OPEN** | Limited requests allowed to test recovery | → CLOSED on success, → OPEN on failure |

### Implementation

```python
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout: timedelta = timedelta(seconds=30)  # Time before half-open
    half_open_max_calls: int = 3        # Max concurrent calls in half-open

@dataclass
class CircuitBreaker:
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if not self._can_execute():
            logger.warning(f"Circuit {self.name} is OPEN, failing fast")
            raise CircuitOpenError(f"Circuit breaker {self.name} is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time >= self.config.timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls

        return False

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls -= 1
            if self.success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # Reset on success

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState):
        logger.info(f"Circuit {self.name}: {self.state.value} → {new_state.value}")
        self.state = new_state
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
            self.half_open_calls = 0

class CircuitOpenError(Exception):
    pass

# Usage
user_service_breaker = CircuitBreaker(
    name="user-service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        timeout=timedelta(seconds=30)
    )
)

async def get_user(user_id: str):
    return await user_service_breaker.call(
        http_client.get,
        f"http://user-service/users/{user_id}"
    )
```

### Configuration Guidelines

| Parameter | Low Traffic | High Traffic | Critical Path |
|-----------|-------------|--------------|---------------|
| `failure_threshold` | 3-5 | 10-20 | 3 |
| `timeout` | 30-60s | 10-30s | 5-15s |
| `success_threshold` | 2-3 | 5-10 | 3 |

---

## Bulkhead Pattern

Isolates failures by partitioning resources.

### Thread Pool Isolation

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

class BulkheadManager:
    """Manages isolated thread pools per service."""

    def __init__(self):
        self.pools: Dict[str, ThreadPoolExecutor] = {}
        self.semaphores: Dict[str, asyncio.Semaphore] = {}

    def register(self, name: str, max_concurrent: int):
        """Register a bulkhead for a service."""
        self.pools[name] = ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix=f"bulkhead-{name}"
        )
        self.semaphores[name] = asyncio.Semaphore(max_concurrent)

    async def execute(self, name: str, func, *args, **kwargs):
        """Execute function within bulkhead."""
        if name not in self.semaphores:
            raise ValueError(f"Unknown bulkhead: {name}")

        semaphore = self.semaphores[name]

        # Try to acquire without blocking
        if not semaphore.locked() or await asyncio.wait_for(
            semaphore.acquire(), timeout=0.1
        ):
            try:
                return await func(*args, **kwargs)
            finally:
                semaphore.release()
        else:
            raise BulkheadFullError(f"Bulkhead {name} is full")

class BulkheadFullError(Exception):
    pass

# Usage
bulkheads = BulkheadManager()
bulkheads.register("user-service", max_concurrent=10)
bulkheads.register("order-service", max_concurrent=20)
bulkheads.register("payment-service", max_concurrent=5)  # Critical, limit concurrency

async def get_user(user_id: str):
    return await bulkheads.execute(
        "user-service",
        http_client.get,
        f"http://user-service/users/{user_id}"
    )
```

### Semaphore Isolation (Lightweight)

```python
from contextlib import asynccontextmanager

class SemaphoreBulkhead:
    """Lightweight bulkhead using semaphores."""

    def __init__(self, name: str, max_concurrent: int, max_wait: float = 1.0):
        self.name = name
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_wait = max_wait
        self.rejected_count = 0

    @asynccontextmanager
    async def acquire(self):
        try:
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=self.max_wait
            )
            yield
        except asyncio.TimeoutError:
            self.rejected_count += 1
            raise BulkheadFullError(
                f"Bulkhead {self.name} full, rejected: {self.rejected_count}"
            )
        finally:
            self.semaphore.release()

# Usage
payment_bulkhead = SemaphoreBulkhead("payment", max_concurrent=5)

async def process_payment(payment: Payment):
    async with payment_bulkhead.acquire():
        return await payment_service.process(payment)
```

---

## Retry with Exponential Backoff

Handles transient failures with intelligent retry logic.

### Implementation

```python
import asyncio
import random
from typing import Callable, Type, Tuple
from functools import wraps

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retry with exponential backoff and jitter."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator

# Usage
@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
async def call_external_service(data: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post("http://external-api/endpoint", json=data)
        response.raise_for_status()
        return response.json()
```

### Retry Decision Matrix

| Error Type | Retry? | Notes |
|------------|--------|-------|
| Connection timeout | Yes | Network transient |
| Read timeout | Maybe | Could cause duplicates |
| 429 Too Many Requests | Yes | With longer backoff |
| 500 Internal Server Error | Yes | Server transient |
| 502/503/504 | Yes | Infrastructure issues |
| 400 Bad Request | No | Client error, won't change |
| 401/403 | No | Auth issue, won't change |
| 404 Not Found | No | Resource doesn't exist |

---

## Timeout Patterns

### Request Timeout

```python
import asyncio
import httpx

async def fetch_with_timeout(url: str, timeout: float = 5.0):
    """Single request with timeout."""
    try:
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.get(url),
                timeout=timeout
            )
            return response.json()
    except asyncio.TimeoutError:
        logger.error(f"Request to {url} timed out after {timeout}s")
        raise ServiceTimeoutError(f"Timeout calling {url}")
```

### Timeout Budget (Deadline Propagation)

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from contextvars import ContextVar

# Context variable for deadline propagation
request_deadline: ContextVar[Optional[datetime]] = ContextVar(
    'request_deadline', default=None
)

@dataclass
class TimeoutBudget:
    """Track remaining time budget across service calls."""
    deadline: datetime
    min_timeout: float = 0.1  # Minimum timeout to attempt call

    @classmethod
    def from_timeout(cls, timeout_seconds: float) -> "TimeoutBudget":
        return cls(deadline=datetime.now() + timedelta(seconds=timeout_seconds))

    @property
    def remaining(self) -> float:
        """Remaining seconds until deadline."""
        remaining = (self.deadline - datetime.now()).total_seconds()
        return max(0, remaining)

    @property
    def has_time(self) -> bool:
        """Check if enough time remains."""
        return self.remaining >= self.min_timeout

    def allocate(self, max_timeout: float) -> float:
        """Allocate timeout for next call, respecting budget."""
        return min(self.remaining, max_timeout)

# Middleware to set deadline from incoming request
async def deadline_middleware(request, call_next):
    # Check for deadline header from upstream
    deadline_header = request.headers.get("X-Request-Deadline")

    if deadline_header:
        deadline = datetime.fromisoformat(deadline_header)
    else:
        # Set default deadline for new requests
        deadline = datetime.now() + timedelta(seconds=30)

    request_deadline.set(deadline)
    budget = TimeoutBudget(deadline=deadline)

    if not budget.has_time:
        return JSONResponse(
            status_code=504,
            content={"error": "Request deadline exceeded"}
        )

    return await call_next(request)

# Usage in service calls
async def get_user_with_orders(user_id: str):
    budget = TimeoutBudget(deadline=request_deadline.get())

    if not budget.has_time:
        raise DeadlineExceededError()

    # Allocate time for user call
    user = await http_client.get(
        f"http://user-service/users/{user_id}",
        timeout=budget.allocate(5.0),
        headers={"X-Request-Deadline": budget.deadline.isoformat()}
    )

    if not budget.has_time:
        return {"user": user, "orders": None}  # Partial response

    # Allocate remaining time for orders
    orders = await http_client.get(
        f"http://order-service/users/{user_id}/orders",
        timeout=budget.allocate(10.0),
        headers={"X-Request-Deadline": budget.deadline.isoformat()}
    )

    return {"user": user, "orders": orders}
```

---

## Rate Limiting

### Token Bucket Algorithm

```python
import time
from threading import Lock

class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens (burst size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate wait time until tokens available."""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            deficit = tokens - self.tokens
            return deficit / self.rate

# Usage
api_limiter = TokenBucket(rate=100, capacity=200)  # 100 req/s, burst 200

async def rate_limited_handler(request):
    if not api_limiter.acquire():
        wait = api_limiter.wait_time()
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(int(wait) + 1)},
            detail=f"Rate limit exceeded. Retry after {wait:.1f}s"
        )
    return await process_request(request)
```

### Leaky Bucket (Queue-based)

```python
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class LeakyBucket:
    """Leaky bucket for smooth request processing."""
    rate: float  # Requests per second
    capacity: int  # Queue size

    def __post_init__(self):
        self.queue: deque = deque(maxlen=self.capacity)
        self.processing = False

    async def submit(self, func: Callable, *args, **kwargs) -> Any:
        """Submit request to bucket."""
        if len(self.queue) >= self.capacity:
            raise BucketFullError("Rate limit exceeded, queue full")

        future = asyncio.Future()
        self.queue.append((func, args, kwargs, future))

        if not self.processing:
            asyncio.create_task(self._process())

        return await future

    async def _process(self):
        """Process queue at fixed rate."""
        self.processing = True
        interval = 1.0 / self.rate

        while self.queue:
            func, args, kwargs, future = self.queue.popleft()
            try:
                result = await func(*args, **kwargs)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

            await asyncio.sleep(interval)

        self.processing = False
```

---

## Fallback Strategies

### Fallback Pattern

```python
from typing import Callable, TypeVar, Optional

T = TypeVar('T')

class FallbackChain:
    """Execute with fallback options."""

    def __init__(self):
        self.strategies: list[Callable] = []

    def add(self, strategy: Callable) -> "FallbackChain":
        self.strategies.append(strategy)
        return self

    async def execute(self, *args, **kwargs) -> T:
        """Try strategies in order until one succeeds."""
        last_error = None

        for i, strategy in enumerate(self.strategies):
            try:
                result = await strategy(*args, **kwargs)
                if i > 0:
                    logger.info(f"Fallback {i} succeeded")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Strategy {i} failed: {e}")
                continue

        raise FallbackExhaustedError(
            f"All {len(self.strategies)} strategies failed"
        ) from last_error

# Usage
async def get_product_price(product_id: str) -> float:
    fallback = FallbackChain()
    fallback.add(lambda pid: pricing_service.get_price(pid))       # Primary
    fallback.add(lambda pid: cache.get(f"price:{pid}"))            # Cache fallback
    fallback.add(lambda pid: catalog_db.get_base_price(pid))       # DB fallback
    fallback.add(lambda pid: DEFAULT_PRICES.get(pid, 0.0))         # Static fallback

    return await fallback.execute(product_id)
```

### Graceful Degradation

```python
async def get_product_details(product_id: str):
    """Return partial data when some services fail."""
    results = await asyncio.gather(
        get_product(product_id),
        get_reviews(product_id),
        get_recommendations(product_id),
        return_exceptions=True
    )

    product, reviews, recommendations = results

    response = {
        "product": product if not isinstance(product, Exception) else None,
        "reviews": reviews if not isinstance(reviews, Exception) else [],
        "recommendations": recommendations if not isinstance(recommendations, Exception) else [],
        "_degraded": any(isinstance(r, Exception) for r in results)
    }

    if response["product"] is None:
        raise HTTPException(status_code=503, detail="Product service unavailable")

    return response
```

---

## Health Checks

### Liveness vs Readiness

| Check | Purpose | Failure Action |
|-------|---------|----------------|
| **Liveness** | Is process alive? | Restart container |
| **Readiness** | Can handle requests? | Remove from load balancer |

### Implementation

```python
from fastapi import FastAPI, Response
from enum import Enum
import asyncio

app = FastAPI()

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    def __init__(self):
        self.checks: dict[str, Callable] = {}

    def register(self, name: str, check: Callable):
        self.checks[name] = check

    async def check_all(self) -> dict:
        results = {}
        for name, check in self.checks.items():
            try:
                await asyncio.wait_for(check(), timeout=5.0)
                results[name] = {"status": "healthy"}
            except asyncio.TimeoutError:
                results[name] = {"status": "unhealthy", "error": "timeout"}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
        return results

health = HealthChecker()

# Register dependency checks
health.register("database", lambda: db.execute("SELECT 1"))
health.register("redis", lambda: redis.ping())
health.register("user-service", lambda: httpx.get("http://user-service/health"))

@app.get("/health/live")
async def liveness():
    """Liveness probe - is the process running?"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness(response: Response):
    """Readiness probe - can we handle requests?"""
    results = await health.check_all()
    all_healthy = all(r["status"] == "healthy" for r in results.values())

    if not all_healthy:
        response.status_code = 503

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": results
    }

@app.get("/health/detailed")
async def detailed_health():
    """Detailed health for debugging."""
    results = await health.check_all()
    return {
        "status": "healthy" if all(r["status"] == "healthy" for r in results.values()) else "degraded",
        "checks": results,
        "version": "1.2.3",
        "uptime_seconds": get_uptime()
    }
```

### Kubernetes Probes Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: service
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 0
            periodSeconds: 5
            failureThreshold: 30  # 30 * 5s = 150s max startup
```

---

## Combined Resilience Example

```python
from dataclasses import dataclass

@dataclass
class ResilientClient:
    """HTTP client with full resilience patterns."""
    service_name: str
    circuit_breaker: CircuitBreaker
    bulkhead: SemaphoreBulkhead
    rate_limiter: TokenBucket

    @retry_with_backoff(max_retries=3, retryable_exceptions=(ConnectionError,))
    async def request(self, method: str, path: str, **kwargs):
        # Rate limiting
        if not self.rate_limiter.acquire():
            raise RateLimitExceeded()

        # Bulkhead
        async with self.bulkhead.acquire():
            # Circuit breaker
            return await self.circuit_breaker.call(
                self._do_request, method, path, **kwargs
            )

    async def _do_request(self, method: str, path: str, **kwargs):
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

# Create resilient clients per service
user_client = ResilientClient(
    service_name="user-service",
    circuit_breaker=CircuitBreaker("user-service"),
    bulkhead=SemaphoreBulkhead("user-service", max_concurrent=20),
    rate_limiter=TokenBucket(rate=100, capacity=200)
)
```

---

## Implementation Checklist

- [ ] **Circuit Breakers**: Configured for all external service calls
- [ ] **Bulkheads**: Critical services isolated with concurrency limits
- [ ] **Retries**: Exponential backoff with jitter for transient failures
- [ ] **Timeouts**: Request timeouts set, deadline propagation implemented
- [ ] **Rate Limiting**: Inbound and outbound rate limits configured
- [ ] **Fallbacks**: Graceful degradation for non-critical features
- [ ] **Health Checks**: Liveness and readiness probes implemented
- [ ] **Monitoring**: Circuit breaker state, rejection rates tracked
