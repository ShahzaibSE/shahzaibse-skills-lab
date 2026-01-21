# Data Management Patterns

## Overview

Data management in microservices requires careful consideration of ownership, consistency, and communication patterns. The fundamental principle: **each service owns its data**.

---

## Database Per Service Pattern

### Core Principle

Each microservice has exclusive access to its database. No direct database sharing between services.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ User Service│     │Order Service│     │ Inventory   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
  ┌─────────┐        ┌─────────┐        ┌─────────┐
  │PostgreSQL│        │ MongoDB │        │  Redis  │
  │  Users   │        │ Orders  │        │  Stock  │
  └─────────┘        └─────────┘        └─────────┘
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Loose Coupling** | Services can evolve independently |
| **Right Tool** | Choose database matching workload |
| **Scaling** | Scale databases independently |
| **Fault Isolation** | Database failure isolated to one service |

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Cross-service queries | API composition, CQRS read models |
| Data consistency | Saga pattern, eventual consistency |
| Transactions | Saga, outbox pattern |
| Reporting | Event-driven data lake |

---

## Polyglot Persistence

### Database Selection Guide

| Database | Best For | Example Use Case |
|----------|----------|------------------|
| **PostgreSQL** | Complex queries, ACID, relations | User accounts, financial data |
| **MongoDB** | Flexible schema, documents | Product catalog, content |
| **Redis** | Caching, sessions, real-time | Shopping cart, rate limiting |
| **Elasticsearch** | Full-text search, analytics | Search, log aggregation |
| **Cassandra** | High write throughput, time-series | IoT data, event logs |
| **Neo4j** | Graph relationships | Recommendations, fraud detection |

### Implementation Example

```python
# User Service - PostgreSQL (relational, ACID)
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)

# Product Service - MongoDB (flexible schema)
from motor.motor_asyncio import AsyncIOMotorClient

class ProductRepository:
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.collection = mongo_client.catalog.products

    async def create(self, product: dict) -> str:
        # Flexible schema - products can have varying attributes
        result = await self.collection.insert_one(product)
        return str(result.inserted_id)

    async def find_by_category(self, category: str) -> list:
        cursor = self.collection.find({"category": category})
        return await cursor.to_list(length=100)

# Cart Service - Redis (fast, ephemeral)
import redis.asyncio as redis

class CartRepository:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 86400 * 7  # 7 days

    async def add_item(self, user_id: str, item: dict):
        key = f"cart:{user_id}"
        await self.redis.hset(key, item["product_id"], json.dumps(item))
        await self.redis.expire(key, self.ttl)

    async def get_cart(self, user_id: str) -> list:
        key = f"cart:{user_id}"
        items = await self.redis.hgetall(key)
        return [json.loads(v) for v in items.values()]

# Search Service - Elasticsearch (full-text search)
from elasticsearch import AsyncElasticsearch

class SearchRepository:
    def __init__(self, es_client: AsyncElasticsearch):
        self.es = es_client
        self.index = "products"

    async def search(self, query: str, filters: dict = None) -> list:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"multi_match": {
                            "query": query,
                            "fields": ["name^3", "description", "tags"]
                        }}
                    ],
                    "filter": self._build_filters(filters) if filters else []
                }
            }
        }
        result = await self.es.search(index=self.index, body=body)
        return [hit["_source"] for hit in result["hits"]["hits"]]
```

---

## Consistency Patterns

### Strong vs Eventual Consistency

| Aspect | Strong Consistency | Eventual Consistency |
|--------|-------------------|---------------------|
| **Guarantee** | All reads see latest write | Reads may see stale data temporarily |
| **Latency** | Higher (coordination required) | Lower (no coordination) |
| **Availability** | Lower during partitions | Higher |
| **Use Cases** | Financial, inventory | Social feeds, analytics |

### Eventual Consistency Implementation

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import asyncio

@dataclass
class Event:
    id: str
    type: str
    aggregate_id: str
    data: dict
    timestamp: datetime
    version: int

class EventuallyConsistentView:
    """Materialized view that eventually catches up with events."""

    def __init__(self, event_store, view_store):
        self.event_store = event_store
        self.view_store = view_store
        self.last_processed_version = 0

    async def refresh(self):
        """Process new events and update view."""
        events = await self.event_store.get_events_after(
            self.last_processed_version
        )

        for event in events:
            await self._apply_event(event)
            self.last_processed_version = event.version

    async def _apply_event(self, event: Event):
        """Apply event to materialized view."""
        if event.type == "OrderCreated":
            await self.view_store.upsert_order_summary(event.data)
        elif event.type == "OrderStatusChanged":
            await self.view_store.update_order_status(
                event.aggregate_id,
                event.data["new_status"]
            )

# Background worker to keep view updated
async def view_refresh_worker(view: EventuallyConsistentView):
    while True:
        try:
            await view.refresh()
        except Exception as e:
            logger.error(f"View refresh failed: {e}")
        await asyncio.sleep(1)  # Refresh every second
```

### Consistency Strategies by Domain

```
Financial Transactions  →  Strong (ACID, 2PC if needed)
Inventory Counts       →  Strong for purchases, eventual for display
User Profiles          →  Eventual (users tolerate brief staleness)
Search Results         →  Eventual (indexed asynchronously)
Analytics              →  Eventual (batch processing acceptable)
Notifications          →  Eventual (at-least-once delivery)
```

---

## Event Sourcing

### Core Concept

Store state changes as a sequence of events rather than current state.

```
Traditional: UPDATE accounts SET balance = 150 WHERE id = 1

Event Sourcing:
  Event 1: AccountOpened(id=1, initial_balance=100)
  Event 2: MoneyDeposited(id=1, amount=100)
  Event 3: MoneyWithdrawn(id=1, amount=50)
  Current State: balance = 100 + 100 - 50 = 150
```

### Implementation

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import json

@dataclass
class DomainEvent:
    event_id: str
    aggregate_id: str
    event_type: str
    data: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 0

class Aggregate(ABC):
    """Base class for event-sourced aggregates."""

    def __init__(self, aggregate_id: str):
        self.id = aggregate_id
        self.version = 0
        self._pending_events: List[DomainEvent] = []

    def apply_event(self, event: DomainEvent):
        """Apply event to update state."""
        handler = getattr(self, f"_apply_{event.event_type}", None)
        if handler:
            handler(event.data)
        self.version = event.version

    def _record_event(self, event_type: str, data: dict):
        """Record new event."""
        event = DomainEvent(
            event_id=str(uuid.uuid4()),
            aggregate_id=self.id,
            event_type=event_type,
            data=data,
            version=self.version + 1
        )
        self._pending_events.append(event)
        self.apply_event(event)

    def get_pending_events(self) -> List[DomainEvent]:
        return self._pending_events

    def clear_pending_events(self):
        self._pending_events = []

# Example: Order Aggregate
class Order(Aggregate):
    def __init__(self, order_id: str):
        super().__init__(order_id)
        self.status = None
        self.items = []
        self.total = 0

    # Commands
    def create(self, customer_id: str, items: list):
        if self.status is not None:
            raise ValueError("Order already exists")
        self._record_event("OrderCreated", {
            "customer_id": customer_id,
            "items": items,
            "total": sum(i["price"] * i["quantity"] for i in items)
        })

    def confirm(self):
        if self.status != "pending":
            raise ValueError("Can only confirm pending orders")
        self._record_event("OrderConfirmed", {})

    def ship(self, tracking_number: str):
        if self.status != "confirmed":
            raise ValueError("Can only ship confirmed orders")
        self._record_event("OrderShipped", {"tracking_number": tracking_number})

    # Event handlers
    def _apply_OrderCreated(self, data: dict):
        self.status = "pending"
        self.items = data["items"]
        self.total = data["total"]

    def _apply_OrderConfirmed(self, data: dict):
        self.status = "confirmed"

    def _apply_OrderShipped(self, data: dict):
        self.status = "shipped"
        self.tracking_number = data["tracking_number"]

# Event Store
class EventStore:
    async def save_events(self, aggregate_id: str, events: List[DomainEvent],
                         expected_version: int):
        """Save events with optimistic concurrency."""
        async with self.db.transaction():
            current_version = await self._get_version(aggregate_id)
            if current_version != expected_version:
                raise ConcurrencyError(
                    f"Expected version {expected_version}, got {current_version}"
                )

            for event in events:
                await self.db.execute(
                    """INSERT INTO events
                       (event_id, aggregate_id, event_type, data, version, timestamp)
                       VALUES ($1, $2, $3, $4, $5, $6)""",
                    event.event_id, event.aggregate_id, event.event_type,
                    json.dumps(event.data), event.version, event.timestamp
                )

    async def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        """Get all events for an aggregate."""
        rows = await self.db.fetch(
            "SELECT * FROM events WHERE aggregate_id = $1 ORDER BY version",
            aggregate_id
        )
        return [self._row_to_event(row) for row in rows]

# Repository
class OrderRepository:
    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    async def get(self, order_id: str) -> Order:
        """Reconstitute order from events."""
        events = await self.event_store.get_events(order_id)
        order = Order(order_id)
        for event in events:
            order.apply_event(event)
        return order

    async def save(self, order: Order):
        """Persist new events."""
        events = order.get_pending_events()
        if events:
            await self.event_store.save_events(
                order.id,
                events,
                expected_version=order.version - len(events)
            )
            order.clear_pending_events()
```

### Snapshots for Performance

```python
class SnapshotStore:
    async def save_snapshot(self, aggregate_id: str, state: dict, version: int):
        await self.db.execute(
            """INSERT INTO snapshots (aggregate_id, state, version)
               VALUES ($1, $2, $3)
               ON CONFLICT (aggregate_id)
               DO UPDATE SET state = $2, version = $3""",
            aggregate_id, json.dumps(state), version
        )

    async def get_snapshot(self, aggregate_id: str) -> Optional[tuple]:
        row = await self.db.fetchrow(
            "SELECT state, version FROM snapshots WHERE aggregate_id = $1",
            aggregate_id
        )
        return (json.loads(row["state"]), row["version"]) if row else None

class OrderRepositoryWithSnapshots(OrderRepository):
    SNAPSHOT_FREQUENCY = 100  # Snapshot every 100 events

    async def get(self, order_id: str) -> Order:
        order = Order(order_id)

        # Try to load from snapshot
        snapshot = await self.snapshot_store.get_snapshot(order_id)
        if snapshot:
            state, version = snapshot
            order._restore_from_snapshot(state)
            order.version = version
            # Only load events after snapshot
            events = await self.event_store.get_events_after(order_id, version)
        else:
            events = await self.event_store.get_events(order_id)

        for event in events:
            order.apply_event(event)

        return order

    async def save(self, order: Order):
        await super().save(order)

        # Create snapshot if needed
        if order.version % self.SNAPSHOT_FREQUENCY == 0:
            await self.snapshot_store.save_snapshot(
                order.id,
                order._get_snapshot(),
                order.version
            )
```

---

## Change Data Capture (CDC)

### Overview

Capture database changes and publish them as events for downstream consumers.

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  PostgreSQL  │────▶│   Debezium  │────▶│    Kafka     │
│  (Source DB) │     │   (CDC)     │     │   Topics     │
└──────────────┘     └─────────────┘     └──────┬───────┘
                                                │
                    ┌───────────────────────────┼───────────────────────┐
                    ▼                           ▼                       ▼
             ┌──────────────┐          ┌──────────────┐        ┌──────────────┐
             │ Search Index │          │ Analytics DB │        │ Cache Update │
             └──────────────┘          └──────────────┘        └──────────────┘
```

### Debezium Configuration

```json
{
  "name": "orders-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "${POSTGRES_PASSWORD}",
    "database.dbname": "orders",
    "database.server.name": "orders-db",
    "table.include.list": "public.orders,public.order_items",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_orders",
    "publication.name": "dbz_publication",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter"
  }
}
```

### CDC Event Consumer

```python
from aiokafka import AIOKafkaConsumer
import json

class CDCConsumer:
    """Consume CDC events and update downstream systems."""

    def __init__(self, bootstrap_servers: str, topic: str):
        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id="search-indexer",
            value_deserializer=lambda m: json.loads(m.decode())
        )

    async def start(self):
        await self.consumer.start()
        try:
            async for msg in self.consumer:
                await self._process_change(msg.value)
        finally:
            await self.consumer.stop()

    async def _process_change(self, change: dict):
        operation = change.get("op")  # c=create, u=update, d=delete
        table = change.get("source", {}).get("table")

        if table == "orders":
            if operation in ("c", "u"):
                await self._index_order(change["after"])
            elif operation == "d":
                await self._delete_order(change["before"]["id"])

    async def _index_order(self, order: dict):
        """Update search index."""
        await elasticsearch.index(
            index="orders",
            id=order["id"],
            document=order
        )

    async def _delete_order(self, order_id: str):
        """Remove from search index."""
        await elasticsearch.delete(index="orders", id=order_id)
```

---

## Transactional Outbox Pattern

Ensures reliable event publishing alongside database changes.

### Problem

```python
# ANTI-PATTERN: Not atomic
async def create_order(order: Order):
    await db.insert(order)           # What if this succeeds...
    await kafka.publish(order_event) # ...but this fails?
```

### Solution: Outbox Table

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE INDEX idx_outbox_unprocessed ON outbox (created_at)
WHERE processed_at IS NULL;
```

### Implementation

```python
from dataclasses import dataclass
import json
import uuid

@dataclass
class OutboxEvent:
    id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict

class OutboxRepository:
    async def save_with_outbox(self, entity, events: list[OutboxEvent]):
        """Save entity and outbox events in single transaction."""
        async with self.db.transaction():
            # Save the entity
            await self._save_entity(entity)

            # Save events to outbox (same transaction)
            for event in events:
                await self.db.execute(
                    """INSERT INTO outbox
                       (id, aggregate_type, aggregate_id, event_type, payload)
                       VALUES ($1, $2, $3, $4, $5)""",
                    event.id, event.aggregate_type, event.aggregate_id,
                    event.event_type, json.dumps(event.payload)
                )

# Order Service using outbox
class OrderService:
    async def create_order(self, request: CreateOrderRequest) -> Order:
        order = Order.create(request)

        # Create outbox event
        outbox_event = OutboxEvent(
            id=str(uuid.uuid4()),
            aggregate_type="Order",
            aggregate_id=order.id,
            event_type="OrderCreated",
            payload=order.to_dict()
        )

        # Save order and event atomically
        await self.repository.save_with_outbox(order, [outbox_event])

        return order

# Outbox Publisher (separate process)
class OutboxPublisher:
    """Polls outbox and publishes to message broker."""

    async def run(self):
        while True:
            async with self.db.transaction():
                # Get unprocessed events (with lock)
                events = await self.db.fetch(
                    """SELECT * FROM outbox
                       WHERE processed_at IS NULL
                       ORDER BY created_at
                       LIMIT 100
                       FOR UPDATE SKIP LOCKED"""
                )

                for event in events:
                    # Publish to Kafka
                    await self.kafka.publish(
                        topic=f"{event['aggregate_type'].lower()}-events",
                        key=event['aggregate_id'],
                        value=event['payload']
                    )

                    # Mark as processed
                    await self.db.execute(
                        "UPDATE outbox SET processed_at = NOW() WHERE id = $1",
                        event['id']
                    )

            await asyncio.sleep(1)  # Poll interval
```

### CDC-based Outbox (Alternative)

Use Debezium to capture outbox changes instead of polling:

```json
{
  "name": "outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.server.name": "orders-db",
    "table.include.list": "public.outbox",
    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.field.event.key": "aggregate_id",
    "transforms.outbox.table.field.event.type": "event_type",
    "transforms.outbox.table.field.event.payload": "payload",
    "transforms.outbox.route.topic.replacement": "${routedByValue}-events"
  }
}
```

---

## Data Synchronization Patterns

### API Composition

```python
class OrderDetailsComposer:
    """Compose order details from multiple services."""

    async def get_order_details(self, order_id: str) -> dict:
        # Parallel calls to services
        order, customer, products = await asyncio.gather(
            self.order_service.get(order_id),
            self.customer_service.get(order.customer_id),
            self.product_service.get_many([i.product_id for i in order.items])
        )

        # Compose response
        return {
            "order": order,
            "customer": {
                "id": customer.id,
                "name": customer.name
            },
            "items": [
                {**item, "product": products[item.product_id]}
                for item in order.items
            ]
        }
```

### Saga for Distributed Transactions

See `communication-patterns.md` for detailed Saga implementation.

---

## Implementation Checklist

- [ ] **Database per Service**: Each service has isolated database
- [ ] **Data Ownership**: Clear owner for each data entity
- [ ] **Consistency Model**: Documented (strong vs eventual) per use case
- [ ] **Event Publishing**: Outbox pattern or CDC configured
- [ ] **Cross-Service Queries**: API composition or CQRS views
- [ ] **Distributed Transactions**: Saga pattern for multi-service operations
- [ ] **Data Backup**: Per-service backup strategy
- [ ] **Schema Evolution**: Migration strategy without service coupling
