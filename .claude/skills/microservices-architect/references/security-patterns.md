# Security Patterns

## Overview

Microservices security requires defense in depth: securing the perimeter, service-to-service communication, data, and implementing proper identity management.

---

## Zero Trust Architecture

### Core Principles

```
Traditional: Trust internal network, secure perimeter
Zero Trust:  Never trust, always verify
```

| Principle | Implementation |
|-----------|----------------|
| **Verify explicitly** | Authenticate and authorize every request |
| **Least privilege** | Minimal permissions for each service |
| **Assume breach** | Encrypt everything, segment networks |

### Zero Trust in Microservices

```
┌─────────────────────────────────────────────────────────────────┐
│                         ZERO TRUST                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐    mTLS     ┌─────────┐    mTLS     ┌─────────┐  │
│  │Service A│◄───────────►│Service B│◄───────────►│Service C│  │
│  └────┬────┘             └────┬────┘             └────┬────┘  │
│       │                       │                       │        │
│       ▼                       ▼                       ▼        │
│  ┌─────────┐             ┌─────────┐             ┌─────────┐  │
│  │ Authz   │             │ Authz   │             │ Authz   │  │
│  │ Policy  │             │ Policy  │             │ Policy  │  │
│  └─────────┘             └─────────┘             └─────────┘  │
│                                                                │
│  Every call: Identity verified → Policy checked → Encrypted   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Service Mesh Security (mTLS)

### Mutual TLS Overview

```
┌──────────┐                           ┌──────────┐
│ Service A│                           │ Service B│
│          │  1. Client Hello          │          │
│          │─────────────────────────▶ │          │
│          │                           │          │
│          │  2. Server Cert           │          │
│          │◀───────────────────────── │          │
│          │                           │          │
│          │  3. Client Cert           │          │
│          │─────────────────────────▶ │          │
│          │                           │          │
│          │  4. Encrypted Traffic     │          │
│          │◀─────────────────────────▶│          │
└──────────┘                           └──────────┘
```

### Istio mTLS Configuration

```yaml
# PeerAuthentication - Require mTLS for all services
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT  # STRICT, PERMISSIVE, or DISABLE

---
# DestinationRule - Client-side mTLS
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: default
  namespace: production
spec:
  host: "*.production.svc.cluster.local"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL

---
# AuthorizationPolicy - Service-level access control
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: order-service-policy
  namespace: production
spec:
  selector:
    matchLabels:
      app: order-service
  action: ALLOW
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/production/sa/api-gateway"
              - "cluster.local/ns/production/sa/payment-service"
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/orders*"]
```

### Certificate Management with cert-manager

```yaml
# ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx

---
# Certificate for service
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: order-service-cert
  namespace: production
spec:
  secretName: order-service-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - order-service.example.com
    - order-service.production.svc.cluster.local
```

---

## Authentication & Authorization

### OAuth 2.0 / OpenID Connect Flow

```
┌──────┐     ┌─────────┐     ┌─────────────┐     ┌─────────┐
│Client│     │API Gate │     │Auth Server  │     │Service  │
└──┬───┘     └────┬────┘     │(Keycloak)   │     └────┬────┘
   │              │          └──────┬──────┘          │
   │ 1. Login     │                 │                 │
   │─────────────────────────────▶  │                 │
   │              │                 │                 │
   │ 2. Auth Code │                 │                 │
   │◀─────────────────────────────  │                 │
   │              │                 │                 │
   │ 3. Exchange Code              │                 │
   │─────────────────────────────▶  │                 │
   │              │                 │                 │
   │ 4. Access Token + ID Token     │                 │
   │◀─────────────────────────────  │                 │
   │              │                 │                 │
   │ 5. API Request + Token        │                 │
   │─────────────▶│                 │                 │
   │              │ 6. Validate     │                 │
   │              │────────────────▶│                 │
   │              │◀────────────────│                 │
   │              │                 │                 │
   │              │ 7. Forward + User Context        │
   │              │────────────────────────────────▶ │
   │              │◀────────────────────────────────  │
   │ 8. Response  │                 │                 │
   │◀─────────────│                 │                 │
```

### JWT Validation

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from typing import List, Optional
import httpx

security = HTTPBearer()

class TokenPayload(BaseModel):
    sub: str  # Subject (user ID)
    exp: int  # Expiration
    iat: int  # Issued at
    iss: str  # Issuer
    aud: str  # Audience
    roles: List[str] = []
    permissions: List[str] = []

class JWTValidator:
    def __init__(self, jwks_url: str, audience: str, issuer: str):
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self._jwks_cache = None

    async def _get_jwks(self):
        """Fetch and cache JWKS from auth server."""
        if not self._jwks_cache:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                self._jwks_cache = response.json()
        return self._jwks_cache

    async def validate(self, token: str) -> TokenPayload:
        """Validate JWT and return payload."""
        try:
            jwks = await self._get_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer
            )
            return TokenPayload(**payload)
        except JWTError as e:
            raise HTTPException(status_code=401, detail=str(e))

# Dependency
jwt_validator = JWTValidator(
    jwks_url="https://auth.example.com/.well-known/jwks.json",
    audience="order-service",
    issuer="https://auth.example.com"
)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenPayload:
    return await jwt_validator.validate(credentials.credentials)

# Usage
@app.get("/orders")
async def list_orders(user: TokenPayload = Depends(get_current_user)):
    if "orders:read" not in user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return await order_service.list_for_user(user.sub)
```

### Role-Based Access Control (RBAC)

```python
from functools import wraps
from typing import List

def require_roles(*required_roles: str):
    """Decorator to require specific roles."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: TokenPayload, **kwargs):
            if not any(role in user.roles for role in required_roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"Requires one of roles: {required_roles}"
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator

def require_permissions(*required_perms: str):
    """Decorator to require specific permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: TokenPayload, **kwargs):
            missing = set(required_perms) - set(user.permissions)
            if missing:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing permissions: {missing}"
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator

# Usage
@app.delete("/orders/{order_id}")
@require_roles("admin", "order_manager")
async def delete_order(order_id: str, user: TokenPayload = Depends(get_current_user)):
    return await order_service.delete(order_id)

@app.post("/orders/{order_id}/refund")
@require_permissions("orders:write", "payments:refund")
async def refund_order(order_id: str, user: TokenPayload = Depends(get_current_user)):
    return await order_service.refund(order_id)
```

### Service-to-Service Authentication

```python
from datetime import datetime, timedelta
import jwt

class ServiceTokenManager:
    """Manage service-to-service authentication tokens."""

    def __init__(self, service_name: str, private_key: str):
        self.service_name = service_name
        self.private_key = private_key

    def create_token(self, target_service: str, ttl_seconds: int = 300) -> str:
        """Create short-lived token for service call."""
        now = datetime.utcnow()
        payload = {
            "iss": self.service_name,
            "sub": self.service_name,
            "aud": target_service,
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def call_service(self, url: str, target_service: str, **kwargs):
        """Make authenticated call to another service."""
        token = self.create_token(target_service)
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient() as client:
            return await client.request(url=url, headers=headers, **kwargs)
```

---

## Secrets Management

### HashiCorp Vault Integration

```python
import hvac
from functools import lru_cache

class VaultClient:
    def __init__(self, url: str, token: str = None, role: str = None):
        self.client = hvac.Client(url=url)

        if token:
            self.client.token = token
        elif role:
            # Kubernetes auth
            with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
                jwt = f.read()
            self.client.auth.kubernetes.login(role=role, jwt=jwt)

    @lru_cache(maxsize=100)
    def get_secret(self, path: str) -> dict:
        """Retrieve secret from Vault."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']

    def get_database_credentials(self) -> tuple:
        """Get dynamic database credentials."""
        creds = self.client.secrets.database.generate_credentials(name="order-db")
        return creds['data']['username'], creds['data']['password']

# Usage
vault = VaultClient(
    url="https://vault.example.com",
    role="order-service"
)

# Static secrets
api_keys = vault.get_secret("api-keys/payment-provider")

# Dynamic database credentials (auto-rotated)
db_user, db_pass = vault.get_database_credentials()
```

### Kubernetes Secrets with External Secrets Operator

```yaml
# ExternalSecret - Sync from Vault to K8s Secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: order-service-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: order-service-secrets
    creationPolicy: Owner
  data:
    - secretKey: database-url
      remoteRef:
        key: production/order-service
        property: database_url
    - secretKey: api-key
      remoteRef:
        key: production/order-service
        property: api_key

---
# Use in deployment
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: order-service
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: order-service-secrets
                  key: database-url
```

### Secret Rotation Pattern

```python
import asyncio
from datetime import datetime, timedelta

class RotatingSecret:
    """Automatically rotating secret with grace period."""

    def __init__(self, vault: VaultClient, secret_path: str, rotation_interval: timedelta):
        self.vault = vault
        self.secret_path = secret_path
        self.rotation_interval = rotation_interval
        self.current_secret = None
        self.previous_secret = None
        self.last_rotation = None

    async def start_rotation_loop(self):
        """Background task to rotate secrets."""
        while True:
            await self._rotate()
            await asyncio.sleep(self.rotation_interval.total_seconds())

    async def _rotate(self):
        """Rotate to new secret, keeping old one valid."""
        new_secret = self.vault.get_secret(self.secret_path)
        self.previous_secret = self.current_secret
        self.current_secret = new_secret
        self.last_rotation = datetime.utcnow()

    def validate(self, provided_secret: str) -> bool:
        """Validate against current or previous secret."""
        return (
            provided_secret == self.current_secret or
            (self.previous_secret and provided_secret == self.previous_secret)
        )
```

---

## API Security

### Input Validation

```python
from pydantic import BaseModel, validator, constr, EmailStr
from typing import List
import re

class CreateOrderRequest(BaseModel):
    customer_id: constr(min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    items: List[OrderItem]
    shipping_address: Address

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('At least one item required')
        if len(v) > 100:
            raise ValueError('Maximum 100 items per order')
        return v

class OrderItem(BaseModel):
    product_id: constr(min_length=1, max_length=50)
    quantity: int

    @validator('quantity')
    def validate_quantity(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('Quantity must be between 1 and 1000')
        return v

class Address(BaseModel):
    street: constr(min_length=1, max_length=200)
    city: constr(min_length=1, max_length=100)
    postal_code: constr(pattern=r'^\d{5}(-\d{4})?$')
    country: constr(min_length=2, max_length=2)

    @validator('street', 'city')
    def sanitize_text(cls, v):
        # Remove potential XSS
        return re.sub(r'[<>"\']', '', v)
```

### SQL Injection Prevention

```python
# ANTI-PATTERN: String concatenation
async def get_user_bad(user_id: str):
    query = f"SELECT * FROM users WHERE id = '{user_id}'"  # VULNERABLE
    return await db.fetch(query)

# CORRECT: Parameterized queries
async def get_user_good(user_id: str):
    query = "SELECT * FROM users WHERE id = $1"
    return await db.fetch(query, user_id)

# CORRECT: ORM with parameterization
async def get_user_orm(user_id: str):
    return await User.get(id=user_id)
```

### Rate Limiting per User/API Key

```python
from collections import defaultdict
import time

class PerUserRateLimiter:
    """Rate limit per user with different tiers."""

    LIMITS = {
        "free": {"requests": 100, "window": 3600},      # 100/hour
        "pro": {"requests": 1000, "window": 3600},      # 1000/hour
        "enterprise": {"requests": 10000, "window": 3600}  # 10000/hour
    }

    def __init__(self):
        self.requests = defaultdict(list)

    def is_allowed(self, user_id: str, tier: str = "free") -> bool:
        limit = self.LIMITS[tier]
        now = time.time()
        window_start = now - limit["window"]

        # Clean old requests
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > window_start
        ]

        if len(self.requests[user_id]) >= limit["requests"]:
            return False

        self.requests[user_id].append(now)
        return True

    def get_remaining(self, user_id: str, tier: str = "free") -> int:
        limit = self.LIMITS[tier]
        return max(0, limit["requests"] - len(self.requests[user_id]))
```

---

## Network Policies

### Kubernetes Network Policy

```yaml
# Default deny all ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress

---
# Allow specific service communication
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: order-service-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: order-service
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from API gateway
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8080
    # Allow from payment service (callbacks)
    - from:
        - podSelector:
            matchLabels:
              app: payment-service
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Allow to database
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    # Allow to other services
    - to:
        - podSelector:
            matchLabels:
              app: inventory-service
        - podSelector:
            matchLabels:
              app: payment-service
      ports:
        - protocol: TCP
          port: 8080
    # Allow DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

---

## Security Headers

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

        # HTTPS enforcement
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response

app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
```

---

## Compliance Patterns

### Audit Logging

```python
from datetime import datetime
from pydantic import BaseModel
import json

class AuditLog(BaseModel):
    timestamp: datetime
    actor_id: str
    actor_type: str  # user, service, system
    action: str
    resource_type: str
    resource_id: str
    outcome: str  # success, failure
    metadata: dict = {}

class AuditLogger:
    def __init__(self, storage):
        self.storage = storage

    async def log(self, log: AuditLog):
        """Store audit log (immutable, append-only)."""
        await self.storage.append(log.dict())

    async def log_action(
        self,
        actor: TokenPayload,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str = "success",
        **metadata
    ):
        await self.log(AuditLog(
            timestamp=datetime.utcnow(),
            actor_id=actor.sub,
            actor_type="user" if actor.sub.startswith("user_") else "service",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            metadata=metadata
        ))

# Usage
@app.delete("/orders/{order_id}")
async def delete_order(
    order_id: str,
    user: TokenPayload = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger)
):
    try:
        await order_service.delete(order_id)
        await audit.log_action(
            user, "delete", "order", order_id,
            reason="customer_request"
        )
    except Exception as e:
        await audit.log_action(
            user, "delete", "order", order_id,
            outcome="failure", error=str(e)
        )
        raise
```

### Data Encryption at Rest

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class FieldEncryption:
    """Encrypt sensitive fields before storage."""

    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()

# Usage with ORM
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String)  # Not sensitive
    _ssn_encrypted = Column("ssn", String)  # Sensitive, encrypted

    @property
    def ssn(self):
        return encryption.decrypt(self._ssn_encrypted)

    @ssn.setter
    def ssn(self, value):
        self._ssn_encrypted = encryption.encrypt(value)
```

---

## Implementation Checklist

- [ ] **mTLS**: Service-to-service encryption enabled
- [ ] **Authentication**: JWT/OAuth2 at API gateway
- [ ] **Authorization**: RBAC/ABAC policies defined
- [ ] **Secrets Management**: Vault or cloud-native solution
- [ ] **Input Validation**: All inputs validated and sanitized
- [ ] **Network Policies**: Default deny, explicit allow
- [ ] **Security Headers**: HSTS, CSP, X-Frame-Options
- [ ] **Audit Logging**: All sensitive actions logged
- [ ] **Encryption at Rest**: Sensitive data encrypted
- [ ] **Vulnerability Scanning**: Container and dependency scanning
