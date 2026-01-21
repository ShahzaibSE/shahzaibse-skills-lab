# ADR-{NUMBER}: {TITLE}

## Status

{Proposed | Accepted | Deprecated | Superseded by ADR-XXX}

## Date

{YYYY-MM-DD}

## Context

{Describe the forces at play, including technological, political, social, and project context. What is the issue that motivates this decision?}

### Background

{Additional context about the current state, constraints, and requirements}

### Constraints

- {Constraint 1}
- {Constraint 2}

## Decision

{Describe the decision and its rationale. Use active voice: "We will..."}

### Chosen Option

**{Option Name}**

{Detailed description of the chosen approach}

## Alternatives Considered

### Option 1: {Name}

**Description**: {Brief description}

**Pros**:
- {Pro 1}
- {Pro 2}

**Cons**:
- {Con 1}
- {Con 2}

### Option 2: {Name}

**Description**: {Brief description}

**Pros**:
- {Pro 1}
- {Pro 2}

**Cons**:
- {Con 1}
- {Con 2}

## Consequences

### Positive

- {Positive consequence 1}
- {Positive consequence 2}

### Negative

- {Negative consequence 1}
- {Negative consequence 2}

### Neutral

- {Neutral consequence or trade-off}

## Implementation

### Action Items

- [ ] {Action item 1}
- [ ] {Action item 2}
- [ ] {Action item 3}

### Migration Plan

{If applicable, describe how to migrate from current state}

## Related Decisions

- ADR-{XXX}: {Related decision title}
- ADR-{YYY}: {Another related decision}

## References

- {Link to relevant documentation}
- {Link to relevant RFC or specification}

---

## Example ADRs

### ADR-001: Use Event-Driven Communication Between Order and Inventory Services

**Status**: Accepted

**Date**: 2024-01-15

**Context**: The order service needs to notify the inventory service when orders are placed, confirmed, or cancelled. Currently using synchronous REST calls, causing latency issues and coupling.

**Decision**: We will use Apache Kafka for asynchronous event-driven communication between Order and Inventory services.

**Consequences**:
- Positive: Decoupled services, better fault tolerance, easier scaling
- Negative: Added infrastructure complexity, eventual consistency
- Neutral: Team needs Kafka training

---

### ADR-002: Adopt PostgreSQL for Order Service Database

**Status**: Accepted

**Date**: 2024-01-10

**Context**: Need to select a database for the new order service. Requirements include ACID transactions, complex queries, and JSON support.

**Decision**: We will use PostgreSQL 15 as the primary database for the order service.

**Alternatives Considered**:
1. MongoDB - Good for flexibility but weaker transaction support
2. MySQL - Viable but PostgreSQL has better JSON and advanced features

**Consequences**:
- Positive: Strong consistency, rich feature set, team expertise
- Negative: Horizontal scaling requires more planning
