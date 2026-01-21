# Testing Strategies

## Overview

Microservices testing requires strategies that validate both individual services and their interactions. The testing pyramid adapts to distributed systems with emphasis on contract and integration testing.

---

## Testing Pyramid for Microservices

```
                    ┌───────────────┐
                    │   E2E Tests   │  Few, slow, expensive
                    │   (UI/API)    │
                    └───────┬───────┘
                    ┌───────┴───────┐
                    │  Integration  │  Service interactions
                    │    Tests      │
                    └───────┬───────┘
              ┌─────────────┴─────────────┐
              │     Contract Tests        │  API contracts
              │    (Consumer-driven)      │
              └─────────────┬─────────────┘
        ┌───────────────────┴───────────────────┐
        │           Component Tests             │  Single service
        │         (with test doubles)           │
        └───────────────────┬───────────────────┘
   ┌────────────────────────┴────────────────────────┐
   │                   Unit Tests                    │  Fast, many
   │              (Business logic)                   │
   └─────────────────────────────────────────────────┘
```

| Level | Scope | Speed | Reliability |
|-------|-------|-------|-------------|
| Unit | Function/Class | ms | High |
| Component | Single service | seconds | High |
| Contract | API boundaries | seconds | High |
| Integration | Multiple services | minutes | Medium |
| E2E | Full system | minutes | Lower |

---

## Unit Testing

### Testing Business Logic

```python
import pytest
from decimal import Decimal
from order_service.domain import Order, OrderItem, OrderStatus

class TestOrder:
    def test_calculate_total(self):
        order = Order(
            id="ord_123",
            items=[
                OrderItem(product_id="prod_1", price=Decimal("10.00"), quantity=2),
                OrderItem(product_id="prod_2", price=Decimal("25.00"), quantity=1)
            ]
        )
        assert order.total == Decimal("45.00")

    def test_apply_discount(self):
        order = Order(id="ord_123", items=[
            OrderItem(product_id="prod_1", price=Decimal("100.00"), quantity=1)
        ])
        order.apply_discount(percentage=10)
        assert order.total == Decimal("90.00")

    def test_cannot_confirm_empty_order(self):
        order = Order(id="ord_123", items=[])
        with pytest.raises(ValueError, match="Cannot confirm empty order"):
            order.confirm()

    def test_status_transitions(self):
        order = Order(id="ord_123", items=[
            OrderItem(product_id="prod_1", price=Decimal("10.00"), quantity=1)
        ])
        assert order.status == OrderStatus.PENDING

        order.confirm()
        assert order.status == OrderStatus.CONFIRMED

        order.ship(tracking_number="TRACK123")
        assert order.status == OrderStatus.SHIPPED

        # Cannot go back to pending
        with pytest.raises(ValueError, match="Invalid status transition"):
            order.status = OrderStatus.PENDING
```

### Mocking External Dependencies

```python
import pytest
from unittest.mock import AsyncMock, patch
from order_service.service import OrderService

@pytest.fixture
def mock_inventory_client():
    client = AsyncMock()
    client.check_availability.return_value = {"available": True, "quantity": 100}
    client.reserve.return_value = {"reservation_id": "res_123"}
    return client

@pytest.fixture
def mock_payment_client():
    client = AsyncMock()
    client.charge.return_value = {"payment_id": "pay_123", "status": "success"}
    return client

@pytest.fixture
def order_service(mock_inventory_client, mock_payment_client):
    return OrderService(
        inventory_client=mock_inventory_client,
        payment_client=mock_payment_client
    )

class TestOrderService:
    @pytest.mark.asyncio
    async def test_create_order_success(self, order_service, mock_inventory_client):
        request = CreateOrderRequest(
            customer_id="cust_123",
            items=[{"product_id": "prod_1", "quantity": 2}]
        )

        order = await order_service.create(request)

        assert order.status == OrderStatus.PENDING
        mock_inventory_client.check_availability.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_insufficient_inventory(
        self, order_service, mock_inventory_client
    ):
        mock_inventory_client.check_availability.return_value = {
            "available": False, "quantity": 0
        }

        with pytest.raises(InsufficientInventoryError):
            await order_service.create(CreateOrderRequest(
                customer_id="cust_123",
                items=[{"product_id": "prod_1", "quantity": 100}]
            ))
```

---

## Component Testing

Test a single service with real dependencies (database, cache) but mocked external services.

```python
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from httpx import AsyncClient
from order_service.main import create_app

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis():
    with RedisContainer("redis:7") as redis:
        yield redis

@pytest.fixture
async def app(postgres, redis, mocker):
    # Mock external services
    mocker.patch(
        "order_service.clients.inventory.InventoryClient.check_availability",
        return_value={"available": True}
    )
    mocker.patch(
        "order_service.clients.payment.PaymentClient.charge",
        return_value={"payment_id": "pay_123"}
    )

    app = create_app(
        database_url=postgres.get_connection_url(),
        redis_url=redis.get_connection_url()
    )

    # Run migrations
    await run_migrations(postgres.get_connection_url())

    yield app

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

class TestOrderAPI:
    @pytest.mark.asyncio
    async def test_create_order(self, client):
        response = await client.post("/api/orders", json={
            "customer_id": "cust_123",
            "items": [{"product_id": "prod_1", "quantity": 2, "price": 10.00}]
        })

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["total"] == 20.00

    @pytest.mark.asyncio
    async def test_get_order(self, client):
        # Create order first
        create_response = await client.post("/api/orders", json={
            "customer_id": "cust_123",
            "items": [{"product_id": "prod_1", "quantity": 1, "price": 10.00}]
        })
        order_id = create_response.json()["id"]

        # Get order
        response = await client.get(f"/api/orders/{order_id}")

        assert response.status_code == 200
        assert response.json()["id"] == order_id

    @pytest.mark.asyncio
    async def test_order_not_found(self, client):
        response = await client.get("/api/orders/nonexistent")
        assert response.status_code == 404
```

---

## Contract Testing

### Consumer-Driven Contract Testing with Pact

**Consumer Side (Order Service calling Inventory Service)**

```python
# test_inventory_contract.py
import pytest
from pact import Consumer, Provider
from order_service.clients.inventory import InventoryClient

@pytest.fixture(scope="session")
def pact():
    pact = Consumer("order-service").has_pact_with(
        Provider("inventory-service"),
        pact_dir="./pacts"
    )
    pact.start_service()
    yield pact
    pact.stop_service()

class TestInventoryContract:
    def test_check_availability(self, pact):
        # Define expected interaction
        pact.given(
            "product prod_123 exists with quantity 50"
        ).upon_receiving(
            "a request to check availability"
        ).with_request(
            method="GET",
            path="/api/inventory/prod_123",
            headers={"Accept": "application/json"}
        ).will_respond_with(
            status=200,
            headers={"Content-Type": "application/json"},
            body={
                "product_id": "prod_123",
                "available": True,
                "quantity": 50
            }
        )

        with pact:
            # Test actual client
            client = InventoryClient(base_url=pact.uri)
            result = client.check_availability("prod_123")

            assert result["available"] is True
            assert result["quantity"] == 50

    def test_product_not_found(self, pact):
        pact.given(
            "product nonexistent does not exist"
        ).upon_receiving(
            "a request for nonexistent product"
        ).with_request(
            method="GET",
            path="/api/inventory/nonexistent"
        ).will_respond_with(
            status=404,
            body={"error": "Product not found"}
        )

        with pact:
            client = InventoryClient(base_url=pact.uri)
            with pytest.raises(ProductNotFoundError):
                client.check_availability("nonexistent")
```

**Provider Side (Inventory Service verifying contracts)**

```python
# test_pact_verification.py
import pytest
from pact import Verifier
from inventory_service.main import create_app

@pytest.fixture
def app():
    return create_app()

def test_pact_verification(app):
    verifier = Verifier(
        provider="inventory-service",
        provider_base_url="http://localhost:8080"
    )

    # Set up provider states
    verifier.set_state_handler(
        "product prod_123 exists with quantity 50",
        lambda: setup_product("prod_123", quantity=50)
    )

    verifier.set_state_handler(
        "product nonexistent does not exist",
        lambda: None  # No setup needed
    )

    # Verify against pacts from broker
    output, _ = verifier.verify_pacts(
        pact_urls=[
            "https://pact-broker.example.com/pacts/provider/inventory-service/consumer/order-service/latest"
        ],
        enable_pending=True,
        publish_verification_results=True,
        provider_version="1.0.0"
    )

    assert output == 0
```

### Contract Testing CI Pipeline

```yaml
# .github/workflows/contract-tests.yml
name: Contract Tests

on: [push, pull_request]

jobs:
  consumer-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run consumer contract tests
        run: pytest tests/contracts/

      - name: Publish pacts to broker
        run: |
          pact-broker publish ./pacts \
            --consumer-app-version=${{ github.sha }} \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }}

  provider-verification:
    runs-on: ubuntu-latest
    needs: consumer-tests
    steps:
      - uses: actions/checkout@v4

      - name: Verify provider contracts
        run: pytest tests/pact_verification.py
        env:
          PACT_BROKER_URL: ${{ secrets.PACT_BROKER_URL }}

      - name: Can I deploy?
        run: |
          pact-broker can-i-deploy \
            --pacticipant=order-service \
            --version=${{ github.sha }} \
            --to-environment=production
```

---

## Integration Testing

### TestContainers for Real Dependencies

```python
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def docker_compose():
    """Spin up entire service mesh for integration tests."""
    with DockerCompose(
        filepath="./tests/integration",
        compose_file_name="docker-compose.test.yml",
        pull=True
    ) as compose:
        compose.wait_for("http://localhost:8080/health")
        compose.wait_for("http://localhost:8081/health")
        yield compose

class TestOrderToPaymentIntegration:
    @pytest.mark.asyncio
    async def test_order_payment_flow(self, docker_compose):
        async with httpx.AsyncClient() as client:
            # Create order
            order_response = await client.post(
                "http://localhost:8080/api/orders",
                json={
                    "customer_id": "cust_123",
                    "items": [{"product_id": "prod_1", "quantity": 1}],
                    "payment_method": "credit_card"
                }
            )
            assert order_response.status_code == 201
            order_id = order_response.json()["id"]

            # Confirm order (triggers payment)
            confirm_response = await client.post(
                f"http://localhost:8080/api/orders/{order_id}/confirm"
            )
            assert confirm_response.status_code == 200

            # Verify payment was processed
            await asyncio.sleep(2)  # Wait for async processing

            payment_response = await client.get(
                f"http://localhost:8081/api/payments/order/{order_id}"
            )
            assert payment_response.status_code == 200
            assert payment_response.json()["status"] == "completed"
```

### Integration Test Docker Compose

```yaml
# tests/integration/docker-compose.test.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test"]
      interval: 5s
      timeout: 5s
      retries: 5

  order-service:
    build: ../../services/order-service
    environment:
      DATABASE_URL: postgresql://test:test@postgres/test
      PAYMENT_SERVICE_URL: http://payment-service:8080
      INVENTORY_SERVICE_URL: http://inventory-service:8080
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8080:8080"

  payment-service:
    build: ../../services/payment-service
    environment:
      DATABASE_URL: postgresql://test:test@postgres/test
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8081:8080"

  inventory-service:
    build: ../../services/inventory-service
    environment:
      DATABASE_URL: postgresql://test:test@postgres/test
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8082:8080"
```

---

## Chaos Engineering

### Principles

1. **Define steady state**: Normal system behavior (latency, error rate)
2. **Hypothesize**: "System will remain stable if X fails"
3. **Inject failure**: Network, pod, resource failures
4. **Verify hypothesis**: Compare to steady state
5. **Fix weaknesses**: Address discovered issues

### Chaos Mesh Experiments

```yaml
# Network delay experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
  namespace: production
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: payment-service
  delay:
    latency: "500ms"
    correlation: "100"
    jitter: "100ms"
  duration: "5m"

---
# Pod failure experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill
  namespace: production
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: inventory-service
  scheduler:
    cron: "@every 10m"

---
# CPU stress experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: cpu-stress
  namespace: production
spec:
  mode: one
  selector:
    labelSelectors:
      app: order-service
  stressors:
    cpu:
      workers: 2
      load: 80
  duration: "5m"
```

### Chaos Engineering Test

```python
import pytest
from chaos_mesh_client import ChaosMeshClient

@pytest.fixture
def chaos_client():
    return ChaosMeshClient(namespace="production")

class TestResilience:
    @pytest.mark.chaos
    async def test_payment_service_latency(self, chaos_client, client):
        """System should handle payment service delays gracefully."""
        # Record baseline
        baseline = await measure_order_latency(client, samples=10)

        # Inject 500ms delay to payment service
        experiment = chaos_client.inject_network_delay(
            target="payment-service",
            latency="500ms",
            duration="2m"
        )

        try:
            # Measure during chaos
            chaos_latency = await measure_order_latency(client, samples=10)

            # Verify graceful degradation
            assert chaos_latency.p99 < baseline.p99 + 1000  # Max 1s increase
            assert chaos_latency.error_rate < 0.01  # <1% errors

            # Verify circuit breaker activated if needed
            metrics = await get_circuit_breaker_metrics("payment-service")
            if chaos_latency.p99 > 2000:
                assert metrics["state"] == "open"
        finally:
            await experiment.cleanup()

    @pytest.mark.chaos
    async def test_inventory_service_failure(self, chaos_client, client):
        """System should handle inventory service outage."""
        # Kill inventory service pods
        experiment = chaos_client.inject_pod_failure(
            target="inventory-service",
            mode="all",
            duration="1m"
        )

        try:
            # Orders should fail gracefully
            response = await client.post("/api/orders", json={
                "customer_id": "cust_123",
                "items": [{"product_id": "prod_1", "quantity": 1}]
            })

            # Should get service unavailable, not 500
            assert response.status_code == 503
            assert "inventory service unavailable" in response.json()["error"]
        finally:
            await experiment.cleanup()
```

### Game Day Runbook

```markdown
# Chaos Game Day Runbook

## Pre-Game Checklist
- [ ] Notify stakeholders
- [ ] Ensure monitoring dashboards open
- [ ] Verify rollback procedures
- [ ] Have incident channel ready

## Experiments

### Experiment 1: Database Failover
**Hypothesis**: Order service continues with <5s interruption during DB failover

**Steps**:
1. Record baseline metrics
2. Trigger DB failover: `aws rds failover-db-cluster --db-cluster-id orders-db`
3. Monitor order creation success rate
4. Verify reconnection within 30s

**Success Criteria**:
- Error rate < 1% during failover
- Recovery < 30 seconds
- No data loss

### Experiment 2: Network Partition
**Hypothesis**: Services degrade gracefully when order→payment network partitioned

**Steps**:
1. Apply NetworkPolicy blocking order→payment
2. Attempt order confirmations
3. Verify circuit breaker activates
4. Remove partition, verify recovery

**Success Criteria**:
- Circuit breaker opens within 30s
- Requests fail fast (< 1s timeout)
- Recovery within 60s of partition removal
```

---

## Performance Testing

### Locust Load Test

```python
# locustfile.py
from locust import HttpUser, task, between
import random

class OrderServiceUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://order-service:8080"

    def on_start(self):
        """Login and get auth token."""
        response = self.client.post("/auth/login", json={
            "username": "loadtest@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def list_orders(self):
        """Most common operation."""
        self.client.get("/api/orders", headers=self.headers)

    @task(5)
    def get_order(self):
        """Get specific order."""
        order_id = random.choice(self.order_ids) if hasattr(self, 'order_ids') else "ord_123"
        self.client.get(f"/api/orders/{order_id}", headers=self.headers)

    @task(2)
    def create_order(self):
        """Create new order."""
        response = self.client.post(
            "/api/orders",
            json={
                "customer_id": f"cust_{random.randint(1, 1000)}",
                "items": [
                    {
                        "product_id": f"prod_{random.randint(1, 100)}",
                        "quantity": random.randint(1, 5),
                        "price": random.uniform(10, 100)
                    }
                    for _ in range(random.randint(1, 3))
                ]
            },
            headers=self.headers
        )
        if response.status_code == 201:
            if not hasattr(self, 'order_ids'):
                self.order_ids = []
            self.order_ids.append(response.json()["id"])

    @task(1)
    def search_products(self):
        """Search products."""
        query = random.choice(["laptop", "phone", "tablet", "camera"])
        self.client.get(f"/api/products/search?q={query}", headers=self.headers)
```

### Performance Test Configuration

```yaml
# k6 load test
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const orderLatency = new Trend('order_creation_latency');

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp to 200
    { duration: '5m', target: 200 },   // Stay at 200
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.01'],
    order_creation_latency: ['p(95)<1000'],
  },
};

export default function () {
  const start = Date.now();

  const response = http.post(
    'http://order-service:8080/api/orders',
    JSON.stringify({
      customer_id: `cust_${Math.random()}`,
      items: [{ product_id: 'prod_1', quantity: 1 }]
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  orderLatency.add(Date.now() - start);

  const success = check(response, {
    'status is 201': (r) => r.status === 201,
    'has order id': (r) => r.json('id') !== undefined,
  });

  errorRate.add(!success);
  sleep(1);
}
```

### Performance CI Integration

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to performance environment
        run: |
          kubectl apply -k ./k8s/overlays/performance

      - name: Run Locust tests
        run: |
          locust -f tests/performance/locustfile.py \
            --headless \
            --users 200 \
            --spawn-rate 10 \
            --run-time 10m \
            --html report.html \
            --csv results

      - name: Check thresholds
        run: |
          python scripts/check_performance_thresholds.py results_stats.csv

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: |
            report.html
            results_*.csv
```

---

## Implementation Checklist

- [ ] **Unit Tests**: Business logic covered (>80%)
- [ ] **Component Tests**: API endpoints tested with real DB
- [ ] **Contract Tests**: Pact contracts for all service interactions
- [ ] **Integration Tests**: Critical flows tested end-to-end
- [ ] **Chaos Tests**: Failure scenarios validated
- [ ] **Performance Tests**: Load tests run regularly
- [ ] **CI Pipeline**: All test types automated
- [ ] **Test Data**: Fixtures and factories for consistent data
