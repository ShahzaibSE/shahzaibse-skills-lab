# Service Specification: {SERVICE_NAME}

## Overview

| Attribute | Value |
|-----------|-------|
| **Service Name** | {service-name} |
| **Owner Team** | {team-name} |
| **Repository** | {repo-url} |
| **Slack Channel** | #{channel-name} |
| **On-Call** | {oncall-rotation} |

### Description

{Brief description of what this service does and its business purpose}

### Business Capability

{The business capability this service supports (e.g., "Order Management", "Payment Processing")}

### Bounded Context

{DDD bounded context this service belongs to}

---

## API Specification

### Base URL

- Production: `https://api.example.com/{service-name}`
- Staging: `https://api.staging.example.com/{service-name}`

### Authentication

{Authentication method: JWT, API Key, mTLS}

### Endpoints

#### `POST /api/v1/{resources}`

**Description**: {What this endpoint does}

**Request**:
```json
{
  "field1": "string",
  "field2": 123,
  "nested": {
    "field3": true
  }
}
```

**Response** (201 Created):
```json
{
  "id": "res_123",
  "field1": "string",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors**:
| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_REQUEST | Request validation failed |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 409 | CONFLICT | Resource already exists |

#### `GET /api/v1/{resources}/{id}`

**Description**: {What this endpoint does}

**Response** (200 OK):
```json
{
  "id": "res_123",
  "field1": "string",
  "status": "active"
}
```

---

## Events

### Published Events

#### `{service}.{resource}.created`

**Topic**: `{service}-events`

**Schema**:
```json
{
  "event_id": "evt_123",
  "event_type": "{service}.{resource}.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "id": "res_123",
    "field1": "value"
  }
}
```

**Consumers**: {List of services that consume this event}

#### `{service}.{resource}.updated`

**Topic**: `{service}-events`

**Schema**:
```json
{
  "event_id": "evt_124",
  "event_type": "{service}.{resource}.updated",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "id": "res_123",
    "changes": {
      "field1": {"old": "value1", "new": "value2"}
    }
  }
}
```

### Consumed Events

| Event | Source | Handler |
|-------|--------|---------|
| `payment.completed` | payment-service | `handle_payment_completed` |
| `inventory.reserved` | inventory-service | `handle_inventory_reserved` |

---

## Data Ownership

### Owned Entities

| Entity | Description | Storage |
|--------|-------------|---------|
| {Entity1} | {Description} | PostgreSQL |
| {Entity2} | {Description} | PostgreSQL |
| {Cache1} | {Description} | Redis |

### Data Schema

```sql
-- Primary entity
CREATE TABLE {resources} (
    id VARCHAR(50) PRIMARY KEY,
    field1 VARCHAR(255) NOT NULL,
    field2 INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_{resources}_status ON {resources}(status);
CREATE INDEX idx_{resources}_created_at ON {resources}(created_at);
```

### Data Retention

| Data Type | Retention Period | Archival Strategy |
|-----------|------------------|-------------------|
| Active records | Indefinite | N/A |
| Completed records | 2 years | Archive to S3 |
| Audit logs | 7 years | Compliance storage |

---

## Dependencies

### Upstream Dependencies (This service depends on)

| Service | Type | Purpose | Criticality |
|---------|------|---------|-------------|
| user-service | Sync (REST) | User validation | Critical |
| inventory-service | Async (Event) | Stock updates | High |
| notification-service | Async (Event) | Send notifications | Low |

### Downstream Dependencies (Services depending on this)

| Service | Type | Purpose |
|---------|------|---------|
| analytics-service | Async (Event) | Reporting |
| billing-service | Sync (REST) | Invoice generation |

---

## Resilience

### Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Database unavailable | Service down | Circuit breaker, retry |
| user-service unavailable | Cannot validate users | Cache recent users, fail open for existing |
| Kafka unavailable | Events not published | Outbox pattern, retry queue |

### Circuit Breakers

| Dependency | Threshold | Timeout | Recovery |
|------------|-----------|---------|----------|
| user-service | 5 failures | 30s | 3 successes |
| payment-service | 3 failures | 60s | 5 successes |

### Fallback Strategies

| Operation | Primary | Fallback |
|-----------|---------|----------|
| Get user details | user-service API | Local cache |
| Get product price | pricing-service | Cached price |

---

## SLOs

### Availability

- **Target**: 99.9%
- **Measurement**: Successful requests / Total requests
- **Window**: 30 days rolling

### Latency

| Endpoint | P50 | P95 | P99 |
|----------|-----|-----|-----|
| POST /resources | 100ms | 300ms | 500ms |
| GET /resources/{id} | 20ms | 50ms | 100ms |
| GET /resources (list) | 50ms | 150ms | 300ms |

### Error Rate

- **Target**: < 0.1%
- **Measurement**: 5xx responses / Total responses

---

## Security

### Authentication

{How requests are authenticated}

### Authorization

| Role | Permissions |
|------|-------------|
| admin | Full CRUD |
| user | Read own, Create |
| service | Read all |

### Sensitive Data

| Field | Classification | Protection |
|-------|----------------|------------|
| email | PII | Encrypted at rest |
| payment_token | Sensitive | Tokenized, never stored |

---

## Infrastructure

### Resources

| Environment | CPU | Memory | Replicas |
|-------------|-----|--------|----------|
| Production | 500m-2000m | 512Mi-2Gi | 3-10 |
| Staging | 250m-500m | 256Mi-512Mi | 2 |

### Scaling

- **Metric**: CPU utilization
- **Target**: 70%
- **Min replicas**: 3
- **Max replicas**: 10

### Health Checks

- **Liveness**: `GET /health/live` (10s interval)
- **Readiness**: `GET /health/ready` (5s interval)

---

## Runbook

### Deployment

```bash
# Deploy to staging
kubectl apply -k k8s/overlays/staging

# Deploy to production
kubectl apply -k k8s/overlays/production
```

### Common Issues

#### High Latency

1. Check database connection pool
2. Review slow query logs
3. Check downstream service health
4. Scale horizontally if needed

#### High Error Rate

1. Check application logs for exceptions
2. Verify database connectivity
3. Check circuit breaker states
4. Review recent deployments

### Contacts

- **Team Lead**: {name} ({email})
- **On-Call**: {pagerduty-link}
- **Escalation**: {escalation-policy}
