# Decision Frameworks

Structured decision matrices for key architectural choices.

---

## Microservices vs Monolith

### Decision Matrix

| Factor | Weight | Microservices Score | Monolith Score |
|--------|--------|---------------------|----------------|
| Team size >20 | 25% | +3 if yes | +3 if no |
| Independent scaling needed | 20% | +3 if yes | +3 if no |
| Different release cadences | 20% | +3 if yes | +3 if no |
| Clear domain boundaries | 15% | +3 if yes | +3 if no |
| Operational maturity high | 10% | +3 if yes | +3 if no |
| Polyglot requirements | 10% | +3 if yes | +3 if no |

**Threshold**: Score >60% suggests microservices; <40% suggests monolith; 40-60% consider modular monolith.

### Warning Signs for Microservices

- Small team (<8 engineers)
- Unclear domain boundaries
- Limited DevOps capabilities
- No distributed systems experience
- Tight timeline with greenfield

### Start with Monolith When

- Exploring product-market fit
- Team learning the domain
- Rapid prototyping phase
- Limited operational resources

---

## Synchronous vs Asynchronous Communication

### Decision Matrix

| Requirement | Sync (REST/gRPC) | Async (Events/Messages) |
|-------------|------------------|-------------------------|
| Immediate response needed | Yes | No |
| Caller needs result | Yes | Maybe (async-await) |
| Temporal coupling acceptable | Yes | No |
| High throughput required | Sometimes | Yes |
| Fire-and-forget | No | Yes |
| Reliability critical | Moderate | High (with queues) |

### Choose Synchronous When

- Request-response semantics required
- Low latency critical
- Simple query operations
- Service discovery sufficient
- Client expects immediate result

### Choose Asynchronous When

- Fire-and-forget acceptable
- High throughput needed
- Temporal decoupling required
- Multiple consumers need same event
- Reliability > latency

### Hybrid Approach

Most systems use both:
```
┌─────────┐  sync   ┌─────────┐  async  ┌─────────┐
│   API   │ ──────> │ Orders  │ ──────> │ Notify  │
│ Gateway │         │ Service │         │ Service │
└─────────┘         └─────────┘         └─────────┘
                         │
                         │ async
                         ▼
                    ┌─────────┐
                    │Inventory│
                    │ Service │
                    └─────────┘
```

---

## Database Per Service vs Shared Database

### Decision Matrix

| Factor | Database Per Service | Shared Database |
|--------|---------------------|-----------------|
| Team autonomy | High | Low |
| Schema evolution | Independent | Coordinated |
| Data consistency | Eventual | Strong |
| Joins across services | Hard (API calls) | Easy |
| Deployment independence | High | Low |
| Operational complexity | Higher | Lower |

### Choose Database Per Service When

- Teams own data lifecycle
- Different data stores needed
- Independent scaling required
- Services change frequently
- Strong isolation needed

### Choose Shared Database When

- Strong consistency required
- Complex cross-service queries
- Limited operational capacity
- Monolith extraction in progress
- Small team

### Migration Path

```
Shared DB → Schema per Service → Database per Service
```

1. Start with schema isolation
2. Move to separate connections
3. Extract to separate instances
4. Add API layer for cross-service data

---

## Service Mesh vs Library

### Decision Matrix

| Factor | Service Mesh | Library (SDK) |
|--------|--------------|---------------|
| Language diversity | Excellent | Per-language impl |
| Runtime overhead | Sidecar cost | In-process |
| Operational complexity | Higher | Lower |
| Feature updates | Central deploy | Per-service |
| Debugging | Separate process | In-process |
| Security (mTLS) | Automatic | Manual |

### Choose Service Mesh When

- Multiple languages/frameworks
- Need uniform policy enforcement
- mTLS everywhere required
- Advanced traffic management needed
- Large number of services (>20)

### Choose Library When

- Single language/framework
- Small number of services
- Want simpler debugging
- Resource constrained
- Team familiar with patterns

### Popular Service Meshes

| Mesh | Strengths | Considerations |
|------|-----------|----------------|
| Istio | Feature-rich, Envoy-based | Complex, resource heavy |
| Linkerd | Lightweight, simple | Fewer features |
| Consul Connect | HashiCorp ecosystem | Service discovery focused |

---

## Event Sourcing vs State Sourcing

### Decision Matrix

| Factor | Event Sourcing | State Sourcing |
|--------|---------------|----------------|
| Audit requirements | Excellent | Requires extra work |
| Temporal queries | Natural | Difficult |
| Storage cost | Higher | Lower |
| Query complexity | Higher (projections) | Lower (direct) |
| Debugging | Event replay | Point-in-time state |
| Learning curve | Steeper | Familiar |

### Choose Event Sourcing When

- Audit trail required
- Need to replay history
- Complex domain with many state transitions
- Multiple views of same data
- Regulatory compliance

### Choose State Sourcing When

- Simple CRUD operations
- No audit requirements
- Direct queries needed
- Team unfamiliar with ES
- Time constraints

---

## API Gateway Pattern

### When to Use

| Scenario | API Gateway | Direct Service |
|----------|-------------|----------------|
| Public APIs | Yes | No |
| Mobile clients | Yes | Rarely |
| Multiple backends | Yes | No |
| Auth centralization | Yes | Sometimes |
| Service-to-service | Rarely | Yes |

### Gateway Responsibilities

**Should Handle**:
- Authentication/Authorization
- Rate limiting
- Request routing
- Protocol translation
- Response aggregation

**Should NOT Handle**:
- Business logic
- Data transformation
- Complex orchestration
- Long-running transactions

### Gateway Options

| Gateway | Type | Best For |
|---------|------|----------|
| Kong | Full-featured | Enterprise, plugin ecosystem |
| AWS API Gateway | Managed | AWS-native, serverless |
| Envoy | Proxy | Service mesh, high performance |
| NGINX | Reverse proxy | Simple routing, static config |

---

## CQRS Decision

### When to Use CQRS

| Indicator | Score |
|-----------|-------|
| Read/write ratio >10:1 | +2 |
| Complex read queries | +2 |
| Different scaling needs | +2 |
| Event sourcing in use | +2 |
| Need different read models | +2 |

**Score ≥6**: Strong CQRS candidate
**Score 3-5**: Consider partial CQRS
**Score <3**: Likely not needed

### CQRS Complexity Levels

```
Level 1: Separate read/write models (same DB)
Level 2: Separate read/write databases
Level 3: Event sourcing + projections
```

Start at Level 1, evolve only if needed.

---

## Saga Pattern Selection

### Choreography vs Orchestration

| Factor | Choreography | Orchestration |
|--------|--------------|---------------|
| Coupling | Loose | Central coordinator |
| Complexity visibility | Distributed | Centralized |
| Failure handling | Per-service | Central logic |
| New steps | Publish new events | Update orchestrator |
| Debugging | Harder (trace events) | Easier (central log) |

### Choose Choreography When

- Few services (2-4) in saga
- Services already event-driven
- Want loose coupling
- Simple compensation logic

### Choose Orchestration When

- Many services (>4) in saga
- Complex business logic
- Need central visibility
- Complex compensation
- SLA requirements

### Example: Order Saga

**Choreography**:
```
Order → [OrderCreated] → Inventory → [Reserved] → Payment → [Paid] → Order
```

**Orchestration**:
```
Order Orchestrator
  → Create Order
  → Reserve Inventory
  → Process Payment
  → Confirm Order
```

---

## Technology Selection Checklists

### Message Broker Selection

| Requirement | Kafka | RabbitMQ | AWS SQS |
|-------------|-------|----------|---------|
| High throughput | Excellent | Good | Good |
| Ordering | Partition-level | Queue-level | FIFO queues |
| Replay | Yes | No | No |
| Managed option | Confluent/MSK | CloudAMQP | Native |
| Operational complexity | Higher | Medium | Low |

### Database Selection

| Need | PostgreSQL | MongoDB | Redis | Elasticsearch |
|------|------------|---------|-------|---------------|
| Transactions | Excellent | Limited | Limited | No |
| Schema flexibility | Moderate | Excellent | High | Good |
| Search | Basic | Good | Limited | Excellent |
| Caching | No | No | Excellent | No |
| Analytics | Good | Good | No | Excellent |

---

## Decision Documentation

For each major decision, create an ADR using `assets/templates/adr-template.md`:

1. **Context**: What situation required this decision?
2. **Decision**: What did you decide?
3. **Consequences**: What are the trade-offs?
4. **Alternatives**: What else was considered?
