# Observability

## Overview

Observability enables understanding system behavior through external outputs. In microservices, it's essential for debugging distributed systems where traditional debugging is impossible.

---

## Three Pillars of Observability

```
┌─────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY                           │
├───────────────────┬───────────────────┬─────────────────────┤
│      TRACES       │      METRICS      │       LOGS          │
│   Request flow    │   Aggregated      │   Discrete events   │
│   across services │   measurements    │   with context      │
├───────────────────┼───────────────────┼─────────────────────┤
│   "What happened  │   "What's the     │   "What happened    │
│    to request X?" │    system state?" │    at time T?"      │
└───────────────────┴───────────────────┴─────────────────────┘
```

| Pillar | Purpose | Tool Examples |
|--------|---------|---------------|
| **Traces** | Follow request across services | Jaeger, Zipkin, Tempo |
| **Metrics** | Aggregate measurements over time | Prometheus, InfluxDB |
| **Logs** | Detailed event records | ELK Stack, Loki |

---

## Distributed Tracing

### OpenTelemetry Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource

def setup_tracing(service_name: str):
    """Configure OpenTelemetry tracing."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENV", "development")
    })

    provider = TracerProvider(resource=resource)

    # Export to Jaeger/Tempo via OTLP
    exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317"),
        insecure=True
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

    return trace.get_tracer(service_name)

# Usage
tracer = setup_tracing("order-service")

@app.post("/orders")
async def create_order(request: CreateOrderRequest):
    with tracer.start_as_current_span("create_order") as span:
        span.set_attribute("order.customer_id", request.customer_id)
        span.set_attribute("order.item_count", len(request.items))

        # Child spans created automatically for HTTP calls
        inventory = await inventory_service.reserve(request.items)
        payment = await payment_service.charge(request.payment)

        span.set_attribute("order.id", order.id)
        span.set_status(trace.Status(trace.StatusCode.OK))

        return order
```

### Context Propagation

```python
from opentelemetry import propagate
from opentelemetry.propagators.b3 import B3MultiFormat
import httpx

# Set up W3C Trace Context + B3 propagation
propagate.set_global_textmap(
    propagate.CompositeHTTPPropagator([
        propagate.get_global_textmap(),  # W3C TraceContext
        B3MultiFormat()  # For Zipkin compatibility
    ])
)

async def call_downstream_service(url: str, data: dict):
    """HTTP call with trace context propagation."""
    headers = {}
    # Inject current trace context into headers
    propagate.inject(headers)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        return response.json()
```

### Trace Visualization

```
Order Service          Inventory Service       Payment Service
     │                        │                       │
     │ create_order           │                       │
     ├─────────────────────────────────────────────────
     │                        │                       │
     │ ──reserve_items──────▶ │                       │
     │                        │ check_stock           │
     │                        ├─────────┐             │
     │                        │         │             │
     │                        │◀────────┘             │
     │ ◀─────────────────────┤                       │
     │                        │                       │
     │ ──process_payment──────────────────────────▶  │
     │                        │                       │ charge_card
     │                        │                       ├─────────┐
     │                        │                       │         │
     │                        │                       │◀────────┘
     │ ◀──────────────────────────────────────────── │
     │                        │                       │
```

---

## Metrics

### Metrics Methods

#### RED Method (Request-focused)

| Metric | Description | Example |
|--------|-------------|---------|
| **R**ate | Requests per second | `rate(http_requests_total[5m])` |
| **E**rrors | Failed requests per second | `rate(http_requests_total{status=~"5.."}[5m])` |
| **D**uration | Request latency distribution | `histogram_quantile(0.99, http_request_duration_seconds_bucket)` |

#### USE Method (Resource-focused)

| Metric | Description | Example |
|--------|-------------|---------|
| **U**tilization | Resource busy percentage | `avg(cpu_usage_percent)` |
| **S**aturation | Queue depth / backlog | `avg(thread_pool_queue_size)` |
| **E**rrors | Error count | `rate(error_total[5m])` |

#### Four Golden Signals (Google SRE)

| Signal | Description |
|--------|-------------|
| **Latency** | Time to service a request |
| **Traffic** | Demand on the system |
| **Errors** | Rate of failed requests |
| **Saturation** | How "full" the service is |

### Prometheus Instrumentation

```python
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
)

IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

DB_POOL_SIZE = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    ['state']  # active, idle, waiting
)

SERVICE_INFO = Info(
    'service',
    'Service information'
)
SERVICE_INFO.info({
    'version': '1.2.3',
    'python_version': '3.11'
})

# Middleware for automatic instrumentation
def metrics_middleware(func):
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        method = request.method
        endpoint = request.url.path

        IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        start_time = time.time()

        try:
            response = await func(request, *args, **kwargs)
            status = response.status_code
            return response
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

    return wrapper

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

### Custom Business Metrics

```python
# Business metrics
ORDERS_CREATED = Counter(
    'orders_created_total',
    'Total orders created',
    ['status', 'payment_method']
)

ORDER_VALUE = Histogram(
    'order_value_dollars',
    'Order value distribution',
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

INVENTORY_LEVEL = Gauge(
    'inventory_level',
    'Current inventory level',
    ['product_id', 'warehouse']
)

async def create_order(order: Order):
    # ... create order logic ...

    # Record metrics
    ORDERS_CREATED.labels(
        status='created',
        payment_method=order.payment_method
    ).inc()
    ORDER_VALUE.observe(order.total_amount)
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'

scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

### PromQL Examples

```promql
# Request rate per service
rate(http_requests_total{job="order-service"}[5m])

# Error rate percentage
100 * (
  rate(http_requests_total{status=~"5.."}[5m])
  /
  rate(http_requests_total[5m])
)

# P99 latency
histogram_quantile(0.99,
  rate(http_request_duration_seconds_bucket[5m])
)

# Apdex score (target: 0.5s, tolerable: 2s)
(
  sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
  +
  sum(rate(http_request_duration_seconds_bucket{le="2"}[5m]))
) / 2 / sum(rate(http_request_duration_seconds_count[5m]))

# Saturation - connection pool usage
db_connection_pool_size{state="active"}
/
db_connection_pool_size{state="total"}
```

---

## Alerting Rules

```yaml
# alerts.yml
groups:
  - name: service-alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
            /
            sum(rate(http_requests_total[5m])) by (service)
          ) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P99 latency on {{ $labels.service }}"
          description: "P99 latency is {{ $value | humanizeDuration }}"

      # Service down
      - alert: ServiceDown
        expr: up{job=~".*-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"

      # Pod memory high
      - alert: PodMemoryHigh
        expr: |
          container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.pod }} memory usage > 90%"
```

---

## Grafana Dashboards

### Service Dashboard JSON

```json
{
  "title": "Microservice Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[5m])) by (service)",
          "legendFormat": "{{ service }}"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service) * 100",
          "legendFormat": "{{ service }}"
        }
      ],
      "alert": {
        "conditions": [
          {
            "evaluator": {"type": "gt", "params": [5]},
            "reducer": {"type": "avg"}
          }
        ]
      }
    },
    {
      "title": "P50/P95/P99 Latency",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "{{ service }} P50"
        },
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "{{ service }} P95"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "{{ service }} P99"
        }
      ]
    }
  ]
}
```

---

## Structured Logging

### Log Format

```python
import structlog
import logging
from opentelemetry import trace

def setup_logging(service_name: str):
    """Configure structured logging with trace correlation."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_trace_context,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

def add_trace_context(logger, method_name, event_dict):
    """Add trace context to log entries."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, '032x')
        event_dict["span_id"] = format(ctx.span_id, '016x')
    return event_dict

# Usage
logger = structlog.get_logger()

@app.post("/orders")
async def create_order(request: CreateOrderRequest):
    logger.info(
        "creating_order",
        customer_id=request.customer_id,
        item_count=len(request.items),
        total_amount=request.total
    )

    try:
        order = await order_service.create(request)
        logger.info(
            "order_created",
            order_id=order.id,
            processing_time_ms=elapsed_ms
        )
        return order
    except InsufficientInventoryError as e:
        logger.warning(
            "order_creation_failed",
            reason="insufficient_inventory",
            missing_items=e.missing_items
        )
        raise
```

### Log Output

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "order_created",
  "service": "order-service",
  "trace_id": "abc123def456789",
  "span_id": "def456789",
  "order_id": "ord_12345",
  "customer_id": "cust_67890",
  "processing_time_ms": 234
}
```

### Log Correlation Query (Loki/Grafana)

```logql
{service="order-service"} |= "order_created"
| json
| trace_id = "abc123def456789"
```

---

## SLOs and Error Budgets

### SLO Definition

```yaml
# slo.yaml
slos:
  - name: order-service-availability
    description: "Order service should be available 99.9% of the time"
    objective: 99.9
    indicator:
      type: availability
      query: |
        sum(rate(http_requests_total{service="order-service", status!~"5.."}[5m]))
        /
        sum(rate(http_requests_total{service="order-service"}[5m]))

  - name: order-service-latency
    description: "99% of requests should complete within 500ms"
    objective: 99.0
    indicator:
      type: latency
      threshold: 0.5  # seconds
      query: |
        histogram_quantile(0.99,
          sum(rate(http_request_duration_seconds_bucket{service="order-service"}[5m])) by (le)
        )
```

### Error Budget Calculation

```python
from dataclasses import dataclass
from datetime import timedelta

@dataclass
class SLO:
    name: str
    objective: float  # e.g., 99.9
    window: timedelta = timedelta(days=30)

    @property
    def error_budget_percent(self) -> float:
        """Percentage of requests that can fail."""
        return 100 - self.objective

    def error_budget_minutes(self, total_minutes: int) -> float:
        """Minutes of allowed downtime."""
        return total_minutes * (self.error_budget_percent / 100)

# Example
slo = SLO(name="availability", objective=99.9)
# 30-day window = 43,200 minutes
# Error budget = 43,200 * 0.001 = 43.2 minutes of downtime allowed
```

### SLO Dashboard Metrics

```promql
# Current SLI (Service Level Indicator)
sum(rate(http_requests_total{status!~"5.."}[30d]))
/
sum(rate(http_requests_total[30d]))

# Error budget remaining
1 - (
  (1 - (sum(rate(http_requests_total{status!~"5.."}[30d])) / sum(rate(http_requests_total[30d]))))
  /
  (1 - 0.999)  # SLO objective
)

# Error budget burn rate
(
  1 - (sum(rate(http_requests_total{status!~"5.."}[1h])) / sum(rate(http_requests_total[1h])))
)
/
(1 - 0.999)
```

---

## Observability Stack Configuration

### Docker Compose Example

```yaml
version: '3.8'
services:
  # Tracing
  tempo:
    image: grafana/tempo:latest
    ports:
      - "4317:4317"  # OTLP gRPC
      - "3200:3200"  # Tempo API
    volumes:
      - ./tempo-config.yaml:/etc/tempo/config.yaml
    command: ["-config.file=/etc/tempo/config.yaml"]

  # Metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alerts:/etc/prometheus/rules

  # Logs
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/config.yaml

  # Visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
    volumes:
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning
```

---

## Implementation Checklist

- [ ] **Tracing**: OpenTelemetry configured with auto-instrumentation
- [ ] **Context Propagation**: Trace context passed between services
- [ ] **Metrics**: RED/USE metrics exposed on `/metrics`
- [ ] **Custom Metrics**: Business metrics instrumented
- [ ] **Prometheus**: Scraping configured, alerting rules defined
- [ ] **Grafana**: Dashboards created for each service
- [ ] **Structured Logging**: JSON logs with trace correlation
- [ ] **Log Aggregation**: Centralized logging (Loki/ELK)
- [ ] **SLOs**: Defined with error budgets
- [ ] **Alerting**: Multi-level alerts (warning/critical)
