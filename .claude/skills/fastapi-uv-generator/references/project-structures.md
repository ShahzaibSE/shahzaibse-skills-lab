# Project Structures

## Feature-Based Structure (Recommended)

Best for larger projects, monoliths, or projects expected to grow. Inspired by Netflix's Dispatch.

```
{project_name}/
├── pyproject.toml              # uv project config
├── uv.lock                     # Dependency lock file
├── .python-version             # Python version (3.12)
├── .env.example                # Environment template
├── .gitignore
├── .pre-commit-config.yaml
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── {project_name}/
│       ├── __init__.py
│       ├── main.py             # FastAPI app creation
│       ├── config.py           # Settings (pydantic-settings)
│       ├── database.py         # DB engine, session
│       ├── dependencies.py     # Shared dependencies
│       ├── features/
│       │   ├── __init__.py
│       │   ├── auth/
│       │   │   ├── __init__.py
│       │   │   ├── router.py       # API endpoints
│       │   │   ├── schemas.py      # Pydantic models
│       │   │   ├── models.py       # SQLAlchemy models
│       │   │   ├── service.py      # Business logic
│       │   │   ├── repository.py   # Data access
│       │   │   └── dependencies.py # Feature-specific deps
│       │   ├── users/
│       │   │   ├── __init__.py
│       │   │   ├── router.py
│       │   │   ├── schemas.py
│       │   │   ├── models.py
│       │   │   ├── service.py
│       │   │   └── repository.py
│       │   └── {feature_name}/
│       │       └── ...
│       └── core/
│           ├── __init__.py
│           ├── security.py     # JWT, password hashing
│           ├── exceptions.py   # Custom exceptions
│           └── middleware.py   # Custom middleware
└── tests/
    ├── __init__.py
    ├── conftest.py             # Fixtures
    ├── factories.py            # Test data factories
    └── features/
        ├── __init__.py
        ├── test_auth.py
        └── test_users.py
```

### Benefits
- All code for a domain in one place
- Easy to understand feature boundaries
- Scales well as project grows
- Easy to extract microservices later

### File Responsibilities

| File | Purpose |
|------|---------|
| `router.py` | Define API endpoints, request/response handling |
| `schemas.py` | Pydantic models for validation |
| `models.py` | SQLAlchemy/SQLModel ORM models |
| `service.py` | Business logic, orchestration |
| `repository.py` | Database queries, data access |
| `dependencies.py` | Feature-specific FastAPI dependencies |

---

## File-Type Structure

Better for microservices, smaller projects, or teams new to FastAPI.

```
{project_name}/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   └── ...
├── src/
│   └── {project_name}/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── dependencies.py
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   └── users.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   └── users.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── user.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   └── users.py
│       └── core/
│           ├── __init__.py
│           └── security.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    └── test_users.py
```

### Benefits
- Follows FastAPI docs structure
- Lower cognitive load for beginners
- Clear separation by file type

### When to Use
- Microservices with limited scope
- Projects with <5 main features
- Teams learning FastAPI

---

## API Versioning

Add versioning prefix to support API evolution:

```
src/{project_name}/
├── main.py
└── api/
    ├── __init__.py
    ├── v1/
    │   ├── __init__.py
    │   ├── router.py      # Aggregates all v1 routes
    │   └── endpoints/
    │       ├── auth.py
    │       └── users.py
    └── v2/
        ├── __init__.py
        └── ...
```

```python
# main.py
from fastapi import FastAPI
from src.project.api.v1.router import api_router as v1_router

app = FastAPI()
app.include_router(v1_router, prefix="/api/v1")
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Project directory | lowercase, hyphens | `my-api` |
| Python package | lowercase, underscores | `my_api` |
| Modules | lowercase, underscores | `user_service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_id` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_PAGE_SIZE` |
| Environment vars | UPPER_SNAKE_CASE | `DATABASE_URL` |
