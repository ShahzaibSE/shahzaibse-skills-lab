# Service Decomposition Strategies

Patterns and techniques for breaking down systems into microservices.

---

## Domain-Driven Design Foundation

### Bounded Contexts

A bounded context is a boundary within which a domain model is defined and applicable.

**Key Principles**:
- Each bounded context has its own ubiquitous language
- Models mean different things in different contexts
- Explicit boundaries prevent model pollution

**Example**: "Customer" means different things:
- **Sales Context**: Prospect, lead score, contact info
- **Billing Context**: Payment methods, invoices, credit
- **Support Context**: Tickets, satisfaction score, history

### Context Mapping

| Relationship | Description | When to Use |
|--------------|-------------|-------------|
| **Partnership** | Teams cooperate on integration | Two teams with aligned goals |
| **Shared Kernel** | Shared subset of domain model | Common core concepts |
| **Customer-Supplier** | Downstream depends on upstream | Clear dependency direction |
| **Conformist** | Downstream conforms to upstream | No influence over upstream |
| **Anti-Corruption Layer** | Translation layer | Protect from external model |
| **Open Host Service** | Published protocol | Multiple consumers |
| **Published Language** | Shared interchange format | Cross-context communication |

### Context Mapping Diagram

```
┌─────────────────┐         ┌─────────────────┐
│   Sales         │  OHS    │   Billing       │
│   Context       │ ──────> │   Context       │
│                 │   PL    │                 │
└─────────────────┘         └─────────────────┘
        │                           │
        │ ACL                       │ CS
        ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│   Legacy CRM    │         │   Support       │
│   (External)    │         │   Context       │
└─────────────────┘         └─────────────────┘
```

---

## Decomposition by Business Capability

### Approach

Identify business capabilities → Map to services

**Business Capability**: What the business does (not how)

### Example: E-Commerce

```
E-Commerce Platform
├── Product Catalog Management
│   └── product-service
├── Inventory Management
│   └── inventory-service
├── Order Management
│   ├── order-service
│   └── fulfillment-service
├── Customer Management
│   └── customer-service
├── Payment Processing
│   └── payment-service
└── Shipping & Delivery
    └── shipping-service
```

### Identification Process

1. **Start with business functions**: What does the business do?
2. **Map to organizational structure**: Who owns what?
3. **Identify dependencies**: How do capabilities interact?
4. **Define boundaries**: Where does one capability end?

---

## Decomposition by Subdomain

### Subdomain Types

| Type | Description | Investment | Example |
|------|-------------|------------|---------|
| **Core** | Competitive advantage | High | Recommendation engine |
| **Supporting** | Necessary but not differentiating | Medium | User management |
| **Generic** | Commodity, buy/outsource | Low | Email sending |

### Example: Streaming Platform

```
Streaming Platform
├── Core Subdomains
│   ├── content-recommendation    (ML-driven)
│   ├── content-personalization   (user experience)
│   └── content-delivery          (streaming tech)
├── Supporting Subdomains
│   ├── user-management
│   ├── subscription-management
│   └── content-catalog
└── Generic Subdomains
    ├── payment-processing        (use Stripe)
    ├── email-notifications       (use SendGrid)
    └── analytics                 (use Mixpanel)
```

---

## Strangler Fig Pattern

### Approach

Gradually replace monolith functionality with microservices.

```
Phase 1: Facade
┌─────────────────────────────────────┐
│            Facade/Gateway           │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
┌───────▼───────┐   ┌───────▼───────┐
│   Monolith    │   │   New Service │
│   (all)       │   │   (orders)    │
└───────────────┘   └───────────────┘

Phase 2: Extract More
┌─────────────────────────────────────┐
│            Facade/Gateway           │
└─────────────────┬───────────────────┘
        ┌─────────┼─────────┐
        │         │         │
┌───────▼───┐ ┌───▼───┐ ┌───▼───────┐
│ Monolith  │ │Orders │ │ Inventory │
│ (reduced) │ │Service│ │ Service   │
└───────────┘ └───────┘ └───────────┘

Phase 3: Complete
┌─────────────────────────────────────┐
│            API Gateway              │
└─────────────────┬───────────────────┘
    ┌─────────────┼─────────────┐
    │      │      │      │      │
┌───▼─┐ ┌──▼──┐ ┌─▼──┐ ┌─▼──┐ ┌▼───┐
│Users│ │Order│ │Inv │ │Pay │ │Ship│
└─────┘ └─────┘ └────┘ └────┘ └────┘
```

### Implementation Steps

1. **Identify extraction candidate**
   - High change frequency
   - Clear boundaries
   - Independent data

2. **Create facade**
   - Route requests
   - Start with 100% to monolith

3. **Build new service**
   - Implement functionality
   - Create data migration plan

4. **Gradual cutover**
   - Route increasing traffic to new service
   - Monitor for issues
   - Rollback capability

5. **Complete migration**
   - Remove old code from monolith
   - Decommission route to old code

### Extraction Prioritization

| Factor | High Priority | Low Priority |
|--------|--------------|--------------|
| Change frequency | Changes weekly | Changes yearly |
| Team ownership | Clear owner | Shared ownership |
| Data coupling | Independent data | Highly coupled |
| Deployment needs | Needs independent deploy | Deploys with others |
| Scale requirements | Needs independent scale | Scales uniformly |

---

## Service Sizing Guidelines

### Team Size (Conway's Law)

**Two-Pizza Rule**: Service should be owned by team of 5-9 people

```
Too Large: >15 people working on service
Right Size: 5-9 people (2-pizza team)
Too Small: <3 people (consider merging)
```

### Codebase Size

| Size | Lines of Code | Typical Characteristics |
|------|---------------|------------------------|
| Micro | <5K | Single responsibility, few endpoints |
| Small | 5K-20K | Bounded context, moderate complexity |
| Medium | 20K-50K | Multiple aggregates, complex domain |
| Large | >50K | Consider splitting |

### Deploy Frequency

Services that need to deploy together should probably be one service.

```
Coupled Deploys → Consider Merging
├── Always deploy A with B
├── Integration tests require both
└── Shared release schedule

Independent Deploys → Good Boundaries
├── Can deploy A without B
├── Own integration tests
└── Own release schedule
```

---

## Identifying Service Boundaries

### Analysis Techniques

**1. Event Storming**

```
1. Identify domain events (past tense)
   "OrderPlaced", "PaymentReceived", "ItemShipped"

2. Group related events
   Order events, Payment events, Shipping events

3. Identify aggregates
   Order, Payment, Shipment

4. Draw boundaries
   Order Service, Payment Service, Shipping Service
```

**2. Data Ownership Analysis**

```
For each data entity:
1. Who creates it?
2. Who updates it?
3. Who reads it?
4. What are the consistency requirements?

→ Entity belongs to service that creates/owns lifecycle
```

**3. Use Case Analysis**

```
For each use case:
1. What data does it need?
2. What services does it call?
3. What are the transactional requirements?

→ If use case spans many services, consider service boundaries
```

### Boundary Validation Questions

- Does this service have a single reason to change?
- Can this service be deployed independently?
- Does this service have clear data ownership?
- Is the service owned by one team?
- Are the service's APIs stable?

---

## Code Examples

### Python: Domain Events

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

# Domain Event Base
@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID
    occurred_at: datetime
    aggregate_id: UUID

# Order Domain Events
@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    customer_id: UUID
    items: list[dict]
    total_amount: float

@dataclass(frozen=True)
class OrderConfirmed(DomainEvent):
    confirmed_at: datetime

@dataclass(frozen=True)
class OrderShipped(DomainEvent):
    tracking_number: str
    carrier: str

# Event Publisher Protocol
class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...

# Aggregate Root
class Order:
    def __init__(self, order_id: UUID, customer_id: UUID):
        self.id = order_id
        self.customer_id = customer_id
        self.items: list[dict] = []
        self.status = "draft"
        self._events: list[DomainEvent] = []

    def add_item(self, product_id: UUID, quantity: int, price: float):
        self.items.append({
            "product_id": str(product_id),
            "quantity": quantity,
            "price": price
        })

    def place(self) -> OrderCreated:
        self.status = "placed"
        event = OrderCreated(
            event_id=UUID(),
            occurred_at=datetime.utcnow(),
            aggregate_id=self.id,
            customer_id=self.customer_id,
            items=self.items,
            total_amount=sum(i["price"] * i["quantity"] for i in self.items)
        )
        self._events.append(event)
        return event

    def get_uncommitted_events(self) -> list[DomainEvent]:
        return self._events.copy()

    def clear_events(self):
        self._events.clear()
```

### Go: Bounded Context

```go
package order

import (
    "context"
    "time"

    "github.com/google/uuid"
)

// Order Aggregate - Order Bounded Context
type Order struct {
    ID         uuid.UUID
    CustomerID uuid.UUID
    Items      []OrderItem
    Status     OrderStatus
    CreatedAt  time.Time
    events     []DomainEvent
}

type OrderItem struct {
    ProductID uuid.UUID
    Quantity  int
    Price     float64
}

type OrderStatus string

const (
    StatusDraft     OrderStatus = "draft"
    StatusPlaced    OrderStatus = "placed"
    StatusConfirmed OrderStatus = "confirmed"
    StatusShipped   OrderStatus = "shipped"
)

// Domain Events
type DomainEvent interface {
    EventType() string
    OccurredAt() time.Time
}

type OrderPlaced struct {
    OrderID     uuid.UUID
    CustomerID  uuid.UUID
    TotalAmount float64
    occurredAt  time.Time
}

func (e OrderPlaced) EventType() string    { return "order.placed" }
func (e OrderPlaced) OccurredAt() time.Time { return e.occurredAt }

// Repository Interface (Port)
type OrderRepository interface {
    Save(ctx context.Context, order *Order) error
    FindByID(ctx context.Context, id uuid.UUID) (*Order, error)
}

// Application Service
type OrderService struct {
    repo      OrderRepository
    publisher EventPublisher
}

type EventPublisher interface {
    Publish(ctx context.Context, event DomainEvent) error
}

func NewOrderService(repo OrderRepository, pub EventPublisher) *OrderService {
    return &OrderService{repo: repo, publisher: pub}
}

func (s *OrderService) PlaceOrder(ctx context.Context, order *Order) error {
    order.Status = StatusPlaced
    event := OrderPlaced{
        OrderID:     order.ID,
        CustomerID:  order.CustomerID,
        TotalAmount: order.TotalAmount(),
        occurredAt:  time.Now(),
    }

    if err := s.repo.Save(ctx, order); err != nil {
        return err
    }

    return s.publisher.Publish(ctx, event)
}

func (o *Order) TotalAmount() float64 {
    var total float64
    for _, item := range o.Items {
        total += item.Price * float64(item.Quantity)
    }
    return total
}
```

### Anti-Corruption Layer

```python
# External legacy system client
class LegacyCRMClient:
    def get_customer_data(self, crm_id: str) -> dict:
        # Returns legacy format
        return {
            "CustID": crm_id,
            "CustName": "John Doe",
            "CustEmail": "john@example.com",
            "AcctBalance": 1500.00,
            "CustType": "PREMIUM"
        }

# Our domain model
@dataclass
class Customer:
    id: str
    name: str
    email: str
    tier: str  # 'standard', 'premium', 'enterprise'

# Anti-Corruption Layer
class CustomerACL:
    def __init__(self, legacy_client: LegacyCRMClient):
        self._legacy = legacy_client

    def get_customer(self, customer_id: str) -> Customer:
        legacy_data = self._legacy.get_customer_data(customer_id)
        return self._translate(legacy_data)

    def _translate(self, legacy: dict) -> Customer:
        return Customer(
            id=legacy["CustID"],
            name=legacy["CustName"],
            email=legacy["CustEmail"],
            tier=self._map_tier(legacy["CustType"])
        )

    def _map_tier(self, legacy_type: str) -> str:
        mapping = {
            "BASIC": "standard",
            "PREMIUM": "premium",
            "ENTERPRISE": "enterprise",
            "VIP": "enterprise"
        }
        return mapping.get(legacy_type, "standard")
```

---

## Decomposition Anti-Patterns

### Distributed Monolith

**Symptoms**:
- Services must deploy together
- Shared database
- Synchronous calls everywhere
- Tight coupling

**Fix**: Redefine boundaries, introduce async, separate data

### Nanoservices

**Symptoms**:
- Hundreds of tiny services
- High network overhead
- Complex debugging
- Operational nightmare

**Fix**: Merge related services, follow team boundaries

### Anemic Services

**Symptoms**:
- CRUD-only operations
- No business logic
- Logic in orchestration layer

**Fix**: Push logic into services, model behavior not just data
