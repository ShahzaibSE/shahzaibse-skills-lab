---
name: fastapi-uv-generator
description: |
  Production-grade FastAPI project generator using uv package manager.
  This skill should be used when users want to create new FastAPI projects,
  scaffold APIs, or set up Python web backends with modern tooling.
  Generates complete project structure with authentication, database,
  testing, Docker, and development tooling configured.
---

# FastAPI UV Generator

Generate production-ready FastAPI projects with uv package manager.

## What This Skill Does

- Scaffolds complete FastAPI project structure (feature-based or file-type)
- Configures uv with pyproject.toml and lock file
- Sets up authentication (JWT/OAuth2), database (SQLAlchemy/SQLModel), migrations (Alembic)
- Includes testing (pytest), linting (ruff), type checking (mypy)
- Generates Docker and docker-compose configuration
- Configures environment management with pydantic-settings

## What This Skill Does NOT Do

- Deploy projects to cloud providers
- Set up CI/CD pipelines (provides templates only)
- Configure external services (Auth0, AWS RDS, etc.)
- Manage existing projects (use for new projects only)

---

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Conversation** | Project name, features needed, database choice, auth requirements |
| **Skill References** | Patterns from `references/` (project structure, configs, best practices) |
| **User Guidelines** | Team conventions, naming standards, specific requirements |

Only ask user for THEIR specific requirements (domain expertise is in this skill).

---

## Required Clarifications

Ask these questions before generating:

### 1. Project Identity
```
What is your project name? (lowercase, hyphens allowed)
```

### 2. Project Structure
```
Which structure do you prefer?
- Feature-based (Recommended for larger projects)
- File-type based (Simpler, good for microservices)
```
See `references/project-structures.md` for details.

### 3. Database
```
Which database will you use?
- PostgreSQL (Recommended)
- SQLite (Development/testing)
- MySQL
- None (Stateless API)
```

### 4. Authentication
```
What authentication do you need?
- JWT with OAuth2 (Recommended)
- API Key only
- None (Internal service)
```

### 5. Optional Features
```
Which optional features do you need?
- [ ] Background tasks (Celery + Redis)
- [ ] WebSocket support
- [ ] GraphQL (Strawberry)
- [ ] Rate limiting
- [ ] Caching (Redis)
```

---

## Generation Workflow

```
Clarify → Structure → Core → Features → Config → Validate
```

### Step 1: Initialize Project

```bash
# Create project directory
mkdir {project_name}
cd {project_name}

# Initialize with uv
uv init --app

# Set Python version
uv python pin 3.12
```

### Step 2: Install Core Dependencies

```bash
# Core
uv add fastapi uvicorn[standard] pydantic pydantic-settings

# Database (if selected)
uv add sqlalchemy alembic asyncpg  # PostgreSQL
uv add sqlmodel alembic asyncpg    # Alternative: SQLModel

# Auth (if selected)
uv add python-jose[cryptography] passlib[bcrypt]

# Dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov httpx
uv add --dev ruff mypy pre-commit
```

See `references/dependencies.md` for complete dependency matrix.

### Step 3: Generate Project Structure

**Feature-based structure** (recommended):
```
{project_name}/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── {project_name}/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── dependencies.py
│       ├── features/
│       │   ├── __init__.py
│       │   ├── auth/
│       │   │   ├── __init__.py
│       │   │   ├── router.py
│       │   │   ├── schemas.py
│       │   │   ├── models.py
│       │   │   ├── service.py
│       │   │   └── dependencies.py
│       │   └── users/
│       │       ├── __init__.py
│       │       ├── router.py
│       │       ├── schemas.py
│       │       ├── models.py
│       │       └── service.py
│       └── core/
│           ├── __init__.py
│           ├── security.py
│           └── exceptions.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── features/
        ├── test_auth.py
        └── test_users.py
```

See `references/project-structures.md` for file-type structure.

### Step 4: Generate Core Files

Use templates from `assets/` directory:
- `assets/main.py.template` → Main application entry
- `assets/config.py.template` → Settings with pydantic-settings
- `assets/database.py.template` → Async SQLAlchemy setup
- `assets/docker/Dockerfile.template` → Multi-stage Docker build
- `assets/docker/docker-compose.yml.template` → Development compose

### Step 5: Configure Development Tools

Generate configuration in pyproject.toml:
```toml
[tool.ruff]
line-length = 88
target-version = "py312"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Step 6: Validate Generation

```bash
# Verify dependencies
uv sync

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/

# Run tests
uv run pytest

# Start development server
uv run uvicorn src.{project_name}.main:app --reload
```

---

## Key Patterns

### Configuration (pydantic-settings)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App
    app_name: str = "FastAPI App"
    debug: bool = False

    # Database
    database_url: str

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 30

settings = Settings()
```

### Async Database Session
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

### JWT Authentication
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    # Fetch user from database
    return user
```

See `references/patterns.md` for more patterns.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Blocking I/O in async routes | Use async database drivers, `run_in_executor` for sync |
| `allow_origins=["*"]` in CORS | Specify explicit allowed origins |
| Hardcoded secrets | Use environment variables via pydantic-settings |
| No input validation | Always use Pydantic models for request bodies |
| Missing error handling | Use exception handlers, return proper HTTP codes |
| SQLite in production | Use PostgreSQL or MySQL with connection pooling |
| No rate limiting | Implement slowapi or custom rate limiting |

See `references/anti-patterns.md` for detailed explanations.

---

## Output Checklist

Before completing generation, verify:

- [ ] `uv sync` succeeds without errors
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes (or has expected type ignores)
- [ ] `uv run pytest` discovers and runs tests
- [ ] `docker compose build` succeeds
- [ ] `.env.example` contains all required variables
- [ ] API docs accessible at `/docs` when running

---

## Official Documentation

For edge cases or updates not covered in this skill:

| Resource | URL | Use For |
|----------|-----|---------|
| FastAPI | https://fastapi.tiangolo.com | Endpoints, dependencies, middleware |
| uv | https://docs.astral.sh/uv | Package management, workspaces |
| Pydantic v2 | https://docs.pydantic.dev/latest | Validation, settings, serialization |
| SQLAlchemy 2.0 | https://docs.sqlalchemy.org/en/20 | ORM, async sessions, relationships |
| Alembic | https://alembic.sqlalchemy.org | Migration patterns, autogenerate |
| python-jose | https://python-jose.readthedocs.io | JWT encoding, algorithms |

Check these sources when:
- Implementing patterns not in `references/`
- Troubleshooting unexpected behavior
- Using features added after this skill was created

---

## Reference Files

| File | Contents |
|------|----------|
| `references/project-structures.md` | Detailed structure patterns |
| `references/dependencies.md` | Dependency matrix by feature |
| `references/patterns.md` | Code patterns (auth, DB, middleware) |
| `references/anti-patterns.md` | Common mistakes to avoid |
| `references/docker.md` | Docker best practices |
| `assets/` | Ready-to-use templates |
| `scripts/generate.py` | Generation automation script |
