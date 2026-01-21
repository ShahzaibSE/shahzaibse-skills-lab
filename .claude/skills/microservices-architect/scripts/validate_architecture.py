#!/usr/bin/env python3
"""
Microservices Architecture Validation Script

Validates architecture designs against best practices and common anti-patterns.
Can be used standalone or integrated into CI/CD pipelines.

Usage:
    python validate_architecture.py architecture.yaml
    python validate_architecture.py --json architecture.yaml
    python validate_architecture.py --strict architecture.yaml
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Severity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    category: str
    severity: Severity
    message: str
    location: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Aggregated validation results."""
    issues: list[ValidationIssue] = field(default_factory=list)
    services_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.INFO)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "summary": {
                "services": self.services_count,
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "issues": [i.to_dict() for i in self.issues],
        }


class ArchitectureValidator:
    """Validates microservices architecture against best practices."""

    def __init__(self, architecture: dict):
        self.arch = architecture
        self.result = ValidationResult()
        self.services = architecture.get("services", {})
        self.result.services_count = len(self.services)

    def validate(self) -> ValidationResult:
        """Run all validation checks."""
        self._validate_service_boundaries()
        self._validate_communication_patterns()
        self._validate_data_ownership()
        self._validate_resilience()
        self._validate_observability()
        self._validate_security()
        self._validate_anti_patterns()
        return self.result

    def _add_issue(
        self,
        category: str,
        severity: Severity,
        message: str,
        location: str = "",
        suggestion: str = "",
    ):
        self.result.issues.append(
            ValidationIssue(category, severity, message, location, suggestion)
        )

    # =========================================================================
    # Service Boundaries Validation
    # =========================================================================

    def _validate_service_boundaries(self):
        """Validate service boundaries and sizing."""
        for name, service in self.services.items():
            # Check for god service
            capabilities = service.get("capabilities", [])
            if len(capabilities) > 5:
                self._add_issue(
                    "service-boundaries",
                    Severity.WARNING,
                    f"Service '{name}' has {len(capabilities)} capabilities. "
                    "Consider splitting into smaller services.",
                    f"services.{name}",
                    "A service should focus on a single bounded context.",
                )

            # Check for nano service
            endpoints = service.get("endpoints", [])
            if len(endpoints) == 1 and len(capabilities) == 1:
                self._add_issue(
                    "service-boundaries",
                    Severity.INFO,
                    f"Service '{name}' has only 1 endpoint. "
                    "Evaluate if it should be merged with another service.",
                    f"services.{name}",
                    "Avoid nanoservices with excessive operational overhead.",
                )

            # Check for missing bounded context
            if not service.get("bounded_context"):
                self._add_issue(
                    "service-boundaries",
                    Severity.WARNING,
                    f"Service '{name}' has no defined bounded context.",
                    f"services.{name}",
                    "Define bounded context for clear domain ownership.",
                )

    # =========================================================================
    # Communication Patterns Validation
    # =========================================================================

    def _validate_communication_patterns(self):
        """Validate service communication patterns."""
        for name, service in self.services.items():
            dependencies = service.get("dependencies", [])

            # Check for synchronous chains
            sync_deps = [d for d in dependencies if d.get("type") == "sync"]
            if len(sync_deps) > 3:
                self._add_issue(
                    "communication",
                    Severity.WARNING,
                    f"Service '{name}' has {len(sync_deps)} synchronous dependencies. "
                    "Long sync chains increase latency and reduce availability.",
                    f"services.{name}.dependencies",
                    "Consider using async communication for non-critical paths.",
                )

            # Check for missing communication type
            for dep in dependencies:
                if "type" not in dep:
                    self._add_issue(
                        "communication",
                        Severity.ERROR,
                        f"Dependency '{dep.get('service', 'unknown')}' in '{name}' "
                        "has no communication type defined.",
                        f"services.{name}.dependencies",
                        "Specify 'sync' or 'async' for each dependency.",
                    )

            # Check for event publishing without consumers
            events_published = service.get("events_published", [])
            for event in events_published:
                consumers = self._find_event_consumers(event)
                if not consumers:
                    self._add_issue(
                        "communication",
                        Severity.INFO,
                        f"Event '{event}' published by '{name}' has no consumers.",
                        f"services.{name}.events_published",
                        "Ensure events are consumed or remove if unused.",
                    )

    def _find_event_consumers(self, event_name: str) -> list[str]:
        """Find services that consume a given event."""
        consumers = []
        for name, service in self.services.items():
            if event_name in service.get("events_consumed", []):
                consumers.append(name)
        return consumers

    # =========================================================================
    # Data Ownership Validation
    # =========================================================================

    def _validate_data_ownership(self):
        """Validate data ownership patterns."""
        databases = {}

        for name, service in self.services.items():
            db = service.get("database")
            if db:
                db_name = db.get("name", "")
                if db_name:
                    if db_name in databases:
                        # Shared database detected
                        self._add_issue(
                            "data-ownership",
                            Severity.ERROR,
                            f"Database '{db_name}' is shared between '{databases[db_name]}' "
                            f"and '{name}'. Each service should own its database.",
                            f"services.{name}.database",
                            "Extract shared data to separate service or use events.",
                        )
                    else:
                        databases[db_name] = name

            # Check for missing data ownership
            if not service.get("data_entities"):
                self._add_issue(
                    "data-ownership",
                    Severity.WARNING,
                    f"Service '{name}' has no defined data entities.",
                    f"services.{name}",
                    "Document which data entities this service owns.",
                )

    # =========================================================================
    # Resilience Validation
    # =========================================================================

    def _validate_resilience(self):
        """Validate resilience patterns."""
        for name, service in self.services.items():
            resilience = service.get("resilience", {})
            dependencies = service.get("dependencies", [])

            # Check for missing circuit breakers on sync dependencies
            circuit_breakers = resilience.get("circuit_breakers", [])
            sync_deps = [d.get("service") for d in dependencies if d.get("type") == "sync"]

            for dep in sync_deps:
                if dep and dep not in circuit_breakers:
                    self._add_issue(
                        "resilience",
                        Severity.WARNING,
                        f"Service '{name}' has sync dependency on '{dep}' "
                        "without circuit breaker configured.",
                        f"services.{name}.resilience.circuit_breakers",
                        "Add circuit breaker for all synchronous dependencies.",
                    )

            # Check for missing timeouts
            if dependencies and not resilience.get("timeouts"):
                self._add_issue(
                    "resilience",
                    Severity.WARNING,
                    f"Service '{name}' has dependencies but no timeouts configured.",
                    f"services.{name}.resilience.timeouts",
                    "Configure timeouts for all external calls.",
                )

            # Check for missing retry configuration
            if dependencies and not resilience.get("retry"):
                self._add_issue(
                    "resilience",
                    Severity.INFO,
                    f"Service '{name}' has no retry configuration.",
                    f"services.{name}.resilience.retry",
                    "Consider adding retry with exponential backoff.",
                )

            # Check for missing health checks
            if not service.get("health_checks"):
                self._add_issue(
                    "resilience",
                    Severity.ERROR,
                    f"Service '{name}' has no health checks defined.",
                    f"services.{name}.health_checks",
                    "Implement liveness and readiness probes.",
                )

    # =========================================================================
    # Observability Validation
    # =========================================================================

    def _validate_observability(self):
        """Validate observability configuration."""
        for name, service in self.services.items():
            observability = service.get("observability", {})

            # Check for tracing
            if not observability.get("tracing"):
                self._add_issue(
                    "observability",
                    Severity.WARNING,
                    f"Service '{name}' has no distributed tracing configured.",
                    f"services.{name}.observability.tracing",
                    "Enable OpenTelemetry or similar tracing solution.",
                )

            # Check for metrics
            if not observability.get("metrics"):
                self._add_issue(
                    "observability",
                    Severity.WARNING,
                    f"Service '{name}' has no metrics configured.",
                    f"services.{name}.observability.metrics",
                    "Expose Prometheus metrics for RED/USE monitoring.",
                )

            # Check for logging
            if not observability.get("logging"):
                self._add_issue(
                    "observability",
                    Severity.INFO,
                    f"Service '{name}' has no structured logging configured.",
                    f"services.{name}.observability.logging",
                    "Use structured JSON logging with trace correlation.",
                )

            # Check for SLOs
            if not service.get("slos"):
                self._add_issue(
                    "observability",
                    Severity.INFO,
                    f"Service '{name}' has no SLOs defined.",
                    f"services.{name}.slos",
                    "Define availability and latency SLOs.",
                )

    # =========================================================================
    # Security Validation
    # =========================================================================

    def _validate_security(self):
        """Validate security configuration."""
        for name, service in self.services.items():
            security = service.get("security", {})

            # Check for authentication
            if not security.get("authentication"):
                self._add_issue(
                    "security",
                    Severity.ERROR,
                    f"Service '{name}' has no authentication configured.",
                    f"services.{name}.security.authentication",
                    "Implement JWT/OAuth2 or mTLS authentication.",
                )

            # Check for authorization
            if not security.get("authorization"):
                self._add_issue(
                    "security",
                    Severity.WARNING,
                    f"Service '{name}' has no authorization configured.",
                    f"services.{name}.security.authorization",
                    "Implement RBAC or ABAC policies.",
                )

            # Check for encryption
            if service.get("database") and not security.get("encryption_at_rest"):
                self._add_issue(
                    "security",
                    Severity.WARNING,
                    f"Service '{name}' has database but no encryption at rest.",
                    f"services.{name}.security.encryption_at_rest",
                    "Enable encryption at rest for sensitive data.",
                )

            # Check for secrets management
            if not security.get("secrets_management"):
                self._add_issue(
                    "security",
                    Severity.INFO,
                    f"Service '{name}' has no secrets management defined.",
                    f"services.{name}.security.secrets_management",
                    "Use Vault or cloud-native secrets management.",
                )

    # =========================================================================
    # Anti-Pattern Detection
    # =========================================================================

    def _validate_anti_patterns(self):
        """Detect common anti-patterns."""
        self._check_distributed_monolith()
        self._check_chatty_services()
        self._check_database_communication()

    def _check_distributed_monolith(self):
        """Check for distributed monolith signs."""
        # Check for services that always deploy together
        deployment_groups = {}
        for name, service in self.services.items():
            group = service.get("deployment_group")
            if group:
                if group not in deployment_groups:
                    deployment_groups[group] = []
                deployment_groups[group].append(name)

        for group, services in deployment_groups.items():
            if len(services) > 2:
                self._add_issue(
                    "anti-patterns",
                    Severity.WARNING,
                    f"Services {services} share deployment group '{group}'. "
                    "This may indicate a distributed monolith.",
                    "deployment_groups",
                    "Services should be independently deployable.",
                )

    def _check_chatty_services(self):
        """Check for chatty service communication."""
        for name, service in self.services.items():
            sync_deps = [
                d for d in service.get("dependencies", [])
                if d.get("type") == "sync"
            ]

            # Check for multiple calls to same service
            dep_counts = {}
            for dep in sync_deps:
                svc = dep.get("service")
                dep_counts[svc] = dep_counts.get(svc, 0) + 1

            for dep_svc, count in dep_counts.items():
                if count > 2:
                    self._add_issue(
                        "anti-patterns",
                        Severity.WARNING,
                        f"Service '{name}' makes {count} sync calls to '{dep_svc}'. "
                        "Consider aggregating calls or using batch APIs.",
                        f"services.{name}.dependencies",
                        "Reduce chattiness with bulk endpoints or caching.",
                    )

    def _check_database_communication(self):
        """Check for database-based communication between services."""
        for name, service in self.services.items():
            for dep in service.get("dependencies", []):
                if dep.get("type") == "database":
                    self._add_issue(
                        "anti-patterns",
                        Severity.ERROR,
                        f"Service '{name}' communicates with '{dep.get('service')}' "
                        "via shared database. This is an anti-pattern.",
                        f"services.{name}.dependencies",
                        "Use events or APIs for inter-service communication.",
                    )


def load_architecture(file_path: str) -> dict:
    """Load architecture definition from YAML file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Architecture file not found: {file_path}")

    with open(path) as f:
        return yaml.safe_load(f)


def print_results(result: ValidationResult, json_output: bool = False):
    """Print validation results to stdout."""
    if json_output:
        print(json.dumps(result.to_dict(), indent=2))
        return

    # Header
    status = "PASSED" if result.passed else "FAILED"
    print(f"\n{'='*60}")
    print(f"Architecture Validation: {status}")
    print(f"{'='*60}")

    # Summary
    print(f"\nServices validated: {result.services_count}")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")
    print(f"Info: {result.info_count}")

    # Issues by category
    if result.issues:
        print(f"\n{'-'*60}")
        print("Issues:")
        print(f"{'-'*60}")

        categories = sorted(set(i.category for i in result.issues))
        for category in categories:
            cat_issues = [i for i in result.issues if i.category == category]
            print(f"\n[{category.upper()}]")
            for issue in cat_issues:
                severity_icon = {
                    Severity.ERROR: "X",
                    Severity.WARNING: "!",
                    Severity.INFO: "i",
                }[issue.severity]
                print(f"  [{severity_icon}] {issue.message}")
                if issue.location:
                    print(f"      Location: {issue.location}")
                if issue.suggestion:
                    print(f"      Suggestion: {issue.suggestion}")

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate microservices architecture against best practices"
    )
    parser.add_argument(
        "file",
        help="Path to architecture YAML file"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )

    args = parser.parse_args()

    try:
        architecture = load_architecture(args.file)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)

    validator = ArchitectureValidator(architecture)
    result = validator.validate()

    # In strict mode, warnings become errors
    if args.strict:
        for issue in result.issues:
            if issue.severity == Severity.WARNING:
                issue.severity = Severity.ERROR

    print_results(result, json_output=args.json)

    # Exit with error code if validation failed
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
