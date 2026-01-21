#!/usr/bin/env python3
"""
FastAPI Project Generator

Generates a production-ready FastAPI project structure with uv package manager.

Usage:
    python generate.py <project_name> [options]

Options:
    --structure     feature|filetype (default: feature)
    --database      postgres|mysql|sqlite|none (default: postgres)
    --auth          jwt|apikey|none (default: jwt)
    --background    Include background task support (Celery)
    --websocket     Include WebSocket support
    --graphql       Include GraphQL support (Strawberry)
    --ratelimit     Include rate limiting
    --cache         Include Redis caching

Example:
    python generate.py my-api --database postgres --auth jwt
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class ProjectConfig(NamedTuple):
    name: str
    package_name: str
    structure: str
    database: str
    auth: str
    background: bool
    websocket: bool
    graphql: bool
    ratelimit: bool
    cache: bool


def to_package_name(project_name: str) -> str:
    """Convert project name to valid Python package name."""
    return re.sub(r"[^a-z0-9]", "_", project_name.lower()).strip("_")


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a shell command."""
    print(f"  Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def create_directory_structure(config: ProjectConfig, base_path: Path) -> None:
    """Create the project directory structure."""
    print("\n📁 Creating directory structure...")

    pkg = config.package_name

    if config.structure == "feature":
        dirs = [
            f"src/{pkg}",
            f"src/{pkg}/features/auth",
            f"src/{pkg}/features/users",
            f"src/{pkg}/core",
            "tests/features",
            "alembic/versions",
        ]
    else:
        dirs = [
            f"src/{pkg}",
            f"src/{pkg}/routers",
            f"src/{pkg}/schemas",
            f"src/{pkg}/models",
            f"src/{pkg}/services",
            f"src/{pkg}/core",
            "tests",
            "alembic/versions",
        ]

    for dir_path in dirs:
        (base_path / dir_path).mkdir(parents=True, exist_ok=True)
        # Create __init__.py files
        if dir_path.startswith("src") or dir_path.startswith("tests"):
            init_file = base_path / dir_path / "__init__.py"
            init_file.touch()

    print("  ✓ Directory structure created")


def initialize_uv_project(config: ProjectConfig, base_path: Path) -> None:
    """Initialize the project with uv."""
    print("\n📦 Initializing uv project...")

    # Initialize with uv
    run_command(["uv", "init", "--app", "--no-readme"], cwd=base_path)

    # Pin Python version
    run_command(["uv", "python", "pin", "3.12"], cwd=base_path)

    print("  ✓ uv project initialized")


def install_dependencies(config: ProjectConfig, base_path: Path) -> None:
    """Install project dependencies."""
    print("\n📥 Installing dependencies...")

    # Core dependencies
    core_deps = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pydantic-settings",
    ]
    run_command(["uv", "add"] + core_deps, cwd=base_path)

    # Database dependencies
    if config.database == "postgres":
        run_command(["uv", "add", "sqlalchemy", "asyncpg", "alembic"], cwd=base_path)
    elif config.database == "mysql":
        run_command(["uv", "add", "sqlalchemy", "aiomysql", "alembic"], cwd=base_path)
    elif config.database == "sqlite":
        run_command(["uv", "add", "sqlalchemy", "aiosqlite", "alembic"], cwd=base_path)

    # Auth dependencies
    if config.auth == "jwt":
        run_command(
            ["uv", "add", "python-jose[cryptography]", "passlib[bcrypt]"], cwd=base_path
        )

    # Optional features
    if config.background:
        run_command(["uv", "add", "celery", "redis"], cwd=base_path)

    if config.ratelimit:
        run_command(["uv", "add", "slowapi"], cwd=base_path)

    if config.cache or config.background:
        run_command(["uv", "add", "redis"], cwd=base_path)

    if config.graphql:
        run_command(["uv", "add", "strawberry-graphql"], cwd=base_path)

    # Development dependencies
    dev_deps = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "httpx",
        "ruff",
        "mypy",
        "pre-commit",
    ]
    run_command(["uv", "add", "--dev"] + dev_deps, cwd=base_path)

    print("  ✓ Dependencies installed")


def create_config_files(config: ProjectConfig, base_path: Path) -> None:
    """Create configuration files."""
    print("\n⚙️  Creating configuration files...")

    pkg = config.package_name

    # .env.example
    env_content = f"""# Application
APP_NAME={config.name}
DEBUG=false
SECRET_KEY=your-secret-key-min-32-chars-change-this

# Database
{"DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/" + pkg if config.database == "postgres" else ""}
{"DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/" + pkg if config.database == "mysql" else ""}
{"DATABASE_URL=sqlite+aiosqlite:///./app.db" if config.database == "sqlite" else ""}

# Auth
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000

{"# Redis" if config.cache or config.background else ""}
{"REDIS_URL=redis://localhost:6379/0" if config.cache or config.background else ""}
"""
    (base_path / ".env.example").write_text(env_content.strip() + "\n")

    # .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
.eggs/
*.egg-info/
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.*
!.env.example

# Build
dist/
build/

# Misc
.DS_Store
*.log
"""
    (base_path / ".gitignore").write_text(gitignore_content)

    # .pre-commit-config.yaml
    precommit_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic
          - types-passlib
"""
    (base_path / ".pre-commit-config.yaml").write_text(precommit_content)

    print("  ✓ Configuration files created")


def create_source_files(config: ProjectConfig, base_path: Path) -> None:
    """Create main source files."""
    print("\n📝 Creating source files...")

    pkg = config.package_name
    src_path = base_path / "src" / pkg

    # config.py
    config_content = f'''"""Application configuration."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "{config.name}"
    debug: bool = False

    {"# Database" if config.database != "none" else ""}
    {"database_url: str" if config.database != "none" else ""}

    {"# Authentication" if config.auth != "none" else ""}
    {"secret_key: str" if config.auth != "none" else ""}
    {"algorithm: str = 'HS256'" if config.auth == "jwt" else ""}
    {"access_token_expire_minutes: int = 30" if config.auth == "jwt" else ""}

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
'''
    (src_path / "config.py").write_text(config_content)

    # database.py (if database is enabled)
    if config.database != "none":
        db_content = f'''"""Database configuration and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
'''
        (src_path / "database.py").write_text(db_content)

    # main.py
    main_content = f'''"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
{"from .database import engine" if config.database != "none" else ""}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    {"await engine.dispose()" if config.database != "none" else "pass"}


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {{"status": "healthy"}}

    # Include routers here
    # app.include_router(auth_router, prefix="/auth", tags=["auth"])

    return app


app = create_app()
'''
    (src_path / "main.py").write_text(main_content)

    print("  ✓ Source files created")


def create_docker_files(config: ProjectConfig, base_path: Path) -> None:
    """Create Docker configuration files."""
    print("\n🐳 Creating Docker files...")

    pkg = config.package_name

    # Dockerfile
    dockerfile_content = f'''# syntax=docker/dockerfile:1

# Build stage
FROM python:3.12-slim as builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \\
    UV_LINK_MODE=copy \\
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \\
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \\
    uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim as runtime

RUN groupadd --gid 1000 app && \\
    useradd --uid 1000 --gid 1000 --shell /bin/bash app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000
CMD ["uvicorn", "src.{pkg}.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
    (base_path / "Dockerfile").write_text(dockerfile_content)

    # docker-compose.yml
    compose_services = f"""services:
  app:
    build:
      context: .
      target: runtime
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
      - SECRET_KEY=${{SECRET_KEY:-dev-secret-key-change-in-prod}}
      - ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
"""

    if config.database == "postgres":
        compose_services += f"""      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/{pkg}
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn src.{pkg}.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./src:/app/src:ro

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {pkg}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
"""
    else:
        compose_services += f"""    command: uvicorn src.{pkg}.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./src:/app/src:ro
"""

    (base_path / "docker-compose.yml").write_text(compose_services)

    # .dockerignore
    dockerignore_content = """.git
.gitignore
__pycache__
*.py[cod]
.venv
venv/
.pytest_cache/
.coverage
htmlcov/
.idea/
.vscode/
*.md
Dockerfile*
docker-compose*
.env
.env.*
!.env.example
"""
    (base_path / ".dockerignore").write_text(dockerignore_content)

    print("  ✓ Docker files created")


def create_test_files(config: ProjectConfig, base_path: Path) -> None:
    """Create test configuration and example tests."""
    print("\n🧪 Creating test files...")

    pkg = config.package_name

    # conftest.py
    conftest_content = f'''"""Pytest configuration and fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.{pkg}.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
'''
    (base_path / "tests" / "conftest.py").write_text(conftest_content)

    # test_health.py
    test_content = '''"""Health check endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Test the health check endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
'''
    (base_path / "tests" / "test_health.py").write_text(test_content)

    print("  ✓ Test files created")


def print_next_steps(config: ProjectConfig) -> None:
    """Print next steps for the user."""
    print("\n" + "=" * 60)
    print("✅ Project generated successfully!")
    print("=" * 60)
    print(f"\n📂 Project: {config.name}")
    print(f"📦 Package: {config.package_name}")
    print("\n🚀 Next steps:")
    print(f"   cd {config.name}")
    print("   cp .env.example .env  # Configure environment")
    print("   uv sync              # Install dependencies")
    print("   uv run pytest        # Run tests")
    print("   uv run uvicorn src.{}.main:app --reload".format(config.package_name))
    print("\n🐳 Or with Docker:")
    print("   docker compose up -d")
    print("\n📚 API docs will be available at: http://localhost:8000/docs")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a production-ready FastAPI project"
    )
    parser.add_argument("name", help="Project name")
    parser.add_argument(
        "--structure",
        choices=["feature", "filetype"],
        default="feature",
        help="Project structure type",
    )
    parser.add_argument(
        "--database",
        choices=["postgres", "mysql", "sqlite", "none"],
        default="postgres",
        help="Database backend",
    )
    parser.add_argument(
        "--auth",
        choices=["jwt", "apikey", "none"],
        default="jwt",
        help="Authentication type",
    )
    parser.add_argument(
        "--background", action="store_true", help="Include Celery background tasks"
    )
    parser.add_argument(
        "--websocket", action="store_true", help="Include WebSocket support"
    )
    parser.add_argument(
        "--graphql", action="store_true", help="Include GraphQL (Strawberry)"
    )
    parser.add_argument(
        "--ratelimit", action="store_true", help="Include rate limiting"
    )
    parser.add_argument("--cache", action="store_true", help="Include Redis caching")

    args = parser.parse_args()

    config = ProjectConfig(
        name=args.name,
        package_name=to_package_name(args.name),
        structure=args.structure,
        database=args.database,
        auth=args.auth,
        background=args.background,
        websocket=args.websocket,
        graphql=args.graphql,
        ratelimit=args.ratelimit,
        cache=args.cache,
    )

    base_path = Path.cwd() / config.name

    if base_path.exists():
        print(f"❌ Error: Directory '{config.name}' already exists")
        sys.exit(1)

    base_path.mkdir()

    try:
        create_directory_structure(config, base_path)
        initialize_uv_project(config, base_path)
        install_dependencies(config, base_path)
        create_config_files(config, base_path)
        create_source_files(config, base_path)
        create_docker_files(config, base_path)
        create_test_files(config, base_path)
        print_next_steps(config)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: Command failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
