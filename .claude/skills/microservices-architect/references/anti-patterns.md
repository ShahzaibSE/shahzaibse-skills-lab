# Microservices Anti-Patterns

## Overview

Anti-patterns are common solutions that appear helpful but create more problems than they solve. Recognizing these patterns helps avoid costly architectural mistakes.

---

## Architecture Anti-Patterns

### 1. Distributed Monolith

**Symptom**: Services that must be deployed together, share databases, or have tight coupling.

```
ANTI-PATTERN: Distributed Monolith

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Service A  │────▶│  Service B  │────▶│  Service C  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   Shared    │
                    │  Database   │
                    └─────────────┘

Problems:
- Can't deploy independently
- Schema changes break all services
- No isolation, failures cascade
- Worst of both worlds: distributed complexity + monolith coupling
```

**Solution**:

```
CORRECT: Independent Services

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Service A  │     │  Service B  │     │  Service C  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    DB A     │     │    DB B     │     │    DB C     │
└─────────────┘     └─────────────┘     └─────────────┘

Communication via:
- Events (async)
- APIs (sync, when necessary)
```

**Detection Checklist**:
- [ ] Can each service be deployed independently?
- [ ] Does a database change require coordinated deployments?
- [ ] Are there shared libraries with business logic?
- [ ] Does one service failure cascade to others?

---

### 2. Nanoservices

**Symptom**: Services too small to justify their operational overhead.

```python
# ANTI-PATTERN: Nanoservices
# Separate service just for email validation

# email-validation-service/main.py
@app.post("/validate")
def validate_email(email: str):
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return {"valid": bool(re.match(pattern, email))}

# Problems:
# - Network call for simple regex
# - Deployment overhead for 10 lines of code
# - Latency added to every user creation
```

**Solution**:

```python
# CORRECT: Include in relevant service
# user-service/validators.py
def validate_email(email: str) -> bool:
    """Email validation belongs with user domain."""
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

# Use directly
class UserService:
    def create_user(self, email: str, ...):
        if not validate_email(email):
            raise ValidationError("Invalid email")
        ...
```

**Rule of Thumb**: If a service has:
- < 500 lines of business logic
- Single responsibility that's too narrow
- No independent scaling needs
- No separate data ownership

→ It should probably be part of another service.

---

### 3. Chatty Services

**Symptom**: Too many synchronous calls between services for single operations.

```python
# ANTI-PATTERN: Chatty communication
async def get_order_details(order_id: str):
    # 6 synchronous network calls for one user request!
    order = await order_service.get(order_id)
    customer = await customer_service.get(order.customer_id)
    address = await address_service.get(customer.address_id)

    items = []
    for item in order.items:
        product = await product_service.get(item.product_id)
        inventory = await inventory_service.get(item.product_id)
        items.append({**item, "product": product, "stock": inventory})

    return {"order": order, "customer": customer, "items": items}

# Problems:
# - High latency (sum of all calls)
# - Any service failure breaks the request
# - N+1 query problem across network
```

**Solutions**:

```python
# Solution 1: Parallel calls
async def get_order_details(order_id: str):
    order = await order_service.get(order_id)

    # Parallel calls where possible
    customer, products = await asyncio.gather(
        customer_service.get_with_address(order.customer_id),
        product_service.get_many([i.product_id for i in order.items])
    )
    return {"order": order, "customer": customer, "products": products}

# Solution 2: API composition in BFF
# The BFF maintains denormalized data

# Solution 3: Event-driven data sync
# Order service subscribes to product updates
# Maintains local cache of needed product data
```

---

### 4. Synchronous Dependency Chains

**Symptom**: Long chains of synchronous service calls.

```
ANTI-PATTERN: Sync Chain

User Request
     │
     ▼
┌─────────┐    sync    ┌─────────┐    sync    ┌─────────┐    sync    ┌─────────┐
│ API GW  │───────────▶│ Order   │───────────▶│ Payment │───────────▶│ Fraud   │
└─────────┘            └─────────┘            └─────────┘            └─────────┘

Problems:
- Latency = sum of all services
- Availability = product of all availabilities
  (99.9% × 99.9% × 99.9% = 99.7%)
- One slow service blocks everything
```

**Solution**:

```
CORRECT: Async Processing

User Request                              Background Processing
     │                                           │
     ▼                                           ▼
┌─────────┐  create   ┌─────────┐  event   ┌─────────┐
│ API GW  │──────────▶│ Order   │─────────▶│  Queue  │
└─────────┘           └─────────┘          └────┬────┘
     │                                          │
     │ Response: "Order received"               ├────────────────┐
     │ (202 Accepted)                           ▼                ▼
     ▼                                    ┌─────────┐      ┌─────────┐
  [User]                                  │ Payment │      │ Fraud   │
                                          └─────────┘      └─────────┘
```

---

### 5. Shared Libraries with Business Logic

**Symptom**: Common libraries containing domain logic that all services depend on.

```python
# ANTI-PATTERN: shared-lib/order_utils.py
# This library is used by 5 different services

def calculate_order_total(items, discounts, tax_rate):
    """Business logic in shared library."""
    subtotal = sum(i.price * i.quantity for i in items)
    discount = apply_discounts(subtotal, discounts)  # Complex rules
    tax = calculate_tax(subtotal - discount, tax_rate)  # More rules
    return subtotal - discount + tax

# Problems:
# - Changes require redeploying all services
# - Version conflicts across services
# - Testing becomes complex
# - Tight coupling through shared code
```

**Solution**:

```python
# CORRECT: Logic lives in owning service
# order-service/domain/pricing.py

class OrderPricingService:
    """Pricing logic owned by order service."""

    def calculate_total(self, items, discounts, tax_rate):
        # Logic stays here
        ...

# Other services call order service API if they need pricing
# OR use events to get pre-calculated totals

# Acceptable shared libraries:
# - Logging utilities
# - HTTP client wrappers
# - Serialization helpers
# - NOT business logic
```

---

## Data Anti-Patterns

### 6. Shared Database

**Symptom**: Multiple services reading/writing to same database tables.

```
ANTI-PATTERN: Shared Database

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Service A  │    │  Service B  │    │  Service C  │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │    Direct        │    Direct        │
       │    Access        │    Access        │
       ▼                  ▼                  ▼
       └──────────────────┴──────────────────┘
                          │
                   ┌──────┴──────┐
                   │   orders    │
                   │   table     │
                   └─────────────┘

Problems:
- Schema changes break all services
- No encapsulation of data access
- Locking conflicts
- Can't scale databases independently
```

**Solution**: Database per service (see data-management.md)

---

### 7. Using Database for Inter-Service Communication

**Symptom**: Services communicate by reading/writing to shared tables.

```python
# ANTI-PATTERN: Database as message queue
# Service A writes
async def complete_order(order_id: str):
    await db.execute(
        "UPDATE orders SET status = 'completed' WHERE id = $1",
        order_id
    )
    # Inventory service will poll for completed orders...

# Service B polls
async def check_for_completed_orders():
    while True:
        orders = await db.fetch(
            "SELECT * FROM orders WHERE status = 'completed' AND processed = FALSE"
        )
        for order in orders:
            await release_inventory(order)
            await db.execute(
                "UPDATE orders SET processed = TRUE WHERE id = $1",
                order["id"]
            )
        await asyncio.sleep(5)  # Poll every 5 seconds

# Problems:
# - Polling is inefficient
# - Race conditions
# - Tight coupling through schema
# - No delivery guarantees
```

**Solution**:

```python
# CORRECT: Event-driven communication
# Service A publishes
async def complete_order(order_id: str):
    order = await db.update_status(order_id, "completed")
    await event_bus.publish("order.completed", {
        "order_id": order_id,
        "items": order.items
    })

# Service B subscribes
@event_handler("order.completed")
async def handle_order_completed(event):
    await release_inventory(event["order_id"], event["items"])
```

---

## Communication Anti-Patterns

### 8. No Timeouts

**Symptom**: Services wait indefinitely for downstream responses.

```python
# ANTI-PATTERN: No timeout
async def get_user(user_id: str):
    # If user service is slow/hung, this waits forever
    response = await httpx.get(f"http://user-service/users/{user_id}")
    return response.json()

# This can:
# - Exhaust connection pools
# - Block threads/coroutines
# - Cascade failures upstream
```

**Solution**:

```python
# CORRECT: Always set timeouts
async def get_user(user_id: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://user-service/users/{user_id}")
            return response.json()
    except httpx.TimeoutException:
        logger.warning(f"User service timeout for {user_id}")
        raise ServiceUnavailableError("User service unavailable")
```

---

### 9. Ignoring Network Failures

**Symptom**: Code assumes network calls always succeed.

```python
# ANTI-PATTERN: No error handling
async def create_order(request):
    # If any call fails, we have inconsistent state
    order = await order_db.create(request)
    await inventory_service.reserve(order.items)  # Might fail
    await payment_service.charge(order.total)      # Might fail
    await notification_service.send(order)         # Might fail
    return order

# Problems:
# - Order created but inventory not reserved
# - Payment charged but order not confirmed
# - No way to recover
```

**Solution**:

```python
# CORRECT: Handle failures, use saga pattern
async def create_order(request):
    order = None
    reservation = None
    payment = None

    try:
        order = await order_db.create(request, status="pending")
        reservation = await inventory_service.reserve(order.items)
        payment = await payment_service.charge(order.total)
        await order_db.update_status(order.id, "confirmed")
        return order
    except InventoryError:
        if order:
            await order_db.update_status(order.id, "failed")
        raise
    except PaymentError:
        if reservation:
            await inventory_service.release(reservation.id)
        if order:
            await order_db.update_status(order.id, "failed")
        raise
```

---

### 10. Sync Over Async Abuse

**Symptom**: Using synchronous patterns where async would be more appropriate.

```python
# ANTI-PATTERN: Sync call for non-critical operation
@app.post("/orders")
async def create_order(request):
    order = await order_service.create(request)

    # User waits while email sends (500ms+ latency added)
    await email_service.send_confirmation(order)

    # User waits while analytics records
    await analytics_service.track_order(order)

    return order  # User waited for non-critical operations
```

**Solution**:

```python
# CORRECT: Async for non-critical operations
@app.post("/orders")
async def create_order(request):
    order = await order_service.create(request)

    # Fire and forget - user doesn't wait
    asyncio.create_task(email_service.send_confirmation(order))

    # Publish event for decoupled processing
    await event_bus.publish("order.created", order)

    return order  # Immediate response
```

---

## Operational Anti-Patterns

### 11. No Observability

**Symptom**: Can't answer "what happened to request X?"

```python
# ANTI-PATTERN: No logging, no tracing
async def process_order(order_id: str):
    order = await get_order(order_id)
    inventory = await check_inventory(order)
    payment = await process_payment(order)
    return order

# When something fails:
# - Which service failed?
# - What was the request?
# - What was the state?
# - Who knows! Good luck debugging.
```

**Solution**: See observability.md for comprehensive implementation.

---

### 12. Missing Health Checks

**Symptom**: Load balancer routes traffic to unhealthy instances.

```yaml
# ANTI-PATTERN: No health checks
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: order-service
          image: order-service:latest
          # No probes defined
          # Container might be running but not ready
          # Database connection might be broken
          # Still receives traffic!
```

**Solution**: See resilience-patterns.md for health check implementation.

---

### 13. Hardcoded Configuration

**Symptom**: Environment-specific values in code.

```python
# ANTI-PATTERN: Hardcoded config
class OrderService:
    def __init__(self):
        self.db_url = "postgresql://user:pass@prod-db:5432/orders"
        self.payment_url = "http://payment-service:8080"
        self.timeout = 30

# Problems:
# - Different values needed per environment
# - Secrets in code
# - Requires code change to update config
```

**Solution**:

```python
# CORRECT: External configuration
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    payment_service_url: str
    request_timeout: int = 30

    class Config:
        env_file = ".env"

settings = Settings()

class OrderService:
    def __init__(self, settings: Settings):
        self.db_url = settings.database_url
        self.payment_url = settings.payment_service_url
```

---

## Design Anti-Patterns

### 14. God Service

**Symptom**: One service that does everything.

```
ANTI-PATTERN: God Service

                    ┌─────────────────────────────┐
                    │         Core Service        │
                    │                             │
                    │  - User management          │
                    │  - Order processing         │
                    │  - Payment handling         │
                    │  - Inventory tracking       │
                    │  - Shipping logistics       │
                    │  - Reporting               │
                    │  - Notifications           │
                    │  - Analytics               │
                    │                             │
                    └─────────────────────────────┘

Problems:
- Single point of failure
- Can't scale components independently
- Changes affect entire system
- Too complex to understand
```

**Solution**: Decompose by business capability (see decomposition-strategies.md)

---

### 15. Wrong Service Boundaries

**Symptom**: Frequent cross-service changes, high coupling.

```
ANTI-PATTERN: Technical Boundaries

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Frontend   │  │   Backend   │  │  Database   │
│   Service   │  │   Service   │  │   Service   │
└─────────────┘  └─────────────┘  └─────────────┘

# Every feature requires changes to all three services
```

**Solution**:

```
CORRECT: Business Capability Boundaries

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    Order    │  │   Payment   │  │  Shipping   │
│   Service   │  │   Service   │  │   Service   │
│  (API+DB)   │  │  (API+DB)   │  │  (API+DB)   │
└─────────────┘  └─────────────┘  └─────────────┘

# Each service owns full stack for its capability
# Features usually change one service
```

---

## Anti-Pattern Detection Checklist

Use this during architecture reviews:

### Coupling
- [ ] Can services be deployed independently?
- [ ] Do services share databases?
- [ ] Are there shared libraries with business logic?
- [ ] Do changes require coordinated deployments?

### Communication
- [ ] Are there long synchronous call chains?
- [ ] Are all calls protected with timeouts?
- [ ] Is error handling comprehensive?
- [ ] Are non-critical operations async?

### Data
- [ ] Does each service own its data?
- [ ] Are services communicating via database?
- [ ] Is there a clear consistency strategy?

### Operations
- [ ] Are services observable (logs, metrics, traces)?
- [ ] Are health checks implemented?
- [ ] Is configuration externalized?

### Design
- [ ] Are service boundaries aligned with business capabilities?
- [ ] Are services appropriately sized (not nano, not god)?
- [ ] Is the API contract well-defined?

---

## Recovery Strategies

When you've identified an anti-pattern:

| Anti-Pattern | Recovery Strategy |
|--------------|-------------------|
| Distributed Monolith | Identify coupling, extract with strangler fig |
| Nanoservices | Merge into appropriate bounded context |
| Shared Database | Event-driven sync, gradual data migration |
| Sync Chains | Introduce async messaging, saga pattern |
| God Service | Domain-driven decomposition |
| No Observability | Incremental instrumentation |
