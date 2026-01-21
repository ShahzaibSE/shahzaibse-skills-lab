# Communication Patterns

Synchronous, asynchronous, and hybrid communication patterns for microservices.

---

## Synchronous Communication

### REST

**When to Use**:
- Public APIs
- Simple CRUD operations
- Request-response semantics
- Broad client compatibility

**Best Practices**:
```
GET    /orders/{id}          - Retrieve
POST   /orders               - Create
PUT    /orders/{id}          - Full update
PATCH  /orders/{id}          - Partial update
DELETE /orders/{id}          - Delete
```

**Python FastAPI Example**:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID

app = FastAPI()

class OrderCreate(BaseModel):
    customer_id: UUID
    items: list[dict]

class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: str
    total: float

@app.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(order: OrderCreate):
    # Create order logic
    return OrderResponse(
        id=UUID("..."),
        customer_id=order.customer_id,
        status="created",
        total=calculate_total(order.items)
    )

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID):
    order = await order_repository.find(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
```

### gRPC

**When to Use**:
- Service-to-service communication
- High performance requirements
- Strong typing needed
- Bi-directional streaming

**Proto Definition**:
```protobuf
syntax = "proto3";

package orders;

service OrderService {
    rpc CreateOrder(CreateOrderRequest) returns (Order);
    rpc GetOrder(GetOrderRequest) returns (Order);
    rpc StreamOrderUpdates(GetOrderRequest) returns (stream OrderUpdate);
}

message CreateOrderRequest {
    string customer_id = 1;
    repeated OrderItem items = 2;
}

message Order {
    string id = 1;
    string customer_id = 2;
    string status = 3;
    double total = 4;
}

message OrderItem {
    string product_id = 1;
    int32 quantity = 2;
    double price = 3;
}

message GetOrderRequest {
    string order_id = 1;
}

message OrderUpdate {
    string order_id = 1;
    string status = 2;
    string timestamp = 3;
}
```

**Go Server Example**:
```go
package main

import (
    "context"
    pb "example/orders"
    "google.golang.org/grpc"
)

type orderServer struct {
    pb.UnimplementedOrderServiceServer
    repo OrderRepository
}

func (s *orderServer) CreateOrder(ctx context.Context, req *pb.CreateOrderRequest) (*pb.Order, error) {
    order := &Order{
        CustomerID: req.CustomerId,
        Items:      convertItems(req.Items),
    }

    if err := s.repo.Save(ctx, order); err != nil {
        return nil, err
    }

    return &pb.Order{
        Id:         order.ID,
        CustomerId: order.CustomerID,
        Status:     "created",
        Total:      order.Total(),
    }, nil
}

func (s *orderServer) StreamOrderUpdates(req *pb.GetOrderRequest, stream pb.OrderService_StreamOrderUpdatesServer) error {
    updates := s.repo.SubscribeToUpdates(req.OrderId)
    for update := range updates {
        if err := stream.Send(&pb.OrderUpdate{
            OrderId:   update.OrderID,
            Status:    update.Status,
            Timestamp: update.Timestamp.String(),
        }); err != nil {
            return err
        }
    }
    return nil
}
```

### GraphQL

**When to Use**:
- Frontend flexibility needed
- Multiple clients with different data needs
- Aggregating multiple services
- Reducing over-fetching

**Schema Example**:
```graphql
type Query {
    order(id: ID!): Order
    orders(customerId: ID!, status: OrderStatus): [Order!]!
}

type Mutation {
    createOrder(input: CreateOrderInput!): Order!
    updateOrderStatus(id: ID!, status: OrderStatus!): Order!
}

type Order {
    id: ID!
    customer: Customer!
    items: [OrderItem!]!
    status: OrderStatus!
    total: Float!
    createdAt: DateTime!
}

type OrderItem {
    product: Product!
    quantity: Int!
    price: Float!
}

enum OrderStatus {
    PENDING
    CONFIRMED
    SHIPPED
    DELIVERED
}

input CreateOrderInput {
    customerId: ID!
    items: [OrderItemInput!]!
}
```

---

## Asynchronous Communication

### Event-Driven Architecture

**Core Concepts**:
- **Event**: Something that happened (past tense)
- **Producer**: Publishes events
- **Consumer**: Subscribes to events
- **Broker**: Routes events

**Event Types**:

| Type | Description | Example |
|------|-------------|---------|
| **Domain Event** | Business occurrence | OrderPlaced |
| **Integration Event** | Cross-service communication | OrderCreatedEvent |
| **Notification** | Fire-and-forget | EmailRequested |
| **Command** | Request action | ProcessPayment |

### Message Patterns

**Point-to-Point (Queue)**:
```
Producer → [Queue] → Single Consumer
```
- Exactly one consumer processes message
- Load balancing across consumers
- Use for: Commands, work distribution

**Publish-Subscribe (Topic)**:
```
Producer → [Topic] → Multiple Consumers
                 └→ Consumer A
                 └→ Consumer B
                 └→ Consumer C
```
- All subscribers receive message
- Use for: Events, notifications

### Kafka Example

**Python Producer**:
```python
from kafka import KafkaProducer
import json
from dataclasses import asdict

class OrderEventPublisher:
    def __init__(self, bootstrap_servers: list[str]):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )

    async def publish_order_created(self, event: OrderCreated):
        self.producer.send(
            topic='orders.created',
            key=str(event.order_id),
            value={
                'event_type': 'OrderCreated',
                'order_id': str(event.order_id),
                'customer_id': str(event.customer_id),
                'total': event.total,
                'timestamp': event.timestamp.isoformat()
            }
        )
        self.producer.flush()
```

**Python Consumer**:
```python
from kafka import KafkaConsumer
import json

class OrderEventConsumer:
    def __init__(self, bootstrap_servers: list[str], group_id: str):
        self.consumer = KafkaConsumer(
            'orders.created',
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=False
        )

    def process_events(self):
        for message in self.consumer:
            try:
                event = message.value
                self._handle_event(event)
                self.consumer.commit()
            except Exception as e:
                # Handle error, possibly send to DLQ
                self._send_to_dlq(message, e)

    def _handle_event(self, event: dict):
        if event['event_type'] == 'OrderCreated':
            # Process order created event
            print(f"Processing order: {event['order_id']}")
```

### RabbitMQ Example

**Go Publisher**:
```go
package messaging

import (
    "encoding/json"
    amqp "github.com/rabbitmq/amqp091-go"
)

type EventPublisher struct {
    conn    *amqp.Connection
    channel *amqp.Channel
}

func NewEventPublisher(url string) (*EventPublisher, error) {
    conn, err := amqp.Dial(url)
    if err != nil {
        return nil, err
    }

    ch, err := conn.Channel()
    if err != nil {
        return nil, err
    }

    // Declare exchange
    err = ch.ExchangeDeclare(
        "orders",   // name
        "topic",    // type
        true,       // durable
        false,      // auto-deleted
        false,      // internal
        false,      // no-wait
        nil,        // arguments
    )

    return &EventPublisher{conn: conn, channel: ch}, err
}

func (p *EventPublisher) PublishOrderCreated(event OrderCreatedEvent) error {
    body, err := json.Marshal(event)
    if err != nil {
        return err
    }

    return p.channel.Publish(
        "orders",         // exchange
        "order.created",  // routing key
        false,            // mandatory
        false,            // immediate
        amqp.Publishing{
            ContentType:  "application/json",
            DeliveryMode: amqp.Persistent,
            Body:         body,
        },
    )
}
```

---

## CQRS Pattern

### Overview

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
      ┌───────▼───────┐        ┌────────▼────────┐
      │   Commands    │        │     Queries     │
      └───────┬───────┘        └────────┬────────┘
              │                         │
      ┌───────▼───────┐        ┌────────▼────────┐
      │ Write Model   │        │   Read Model    │
      │ (Aggregate)   │        │  (Projection)   │
      └───────┬───────┘        └────────┬────────┘
              │                         │
      ┌───────▼───────┐        ┌────────▼────────┐
      │  Write DB     │───────>│   Read DB       │
      │ (PostgreSQL)  │ events │ (Elasticsearch) │
      └───────────────┘        └─────────────────┘
```

### Python Implementation

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

# Commands
@dataclass
class CreateOrder:
    customer_id: UUID
    items: list[dict]

@dataclass
class ConfirmOrder:
    order_id: UUID

# Command Handler
class OrderCommandHandler:
    def __init__(self, repo: OrderRepository, publisher: EventPublisher):
        self.repo = repo
        self.publisher = publisher

    async def handle_create(self, cmd: CreateOrder) -> UUID:
        order = Order.create(cmd.customer_id, cmd.items)
        await self.repo.save(order)
        await self.publisher.publish(order.get_events())
        return order.id

    async def handle_confirm(self, cmd: ConfirmOrder):
        order = await self.repo.find(cmd.order_id)
        order.confirm()
        await self.repo.save(order)
        await self.publisher.publish(order.get_events())

# Queries
@dataclass
class GetOrderById:
    order_id: UUID

@dataclass
class GetOrdersByCustomer:
    customer_id: UUID
    status: str | None = None

# Query Handler (uses read model)
class OrderQueryHandler:
    def __init__(self, read_repo: OrderReadRepository):
        self.read_repo = read_repo

    async def get_order(self, query: GetOrderById) -> OrderView | None:
        return await self.read_repo.find_by_id(query.order_id)

    async def get_customer_orders(self, query: GetOrdersByCustomer) -> list[OrderView]:
        return await self.read_repo.find_by_customer(
            query.customer_id,
            query.status
        )

# Read Model / Projection
@dataclass
class OrderView:
    id: UUID
    customer_id: UUID
    customer_name: str  # Denormalized
    items: list[dict]
    status: str
    total: float
    created_at: str

# Projection Handler (builds read model from events)
class OrderProjectionHandler:
    def __init__(self, read_repo: OrderReadRepository, customer_client: CustomerClient):
        self.read_repo = read_repo
        self.customer_client = customer_client

    async def handle_order_created(self, event: OrderCreated):
        customer = await self.customer_client.get(event.customer_id)
        view = OrderView(
            id=event.order_id,
            customer_id=event.customer_id,
            customer_name=customer.name,
            items=event.items,
            status="created",
            total=event.total,
            created_at=event.timestamp.isoformat()
        )
        await self.read_repo.save(view)

    async def handle_order_confirmed(self, event: OrderConfirmed):
        await self.read_repo.update_status(event.order_id, "confirmed")
```

---

## Saga Pattern

### Choreography

Services coordinate through events without central orchestrator.

```
┌─────────┐  OrderCreated  ┌───────────┐  InventoryReserved  ┌─────────┐
│  Order  │ ─────────────> │ Inventory │ ──────────────────> │ Payment │
│ Service │                │  Service  │                     │ Service │
└─────────┘                └───────────┘                     └─────────┘
     ▲                           │                                │
     │                           │ ReservationFailed              │
     │                           ▼                                │
     │                    [Compensate]                            │
     │                                                            │
     └─────────────────── PaymentProcessed ───────────────────────┘
```

**Python Choreography Example**:
```python
# Order Service - starts the saga
class OrderService:
    async def create_order(self, cmd: CreateOrder):
        order = Order.create(cmd.customer_id, cmd.items)
        order.status = "pending"
        await self.repo.save(order)
        await self.publisher.publish(OrderCreated(
            order_id=order.id,
            items=order.items,
            customer_id=order.customer_id
        ))

# Inventory Service - responds to OrderCreated
class InventoryEventHandler:
    async def handle_order_created(self, event: OrderCreated):
        try:
            await self.inventory_service.reserve(event.order_id, event.items)
            await self.publisher.publish(InventoryReserved(
                order_id=event.order_id
            ))
        except InsufficientStock:
            await self.publisher.publish(InventoryReservationFailed(
                order_id=event.order_id,
                reason="insufficient_stock"
            ))

# Payment Service - responds to InventoryReserved
class PaymentEventHandler:
    async def handle_inventory_reserved(self, event: InventoryReserved):
        try:
            await self.payment_service.process(event.order_id)
            await self.publisher.publish(PaymentProcessed(
                order_id=event.order_id
            ))
        except PaymentFailed as e:
            await self.publisher.publish(PaymentFailed(
                order_id=event.order_id,
                reason=str(e)
            ))

# Order Service - handles compensation
class OrderEventHandler:
    async def handle_inventory_failed(self, event: InventoryReservationFailed):
        await self.order_service.cancel(event.order_id, event.reason)

    async def handle_payment_failed(self, event: PaymentFailed):
        # Trigger compensation
        await self.publisher.publish(ReleaseInventory(
            order_id=event.order_id
        ))
        await self.order_service.cancel(event.order_id, event.reason)
```

### Orchestration

Central orchestrator coordinates the saga steps.

```
                    ┌────────────────────┐
                    │  Saga Orchestrator │
                    └─────────┬──────────┘
           ┌──────────────────┼──────────────────┐
           │                  │                  │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │   Order     │    │  Inventory  │    │   Payment   │
    │   Service   │    │   Service   │    │   Service   │
    └─────────────┘    └─────────────┘    └─────────────┘
```

**Go Orchestration Example**:
```go
package saga

import (
    "context"
    "fmt"
)

type OrderSagaState string

const (
    StateCreated           OrderSagaState = "created"
    StateInventoryReserved OrderSagaState = "inventory_reserved"
    StatePaymentProcessed  OrderSagaState = "payment_processed"
    StateCompleted         OrderSagaState = "completed"
    StateFailed            OrderSagaState = "failed"
)

type OrderSaga struct {
    OrderID    string
    State      OrderSagaState
    FailReason string
}

type OrderSagaOrchestrator struct {
    orderClient     OrderServiceClient
    inventoryClient InventoryServiceClient
    paymentClient   PaymentServiceClient
    sagaRepo        SagaRepository
}

func (o *OrderSagaOrchestrator) Execute(ctx context.Context, cmd CreateOrderCommand) error {
    saga := &OrderSaga{
        OrderID: cmd.OrderID,
        State:   StateCreated,
    }

    // Step 1: Create Order
    if err := o.orderClient.Create(ctx, cmd); err != nil {
        return o.compensate(ctx, saga, err)
    }

    // Step 2: Reserve Inventory
    saga.State = StateInventoryReserved
    if err := o.sagaRepo.Save(ctx, saga); err != nil {
        return err
    }

    if err := o.inventoryClient.Reserve(ctx, cmd.OrderID, cmd.Items); err != nil {
        return o.compensate(ctx, saga, err)
    }

    // Step 3: Process Payment
    saga.State = StatePaymentProcessed
    if err := o.sagaRepo.Save(ctx, saga); err != nil {
        return err
    }

    if err := o.paymentClient.Process(ctx, cmd.OrderID, cmd.Amount); err != nil {
        return o.compensate(ctx, saga, err)
    }

    // Complete
    saga.State = StateCompleted
    return o.sagaRepo.Save(ctx, saga)
}

func (o *OrderSagaOrchestrator) compensate(ctx context.Context, saga *OrderSaga, err error) error {
    saga.State = StateFailed
    saga.FailReason = err.Error()

    // Compensate in reverse order
    switch saga.State {
    case StatePaymentProcessed:
        _ = o.paymentClient.Refund(ctx, saga.OrderID)
        fallthrough
    case StateInventoryReserved:
        _ = o.inventoryClient.Release(ctx, saga.OrderID)
        fallthrough
    case StateCreated:
        _ = o.orderClient.Cancel(ctx, saga.OrderID)
    }

    return o.sagaRepo.Save(ctx, saga)
}
```

---

## API Composition

### Backend for Frontend (BFF)

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│  Mobile    │     │    Web     │     │  Partner   │
│   App      │     │   App      │     │   API      │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      │                  │                  │
┌─────▼──────┐     ┌─────▼──────┐     ┌─────▼──────┐
│ Mobile BFF │     │  Web BFF   │     │Partner BFF │
└─────┬──────┘     └─────┬──────┘     └─────┬──────┘
      │                  │                  │
      └──────────────────┼──────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
    │ Orders  │     │ Users   │     │Products │
    └─────────┘     └─────────┘     └─────────┘
```

### API Gateway Aggregation

```python
from fastapi import FastAPI
import httpx

app = FastAPI()

class OrderAggregator:
    def __init__(self):
        self.order_client = httpx.AsyncClient(base_url="http://orders:8000")
        self.user_client = httpx.AsyncClient(base_url="http://users:8000")
        self.product_client = httpx.AsyncClient(base_url="http://products:8000")

    async def get_order_details(self, order_id: str) -> dict:
        # Parallel calls
        order_resp, = await asyncio.gather(
            self.order_client.get(f"/orders/{order_id}")
        )
        order = order_resp.json()

        # Get related data in parallel
        user_resp, products_resp = await asyncio.gather(
            self.user_client.get(f"/users/{order['customer_id']}"),
            self.product_client.post("/products/batch", json={
                "ids": [item["product_id"] for item in order["items"]]
            })
        )

        # Compose response
        return {
            "order": order,
            "customer": user_resp.json(),
            "products": {p["id"]: p for p in products_resp.json()}
        }
```

---

## Communication Anti-Patterns

### Synchronous Chain

**Bad**:
```
Client → A → B → C → D → E
         ↓   ↓   ↓   ↓   ↓
        50ms 50ms 50ms 50ms = 200ms + 5x failure points
```

**Better**:
```
Client → A → [Event Bus] → B, C, D, E (parallel)
         ↓
        50ms (async processing)
```

### Chatty Communication

**Bad**:
```python
# 100 API calls
for item in items:
    product = await product_client.get(item.product_id)
```

**Better**:
```python
# 1 batch call
products = await product_client.get_batch([i.product_id for i in items])
```

### Missing Correlation

**Bad**: No way to trace requests across services

**Good**: Propagate correlation ID
```python
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    # Set in context for logging and outgoing calls
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```
