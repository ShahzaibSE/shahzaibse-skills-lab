# Dependency Matrix

## Core Dependencies (Always Included)

```bash
uv add fastapi
uv add "uvicorn[standard]"
uv add pydantic
uv add pydantic-settings
```

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server with performance extras |
| `pydantic` | Data validation |
| `pydantic-settings` | Configuration management |

---

## Database Dependencies

### PostgreSQL (Recommended)

```bash
uv add sqlalchemy asyncpg alembic
# OR with SQLModel
uv add sqlmodel asyncpg alembic
```

| Package | Purpose |
|---------|---------|
| `sqlalchemy` | ORM, database toolkit |
| `sqlmodel` | SQLAlchemy + Pydantic integration |
| `asyncpg` | Async PostgreSQL driver |
| `alembic` | Database migrations |

### MySQL

```bash
uv add sqlalchemy aiomysql alembic
```

### SQLite (Dev/Testing only)

```bash
uv add sqlalchemy aiosqlite alembic
```

---

## Authentication Dependencies

### JWT + OAuth2

```bash
uv add "python-jose[cryptography]" "passlib[bcrypt]"
```

| Package | Purpose |
|---------|---------|
| `python-jose[cryptography]` | JWT token encoding/decoding |
| `passlib[bcrypt]` | Secure password hashing |

### API Key Only

No additional dependencies needed (built into FastAPI).

---

## Optional Feature Dependencies

### Background Tasks (Celery)

```bash
uv add celery redis
```

### Background Tasks (Lightweight)

```bash
uv add arq  # Uses Redis, lighter than Celery
```

### Caching

```bash
uv add redis
```

### Rate Limiting

```bash
uv add slowapi
```

### WebSocket

Built into FastAPI, no additional deps.

### GraphQL

```bash
uv add strawberry-graphql
```

### HTTP Client (for external APIs)

```bash
# Recommended: httpx (sync + async, requests-like API)
uv add httpx

# Alternative: aiohttp (async-only, more features for complex cases)
uv add aiohttp
```

| Package | Best For | Notes |
|---------|----------|-------|
| `httpx` | Most use cases | Sync + async, simple API, FastAPI testing |
| `aiohttp` | High-performance async | WebSocket client, streaming, connection pooling |

**Choose `aiohttp` when you need**:
- WebSocket client connections
- Advanced streaming responses
- Fine-grained connection pool control
- Maximum async performance

---

## Development Dependencies

```bash
# Testing
uv add --dev pytest pytest-asyncio pytest-cov httpx

# Linting & Formatting
uv add --dev ruff

# Type Checking
uv add --dev mypy

# Pre-commit Hooks
uv add --dev pre-commit

# Factory Boy (test fixtures)
uv add --dev factory-boy
```

| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `pytest-asyncio` | Async test support |
| `pytest-cov` | Coverage reporting |
| `httpx` | Async HTTP client for testing |
| `ruff` | Fast linter + formatter |
| `mypy` | Static type checking |
| `pre-commit` | Git hook management |
| `factory-boy` | Test data factories |

---

## Complete pyproject.toml Example

```toml
[project]
name = "my-api"
version = "0.1.0"
description = "Production FastAPI application"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "pre-commit>=4.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_api"]

[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src"]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "W",    # pycodestyle warnings
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "SIM",  # flake8-simplify
]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --cov=src --cov-report=term-missing"
```

---

## Dependency Version Strategy

| Strategy | When |
|----------|------|
| Pin exact (`==1.2.3`) | Production deployments, reproducibility |
| Pin minimum (`>=1.2.0`) | Development, allow compatible updates |
| Pin range (`>=1.2,<2.0`) | Balance stability and updates |

uv.lock handles exact versions automatically. Use minimum pins in pyproject.toml.
