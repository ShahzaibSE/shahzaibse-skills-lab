# Deployment Strategies

## Overview

Safe deployment strategies minimize risk when releasing changes to production. Each strategy offers different trade-offs between speed, safety, and resource cost.

---

## Strategy Comparison

| Strategy | Rollback Speed | Resource Cost | Risk Level | Best For |
|----------|----------------|---------------|------------|----------|
| **Blue-Green** | Instant | 2x | Low | Critical services |
| **Canary** | Fast | 1.1-1.5x | Low | Gradual validation |
| **Rolling** | Slow | 1x | Medium | Stateless services |
| **Feature Flags** | Instant | 1x | Low | Feature control |

---

## Blue-Green Deployment

### Concept

Maintain two identical production environments. Switch traffic instantly between them.

```
                    Load Balancer
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼                           ▼
    ┌─────────────┐             ┌─────────────┐
    │    BLUE     │             │   GREEN     │
    │  (Current)  │             │   (New)     │
    │   v1.0.0    │             │   v1.1.0    │
    └─────────────┘             └─────────────┘
           │                           │
           ▼                           ▼
    ┌─────────────┐             ┌─────────────┐
    │  Database   │◄───────────►│  Database   │
    │  (Shared)   │             │  (Shared)   │
    └─────────────┘             └─────────────┘
```

### Kubernetes Implementation

```yaml
# Blue deployment (current)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service-blue
  labels:
    app: order-service
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
      version: blue
  template:
    metadata:
      labels:
        app: order-service
        version: blue
    spec:
      containers:
        - name: order-service
          image: order-service:v1.0.0

---
# Green deployment (new)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service-green
  labels:
    app: order-service
    version: green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
      version: green
  template:
    metadata:
      labels:
        app: order-service
        version: green
    spec:
      containers:
        - name: order-service
          image: order-service:v1.1.0

---
# Service pointing to blue (switch to green for cutover)
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  selector:
    app: order-service
    version: blue  # Change to 'green' for cutover
  ports:
    - port: 80
      targetPort: 8080
```

### Blue-Green Script

```bash
#!/bin/bash
# blue-green-deploy.sh

NEW_VERSION=$1
CURRENT_COLOR=$(kubectl get svc order-service -o jsonpath='{.spec.selector.version}')
NEW_COLOR=$([[ "$CURRENT_COLOR" == "blue" ]] && echo "green" || echo "blue")

echo "Current: $CURRENT_COLOR, Deploying to: $NEW_COLOR"

# Deploy new version to inactive environment
kubectl set image deployment/order-service-$NEW_COLOR \
  order-service=order-service:$NEW_VERSION

# Wait for rollout
kubectl rollout status deployment/order-service-$NEW_COLOR

# Run smoke tests against new deployment
kubectl run smoke-test --rm -it --image=curlimages/curl \
  -- curl -f http://order-service-$NEW_COLOR:8080/health

if [ $? -eq 0 ]; then
  # Switch traffic
  kubectl patch svc order-service -p "{\"spec\":{\"selector\":{\"version\":\"$NEW_COLOR\"}}}"
  echo "Traffic switched to $NEW_COLOR"
else
  echo "Smoke test failed, aborting deployment"
  exit 1
fi
```

---

## Canary Deployment

### Concept

Gradually shift traffic from old version to new, monitoring for issues.

```
Traffic Split Over Time:

Time 0:    [████████████████████] 100% v1.0  │  0% v1.1
Time 1:    [██████████████████░░]  90% v1.0  │ 10% v1.1
Time 2:    [██████████████░░░░░░]  70% v1.0  │ 30% v1.1
Time 3:    [██████████░░░░░░░░░░]  50% v1.0  │ 50% v1.1
Time 4:    [░░░░░░░░░░░░░░░░░░░░]   0% v1.0  │100% v1.1
```

### Istio Canary Configuration

```yaml
# VirtualService for traffic splitting
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: order-service
spec:
  hosts:
    - order-service
  http:
    - match:
        - headers:
            x-canary:
              exact: "true"
      route:
        - destination:
            host: order-service
            subset: canary
    - route:
        - destination:
            host: order-service
            subset: stable
          weight: 90
        - destination:
            host: order-service
            subset: canary
          weight: 10

---
# DestinationRule defining subsets
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: order-service
spec:
  host: order-service
  subsets:
    - name: stable
      labels:
        version: v1.0.0
    - name: canary
      labels:
        version: v1.1.0
```

### Argo Rollouts Canary

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: order-service
spec:
  replicas: 10
  strategy:
    canary:
      steps:
        # Step 1: 10% traffic for 5 minutes
        - setWeight: 10
        - pause: {duration: 5m}

        # Step 2: 30% traffic, run analysis
        - setWeight: 30
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: order-service

        # Step 3: 50% traffic for 10 minutes
        - setWeight: 50
        - pause: {duration: 10m}

        # Step 4: Full rollout
        - setWeight: 100

      # Automatic rollback on failure
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1

  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
        - name: order-service
          image: order-service:v1.1.0

---
# Analysis template
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.99
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[5m]))
            /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))
```

---

## Rolling Deployment

### Concept

Gradually replace old pods with new ones, maintaining availability.

```
Initial:     [v1] [v1] [v1] [v1] [v1]

Step 1:      [v1] [v1] [v1] [v1] [v2]  ← One pod updated

Step 2:      [v1] [v1] [v1] [v2] [v2]  ← Two pods updated

Step 3:      [v1] [v1] [v2] [v2] [v2]

Step 4:      [v1] [v2] [v2] [v2] [v2]

Complete:    [v2] [v2] [v2] [v2] [v2]  ← All pods updated
```

### Kubernetes Rolling Update

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max pods over desired count
      maxUnavailable: 0  # Zero downtime
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
        - name: order-service
          image: order-service:v1.1.0
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
```

### Rollback Commands

```bash
# Check rollout status
kubectl rollout status deployment/order-service

# View history
kubectl rollout history deployment/order-service

# Rollback to previous version
kubectl rollout undo deployment/order-service

# Rollback to specific revision
kubectl rollout undo deployment/order-service --to-revision=2

# Pause rollout (for canary-like behavior)
kubectl rollout pause deployment/order-service

# Resume rollout
kubectl rollout resume deployment/order-service
```

---

## Feature Flags

### Types of Feature Flags

| Type | Purpose | Lifespan |
|------|---------|----------|
| **Release** | Decouple deploy from release | Days-weeks |
| **Experiment** | A/B testing | Weeks |
| **Ops** | Kill switches, maintenance | Permanent |
| **Permission** | User-based features | Permanent |

### Implementation

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional
import httpx

@dataclass
class FeatureFlag:
    name: str
    enabled: bool
    percentage: int = 100  # Rollout percentage
    conditions: Dict[str, Any] = None

class FeatureFlagClient:
    """Client for feature flag service (e.g., LaunchDarkly, Unleash)."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self._cache: Dict[str, FeatureFlag] = {}

    async def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        attributes: Dict[str, Any] = None
    ) -> bool:
        """Check if feature is enabled for user."""
        flag = await self._get_flag(flag_name)

        if not flag.enabled:
            return False

        # Percentage rollout
        if flag.percentage < 100:
            if user_id:
                # Consistent bucketing based on user ID
                bucket = hash(f"{flag_name}:{user_id}") % 100
                if bucket >= flag.percentage:
                    return False
            else:
                return False

        # Condition-based targeting
        if flag.conditions and attributes:
            return self._evaluate_conditions(flag.conditions, attributes)

        return True

    def _evaluate_conditions(self, conditions: Dict, attributes: Dict) -> bool:
        """Evaluate targeting conditions."""
        for key, expected in conditions.items():
            if attributes.get(key) != expected:
                return False
        return True

# Usage
flags = FeatureFlagClient(
    api_url="https://flags.example.com",
    api_key=os.getenv("FEATURE_FLAG_KEY")
)

@app.post("/orders")
async def create_order(request: CreateOrderRequest, user: User):
    # Release flag - new order flow
    if await flags.is_enabled("new_order_flow", user.id):
        return await new_order_service.create(request)
    return await order_service.create(request)

@app.get("/recommendations")
async def get_recommendations(user: User):
    # Experiment flag with attributes
    if await flags.is_enabled(
        "ml_recommendations",
        user.id,
        attributes={"plan": user.plan, "country": user.country}
    ):
        return await ml_recommendations.get(user.id)
    return await basic_recommendations.get(user.id)

@app.get("/products")
async def list_products():
    # Ops flag - circuit breaker
    if await flags.is_enabled("search_enabled"):
        return await search_service.query()
    return await fallback_product_list()
```

### Feature Flag Best Practices

```python
# 1. Always have defaults
async def get_feature(flag_name: str, default: bool = False) -> bool:
    try:
        return await flags.is_enabled(flag_name)
    except Exception:
        logger.warning(f"Flag service unavailable, using default for {flag_name}")
        return default

# 2. Clean up old flags
DEPRECATED_FLAGS = {
    "old_checkout": "2024-01-15",  # Remove after this date
    "legacy_api": "2024-02-01"
}

def check_deprecated_flags():
    for flag, deadline in DEPRECATED_FLAGS.items():
        if datetime.now().isoformat() > deadline:
            logger.warning(f"Flag {flag} should be removed (deadline: {deadline})")

# 3. Use typed flag configurations
@dataclass
class FeatureConfig:
    new_checkout: bool = False
    ml_recommendations: bool = False
    max_items_per_order: int = 100

async def get_config(user_id: str) -> FeatureConfig:
    return FeatureConfig(
        new_checkout=await flags.is_enabled("new_checkout", user_id),
        ml_recommendations=await flags.is_enabled("ml_recommendations", user_id),
        max_items_per_order=await flags.get_value("max_items_per_order", default=100)
    )
```

---

## GitOps

### ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: order-service
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/company/k8s-manifests
    targetRevision: HEAD
    path: services/order-service/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Flux Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: order-service
  namespace: flux-system
spec:
  interval: 10m
  path: ./services/order-service/overlays/production
  prune: true
  sourceRef:
    kind: GitRepository
    name: k8s-manifests
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: order-service
      namespace: production
  postBuild:
    substitute:
      IMAGE_TAG: ${GIT_COMMIT_SHA}
```

### GitOps Directory Structure

```
k8s-manifests/
├── services/
│   └── order-service/
│       ├── base/
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   ├── configmap.yaml
│       │   └── kustomization.yaml
│       └── overlays/
│           ├── staging/
│           │   ├── kustomization.yaml
│           │   └── replica-patch.yaml
│           └── production/
│               ├── kustomization.yaml
│               ├── replica-patch.yaml
│               └── resource-patch.yaml
└── infrastructure/
    ├── prometheus/
    ├── istio/
    └── cert-manager/
```

---

## Database Migrations

### Expand-Contract Pattern

Safe schema changes without downtime.

```
Phase 1: EXPAND
- Add new column (nullable or with default)
- Application writes to both old and new columns
- Backfill existing data

Phase 2: MIGRATE
- Application reads from new column
- Application writes to new column only

Phase 3: CONTRACT
- Remove old column
- Remove migration code
```

### Implementation Example

```python
# Phase 1: Expand - Add new column
"""
-- migration_001_add_email_verified.sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;

-- Backfill
UPDATE users SET email_verified = (verified_at IS NOT NULL);
"""

# Application code during expand phase
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    verified_at = Column(DateTime)  # Old column
    email_verified = Column(Boolean)  # New column

    def set_verified(self):
        # Write to both columns during expand
        self.verified_at = datetime.utcnow()
        self.email_verified = True

    @property
    def is_verified(self):
        # Read from new column if available, fall back to old
        if self.email_verified is not None:
            return self.email_verified
        return self.verified_at is not None

# Phase 2: Migrate - Use new column exclusively
class User(Base):
    email_verified = Column(Boolean, default=False)

    def set_verified(self):
        self.email_verified = True

    @property
    def is_verified(self):
        return self.email_verified

# Phase 3: Contract - Remove old column
"""
-- migration_002_remove_verified_at.sql
ALTER TABLE users DROP COLUMN verified_at;
"""
```

### Zero-Downtime Migration Script

```python
import asyncio
from datetime import datetime

class MigrationRunner:
    """Run migrations without downtime."""

    async def run_expand(self):
        """Phase 1: Add new structures."""
        await self.db.execute("""
            ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS status_v2 VARCHAR(50)
        """)

        # Backfill in batches
        batch_size = 1000
        while True:
            result = await self.db.execute("""
                UPDATE orders
                SET status_v2 = CASE status
                    WHEN 0 THEN 'pending'
                    WHEN 1 THEN 'confirmed'
                    WHEN 2 THEN 'shipped'
                    WHEN 3 THEN 'delivered'
                END
                WHERE status_v2 IS NULL
                LIMIT $1
                RETURNING id
            """, batch_size)

            if result.rowcount == 0:
                break

            await asyncio.sleep(0.1)  # Avoid overloading DB

    async def run_contract(self):
        """Phase 3: Remove old structures."""
        await self.db.execute("""
            ALTER TABLE orders DROP COLUMN status
        """)
        await self.db.execute("""
            ALTER TABLE orders RENAME COLUMN status_v2 TO status
        """)
```

---

## Deployment Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build and push image
        run: |
          docker build -t order-service:${{ github.sha }} .
          docker push registry.example.com/order-service:${{ github.sha }}

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Update staging manifest
        run: |
          cd k8s-manifests
          kustomize edit set image order-service=order-service:${{ github.sha }}
          git commit -am "Deploy ${{ github.sha }} to staging"
          git push

      - name: Wait for ArgoCD sync
        run: |
          argocd app wait order-service-staging --timeout 300

      - name: Run integration tests
        run: |
          ./scripts/integration-tests.sh staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production  # Requires approval
    steps:
      - name: Update production manifest
        run: |
          cd k8s-manifests
          kustomize edit set image order-service=order-service:${{ github.sha }}
          git commit -am "Deploy ${{ github.sha }} to production"
          git push

      - name: Monitor rollout
        run: |
          argocd app wait order-service-production --timeout 600
```

---

## Implementation Checklist

- [ ] **Strategy Selected**: Appropriate for service criticality
- [ ] **Health Checks**: Readiness and liveness probes configured
- [ ] **Rollback Plan**: Documented and tested
- [ ] **Feature Flags**: Critical features behind flags
- [ ] **Database Migrations**: Expand-contract pattern for schema changes
- [ ] **GitOps**: Declarative configs in version control
- [ ] **Monitoring**: Deployment metrics and alerts
- [ ] **Runbook**: Step-by-step deployment and rollback procedures
