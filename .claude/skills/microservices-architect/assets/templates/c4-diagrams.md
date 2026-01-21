# C4 Diagram Templates

C4 model provides four levels of abstraction for visualizing software architecture.

---

## Level 1: System Context Diagram

Shows the system in scope and its relationships with users and other systems.

```mermaid
C4Context
    title System Context Diagram - {System Name}

    Person(customer, "Customer", "A user of the platform")
    Person(admin, "Admin", "System administrator")

    System(system, "{System Name}", "Core system description")

    System_Ext(payment, "Payment Provider", "Processes payments")
    System_Ext(email, "Email Service", "Sends notifications")
    System_Ext(analytics, "Analytics Platform", "Usage tracking")

    Rel(customer, system, "Uses", "HTTPS")
    Rel(admin, system, "Manages", "HTTPS")
    Rel(system, payment, "Processes payments", "HTTPS/API")
    Rel(system, email, "Sends emails", "SMTP")
    Rel(system, analytics, "Sends events", "HTTPS")
```

### Alternative (Text-based for compatibility)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYSTEM CONTEXT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    ┌──────────┐                           ┌──────────┐         │
│    │ Customer │                           │  Admin   │         │
│    └────┬─────┘                           └────┬─────┘         │
│         │                                      │               │
│         │  Uses (HTTPS)          Manages (HTTPS)               │
│         │                                      │               │
│         └──────────────┬───────────────────────┘               │
│                        │                                       │
│                        ▼                                       │
│              ┌─────────────────┐                               │
│              │   {System}      │                               │
│              │                 │                               │
│              │  Core platform  │                               │
│              └────────┬────────┘                               │
│                       │                                        │
│         ┌─────────────┼─────────────┐                         │
│         │             │             │                          │
│         ▼             ▼             ▼                          │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│   │ Payment  │  │  Email   │  │Analytics │                    │
│   │ Provider │  │ Service  │  │ Platform │                    │
│   └──────────┘  └──────────┘  └──────────┘                    │
│   [External]    [External]    [External]                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Level 2: Container Diagram

Shows the high-level technical building blocks (containers) within the system.

```mermaid
C4Container
    title Container Diagram - {System Name}

    Person(customer, "Customer", "Platform user")

    System_Boundary(system, "{System Name}") {
        Container(web, "Web Application", "React", "Delivers the SPA")
        Container(api, "API Gateway", "Kong", "Routes and authenticates requests")
        Container(order, "Order Service", "Python/FastAPI", "Handles order processing")
        Container(payment, "Payment Service", "Python/FastAPI", "Processes payments")
        Container(inventory, "Inventory Service", "Go", "Manages stock levels")

        ContainerDb(orderdb, "Order Database", "PostgreSQL", "Stores orders")
        ContainerDb(inventorydb, "Inventory Database", "PostgreSQL", "Stores inventory")
        ContainerQueue(kafka, "Message Broker", "Kafka", "Async messaging")
        ContainerDb(cache, "Cache", "Redis", "Session and data cache")
    }

    System_Ext(stripe, "Stripe", "Payment processing")

    Rel(customer, web, "Uses", "HTTPS")
    Rel(web, api, "API calls", "HTTPS/JSON")
    Rel(api, order, "Routes to", "HTTP")
    Rel(api, inventory, "Routes to", "HTTP")
    Rel(order, orderdb, "Reads/Writes", "TCP")
    Rel(order, kafka, "Publishes events", "TCP")
    Rel(payment, kafka, "Consumes events", "TCP")
    Rel(payment, stripe, "Processes payment", "HTTPS")
    Rel(inventory, inventorydb, "Reads/Writes", "TCP")
    Rel(inventory, kafka, "Publishes/Consumes", "TCP")
```

### Text-based Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              {SYSTEM NAME}                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [Customer]                                                                │
│       │                                                                     │
│       │ HTTPS                                                               │
│       ▼                                                                     │
│   ┌───────────────┐                                                         │
│   │ Web App       │                                                         │
│   │ [React SPA]   │                                                         │
│   └───────┬───────┘                                                         │
│           │ HTTPS/JSON                                                      │
│           ▼                                                                 │
│   ┌───────────────┐                                                         │
│   │ API Gateway   │                                                         │
│   │ [Kong]        │                                                         │
│   └───────┬───────┘                                                         │
│           │                                                                 │
│     ┌─────┴─────┬─────────────┐                                            │
│     │           │             │                                             │
│     ▼           ▼             ▼                                             │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐                                        │
│ │ Order   │ │ Payment │ │Inventory│                                        │
│ │ Service │ │ Service │ │ Service │                                        │
│ │[FastAPI]│ │[FastAPI]│ │  [Go]   │                                        │
│ └────┬────┘ └────┬────┘ └────┬────┘                                        │
│      │           │           │                                              │
│      │     ┌─────┴─────┐     │                                              │
│      │     │   Kafka   │     │                                              │
│      │     │  [Broker] │◄────┤                                              │
│      │     └───────────┘     │                                              │
│      │                       │                                              │
│      ▼                       ▼                                              │
│ ┌─────────┐            ┌─────────┐                                         │
│ │Order DB │            │Inv. DB  │                                         │
│ │[Postgres]│           │[Postgres]│                                        │
│ └─────────┘            └─────────┘                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Level 3: Component Diagram

Shows the components within a single container.

```mermaid
C4Component
    title Component Diagram - Order Service

    Container_Boundary(order, "Order Service") {
        Component(api, "API Layer", "FastAPI", "REST API endpoints")
        Component(service, "Order Service", "Python", "Business logic")
        Component(repo, "Order Repository", "SQLAlchemy", "Data access")
        Component(events, "Event Publisher", "Python", "Publishes domain events")
        Component(client_inv, "Inventory Client", "HTTPX", "Calls inventory service")
        Component(client_pay, "Payment Client", "HTTPX", "Calls payment service")
    }

    ContainerDb(db, "Order Database", "PostgreSQL")
    ContainerQueue(kafka, "Kafka", "Message Broker")
    Container(inventory, "Inventory Service", "Go")
    Container(payment, "Payment Service", "Python")

    Rel(api, service, "Uses")
    Rel(service, repo, "Uses")
    Rel(service, events, "Publishes via")
    Rel(service, client_inv, "Checks inventory via")
    Rel(service, client_pay, "Processes payment via")
    Rel(repo, db, "Reads/Writes")
    Rel(events, kafka, "Publishes to")
    Rel(client_inv, inventory, "HTTP")
    Rel(client_pay, payment, "HTTP")
```

### Text-based Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORDER SERVICE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                      API Layer                          │  │
│   │                     [FastAPI]                           │  │
│   │  POST /orders  GET /orders/{id}  PUT /orders/{id}       │  │
│   └─────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    Order Service                        │  │
│   │                   [Business Logic]                      │  │
│   │                                                         │  │
│   │  create_order()  confirm_order()  cancel_order()        │  │
│   └──────┬──────────────────┬──────────────────┬────────────┘  │
│          │                  │                  │                │
│          │                  │                  │                │
│    ┌─────▼─────┐     ┌──────▼──────┐    ┌─────▼─────┐         │
│    │ Order     │     │   Event     │    │  Clients  │         │
│    │ Repository│     │  Publisher  │    │           │         │
│    │[SQLAlchemy]│    │             │    │ Inventory │         │
│    └─────┬─────┘     └──────┬──────┘    │ Payment   │         │
│          │                  │           └─────┬─────┘         │
│          │                  │                 │                │
└──────────┼──────────────────┼─────────────────┼────────────────┘
           │                  │                 │
           ▼                  ▼                 ▼
      ┌─────────┐       ┌─────────┐      ┌───────────┐
      │Order DB │       │  Kafka  │      │ External  │
      │[Postgres]│      │         │      │ Services  │
      └─────────┘       └─────────┘      └───────────┘
```

---

## Sequence Diagrams

### Order Creation Flow

```mermaid
sequenceDiagram
    participant C as Customer
    participant AG as API Gateway
    participant OS as Order Service
    participant IS as Inventory Service
    participant PS as Payment Service
    participant K as Kafka
    participant NS as Notification Service

    C->>AG: POST /orders
    AG->>AG: Validate JWT
    AG->>OS: Forward request

    OS->>IS: Check inventory
    IS-->>OS: Available

    OS->>OS: Create order (pending)
    OS->>K: Publish OrderCreated

    OS-->>AG: 201 Created
    AG-->>C: Order created

    K->>PS: OrderCreated event
    PS->>PS: Process payment
    PS->>K: Publish PaymentCompleted

    K->>OS: PaymentCompleted event
    OS->>OS: Update order (confirmed)
    OS->>K: Publish OrderConfirmed

    K->>IS: OrderConfirmed event
    IS->>IS: Reserve inventory

    K->>NS: OrderConfirmed event
    NS->>C: Send confirmation email
```

### Text-based Sequence

```
Customer    API Gateway    Order Svc    Inventory    Payment    Kafka
   │             │             │            │           │          │
   │ POST /orders│             │            │           │          │
   │────────────>│             │            │           │          │
   │             │ Validate JWT│            │           │          │
   │             │─────────────│            │           │          │
   │             │             │            │           │          │
   │             │ Forward     │            │           │          │
   │             │────────────>│            │           │          │
   │             │             │            │           │          │
   │             │             │ Check stock│           │          │
   │             │             │───────────>│           │          │
   │             │             │<───────────│           │          │
   │             │             │ Available  │           │          │
   │             │             │            │           │          │
   │             │             │ Create order           │          │
   │             │             │────────────────────────────────>  │
   │             │             │            │           │ OrderCreated
   │             │<────────────│            │           │          │
   │<────────────│ 201 Created │            │           │          │
   │             │             │            │           │          │
   │             │             │            │           │<─────────│
   │             │             │            │           │ Process  │
   │             │             │            │           │──────────>
   │             │             │            │           │ PaymentCompleted
   │             │             │<──────────────────────────────────│
   │             │             │ Update status          │          │
   │             │             │────────────────────────────────>  │
   │             │             │            │           │ OrderConfirmed
```

---

## Deployment Diagram

```mermaid
C4Deployment
    title Deployment Diagram - Production

    Deployment_Node(aws, "AWS", "Cloud Provider") {
        Deployment_Node(vpc, "VPC", "10.0.0.0/16") {
            Deployment_Node(eks, "EKS Cluster", "Kubernetes") {
                Deployment_Node(ns_prod, "production namespace") {
                    Container(order, "Order Service", "3 replicas")
                    Container(payment, "Payment Service", "3 replicas")
                    Container(inventory, "Inventory Service", "3 replicas")
                }
            }

            Deployment_Node(rds, "RDS", "Managed PostgreSQL") {
                ContainerDb(orderdb, "order-db", "PostgreSQL 15")
                ContainerDb(inventorydb, "inventory-db", "PostgreSQL 15")
            }

            Deployment_Node(msk, "MSK", "Managed Kafka") {
                ContainerQueue(kafka, "events", "3 brokers")
            }
        }
    }

    Deployment_Node(cloudflare, "Cloudflare", "CDN/WAF") {
        Container(cdn, "CDN", "Static assets")
    }
```

### Text-based Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         VPC (10.0.0.0/16)                           │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    EKS CLUSTER                              │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │                                                             │   │   │
│  │  │  ┌─────────────────────────────────────────────────────┐   │   │   │
│  │  │  │              production namespace                   │   │   │   │
│  │  │  │                                                     │   │   │   │
│  │  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │   │   │
│  │  │  │  │ Order   │  │ Payment │  │Inventory│            │   │   │   │
│  │  │  │  │ Service │  │ Service │  │ Service │            │   │   │   │
│  │  │  │  │(3 pods) │  │(3 pods) │  │(3 pods) │            │   │   │   │
│  │  │  │  └─────────┘  └─────────┘  └─────────┘            │   │   │   │
│  │  │  │                                                     │   │   │   │
│  │  │  └─────────────────────────────────────────────────────┘   │   │   │
│  │  │                                                             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐         │   │
│  │  │        RDS              │  │         MSK             │         │   │
│  │  │  ┌─────────┐           │  │  ┌─────────┐           │         │   │
│  │  │  │order-db │           │  │  │ Kafka   │           │         │   │
│  │  │  │[Primary]│           │  │  │ Cluster │           │         │   │
│  │  │  └─────────┘           │  │  │(3 nodes)│           │         │   │
│  │  │  ┌─────────┐           │  │  └─────────┘           │         │   │
│  │  │  │inv-db   │           │  │                         │         │   │
│  │  │  │[Primary]│           │  │                         │         │   │
│  │  │  └─────────┘           │  │                         │         │   │
│  │  └─────────────────────────┘  └─────────────────────────┘         │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Usage Guidelines

1. **Start with Context (L1)**: Always begin with the big picture
2. **Zoom into Containers (L2)**: Show technical building blocks
3. **Detail Components (L3)**: Only for complex services that need explanation
4. **Code Level (L4)**: Rarely needed, usually generated from code

### When to Use Each Level

| Audience | Recommended Levels |
|----------|-------------------|
| Executives | L1 only |
| Architects | L1, L2 |
| Developers | L2, L3 |
| New team members | L1, L2, L3 |

### Diagram Maintenance

- Update diagrams when architecture changes
- Store in version control alongside code
- Generate from code where possible
- Review during architecture meetings
