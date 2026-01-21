---
name: microservices-architect
description: |
  Guides enterprise microservices architecture design and validation.
  This skill should be used when users ask to design distributed systems,
  decompose monoliths, choose communication patterns, implement resilience,
  set up observability, validate architectural decisions, or create service specifications.
---

# Microservices Architect

Guide enterprise microservices architecture design and validation for professional software engineers.

## What This Skill Does

- Guides service decomposition using DDD and bounded contexts
- Recommends communication patterns (sync/async, CQRS, Saga)
- Designs data management strategies (polyglot persistence, event sourcing)
- Implements resilience patterns (circuit breaker, bulkhead, retry)
- Sets up observability (tracing, metrics, logging)
- Applies security patterns (zero trust, mTLS)
- Plans deployment strategies (blue-green, canary)
- Creates Architecture Decision Records (ADRs)
- Generates C4 diagrams (Mermaid)
- Validates existing architectures against best practices

## What This Skill Does NOT Do

- Implement actual microservices code (provides patterns, not implementation)
- Configure specific infrastructure (provides guidance, not scripts)
- Replace dedicated security audits
- Handle cloud-specific configurations (cloud-agnostic patterns)

---

## Before Implementation

Gather context to ensure successful architecture design:

| Source | Gather |
|--------|--------|
| **Codebase** | Existing services, APIs, data stores, deployment configs |
| **Conversation** | Business context, scale requirements, team structure, constraints |
| **Skill References** | Domain patterns from `references/` (decomposition, communication, resilience) |
| **User Guidelines** | Company architecture standards, compliance requirements |

Only ask user for THEIR specific requirements (domain expertise is in this skill).

---

## AI-Native Workflow

### Phase 1: Discovery

Ask about business and technical context:

**Business Context**
- What problem are you solving?
- What business capabilities need to be supported?
- What scale do you need (users, requests/sec, data volume)?
- Any compliance requirements (GDPR, PCI-DSS, HIPAA)?

**Technical Context**
- Greenfield or monolith decomposition?
- Current/preferred tech stack?
- Team size and structure?

**Constraints**
- Timeline considerations?
- Must-use technologies?
- Existing integrations?

### Phase 2: Design

Produce architecture deliverables:

1. **Executive Summary** - Problem, approach, key decisions
2. **Service Decomposition** - Bounded contexts, service boundaries (C4 diagram)
3. **Communication Patterns** - Sync vs async decisions with rationale
4. **Data Strategy** - Database per service, consistency model
5. **Key ADRs** - Top 3-5 architectural decisions
6. **Risks & Mitigations** - Identified risks with mitigation strategies

### Phase 3: Validation

Validate architecture against checklist:

| Area | Check |
|------|-------|
| **Service Design** | Bounded contexts clear? Services properly sized? |
| **Communication** | No long sync chains? Sagas for distributed transactions? |
| **Data** | Clear ownership? Consistency model defined? |
| **Resilience** | Circuit breakers? Timeouts? Fallbacks? |
| **Observability** | Distributed tracing? Metrics? SLOs defined? |
| **Security** | Zero trust? mTLS? Secrets management? |

### Phase 4: Implementation Guidance

Provide concrete next steps:
- Infrastructure setup priorities
- Service implementation order
- Testing strategy
- Operational readiness checklist

---

## Quick Reference

### When to Use Microservices

| Factor | Microservices | Monolith |
|--------|--------------|----------|
| Team size | Multiple autonomous teams | Single/small team |
| Domain complexity | High, clear boundaries | Moderate, intertwined |
| Scale requirements | Independent scaling needed | Uniform scaling OK |
| Release cadence | Independent deployments | Coordinated releases OK |
| Operational maturity | High (DevOps, monitoring) | Lower |

### Communication Pattern Selection

| Requirement | Pattern |
|-------------|---------|
| Immediate response needed | Sync (REST/gRPC) |
| Fire-and-forget | Async messaging |
| High throughput | Event streaming |
| Complex transactions | Saga (choreography/orchestration) |
| Query optimization | CQRS |

### Database Strategy

| Requirement | Strategy |
|-------------|----------|
| Strong consistency | Single database / 2PC (limited) |
| Eventual consistency | Event sourcing + CDC |
| Read-heavy workloads | CQRS with read replicas |
| Mixed data types | Polyglot persistence |

### Resilience Essentials

| Pattern | When to Use |
|---------|-------------|
| Circuit Breaker | Prevent cascade failures |
| Bulkhead | Isolate failure domains |
| Retry + Backoff | Transient failures |
| Timeout | Prevent resource exhaustion |
| Fallback | Graceful degradation |

---

## Output Templates

Use templates from `assets/templates/`:

| Template | Purpose |
|----------|---------|
| `adr-template.md` | Document architectural decisions |
| `service-spec.md` | Define service specifications |
| `c4-diagrams.md` | Generate architecture diagrams |

---

## Reference Files

| File | When to Read |
|------|--------------|
| `references/decision-frameworks.md` | Choosing between architectural approaches |
| `references/decomposition-strategies.md` | Breaking down monoliths, defining service boundaries |
| `references/communication-patterns.md` | REST vs gRPC vs async, CQRS, Saga patterns |
| `references/data-management.md` | Database per service, event sourcing, CDC |
| `references/resilience-patterns.md` | Circuit breaker, bulkhead, retry patterns |
| `references/observability.md` | Tracing, metrics, logging, SLOs |
| `references/security-patterns.md` | Zero trust, mTLS, secrets management |
| `references/deployment-strategies.md` | Blue-green, canary, feature flags |
| `references/testing-strategies.md` | Contract testing, chaos engineering |
| `references/anti-patterns.md` | Common mistakes to avoid |

**Large file search patterns:**
```
grep -n "circuit breaker" references/resilience-patterns.md
grep -n "saga" references/communication-patterns.md
grep -n "bounded context" references/decomposition-strategies.md
```

---

## Output Checklist

Before delivering architecture design, verify:

### Discovery Complete
- [ ] Business capabilities identified
- [ ] Scale requirements understood
- [ ] Compliance needs documented
- [ ] Team structure considered

### Design Quality
- [ ] Service boundaries aligned with bounded contexts
- [ ] Communication patterns appropriate for requirements
- [ ] Data ownership clearly defined
- [ ] Resilience patterns specified
- [ ] Observability strategy defined
- [ ] Security model documented

### Deliverables
- [ ] Executive summary provided
- [ ] C4 diagrams generated (context, container)
- [ ] Key ADRs documented (3-5)
- [ ] Risks identified with mitigations
- [ ] Implementation roadmap provided

### Validation
- [ ] No distributed monolith patterns
- [ ] No synchronous chains > 3 services
- [ ] Each service has single owner
- [ ] Failure modes documented
- [ ] SLOs defined for critical paths
