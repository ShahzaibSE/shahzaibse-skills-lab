# Base Image Selection Guide

Choosing the right base image is critical for security, size, and compatibility.

## Quick Reference

| Use Case | Recommended | Size | Shell | Notes |
|----------|-------------|------|-------|-------|
| Go (static) | `scratch` | 0MB | No | CGO_ENABLED=0 |
| Go (dynamic) | `gcr.io/distroless/base` | ~20MB | No | With C dependencies |
| Rust (static) | `scratch` | 0MB | No | MUSL target |
| Rust (dynamic) | `gcr.io/distroless/cc` | ~20MB | No | glibc linked |
| Python | `python:3.x-slim` | ~150MB | Yes | Best debugging support |
| Python (minimal) | `gcr.io/distroless/python3` | ~50MB | No | No pip at runtime |
| Node.js | `node:lts-alpine` | ~120MB | Yes | Good debugging |
| Node.js (minimal) | `gcr.io/distroless/nodejs` | ~100MB | No | Prod only |
| Java | `eclipse-temurin:*-jre-alpine` | ~200MB | Yes | JRE only |
| Java (minimal) | `gcr.io/distroless/java` | ~200MB | No | No shell |
| .NET | `mcr.microsoft.com/dotnet/runtime-deps:*-alpine` | ~10MB | Yes | Self-contained |

---

## Image Categories

### 1. Scratch (Empty Image)

**Size**: 0 bytes
**Use when**: Statically linked binaries (Go, Rust)

```dockerfile
FROM scratch
COPY --from=builder /app/binary /binary
ENTRYPOINT ["/binary"]
```

**Pros:**
- Smallest possible image
- Minimal attack surface (no shell, no tools)
- No CVEs from base OS

**Cons:**
- No shell for debugging
- No DNS resolution without embedded resolver
- Cannot exec into container

**Requirements:**
- Go: `CGO_ENABLED=0 go build -ldflags="-s -w"`
- Rust: `rustup target add x86_64-unknown-linux-musl`

---

### 2. Distroless (Google)

**Size**: 20-50MB depending on variant
**Use when**: Need minimal runtime without shell

| Variant | Contents | Use For |
|---------|----------|---------|
| `gcr.io/distroless/static` | glibc, ca-certs | Static binaries needing certs |
| `gcr.io/distroless/base` | + libc | Dynamic binaries |
| `gcr.io/distroless/cc` | + libgcc | C++ applications |
| `gcr.io/distroless/python3` | Python runtime | Python apps |
| `gcr.io/distroless/nodejs` | Node runtime | Node.js apps |
| `gcr.io/distroless/java` | JRE | Java apps |

**Pros:**
- No shell, package manager, or unnecessary tools
- Significantly reduced CVE surface
- Supports multiple languages

**Cons:**
- Cannot exec into container for debugging
- No package installation at runtime
- Debug images available but larger

**Debug variant** (for troubleshooting):
```dockerfile
FROM gcr.io/distroless/python3:debug
# Includes busybox shell at /busybox/sh
```

---

### 3. Alpine Linux

**Size**: ~5MB base
**Use when**: Need shell but want minimal size

```dockerfile
FROM python:3.12-alpine
```

**Pros:**
- Very small (~5MB base)
- Shell available for debugging
- Package manager (apk) available

**Cons:**
- Uses musl libc (not glibc)
- Some Python packages need compilation
- Potential compatibility issues

**musl vs glibc issues:**
```dockerfile
# If you see errors like "Error loading shared library"
# The package may require glibc

# Option 1: Install glibc compatibility layer
RUN apk add --no-cache gcompat

# Option 2: Use slim variant instead of alpine
FROM python:3.12-slim
```

**Common Alpine packages for building:**
```dockerfile
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev
```

---

### 4. Slim Variants (Debian-based)

**Size**: ~80-150MB
**Use when**: Need glibc compatibility and debugging

```dockerfile
FROM python:3.12-slim
FROM node:20-slim
```

**Pros:**
- Uses glibc (maximum compatibility)
- Shell and basic tools available
- apt package manager
- Good balance of size and functionality

**Cons:**
- Larger than Alpine
- More potential CVEs than distroless

**Recommended cleanup:**
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        package1 \
        package2 && \
    rm -rf /var/lib/apt/lists/*
```

---

## Version Pinning

### Levels of Pinning

```dockerfile
# Level 1: Floating (NEVER use in production)
FROM python:latest        # Changes unpredictably
FROM python:3            # Could be 3.12, 3.13, etc.

# Level 2: Version pinned (Good)
FROM python:3.12.3-slim  # Specific version

# Level 3: Digest pinned (Best for production)
FROM python:3.12.3-slim@sha256:abc123def456...
```

### Getting Image Digests

```bash
# Pull the image first
docker pull python:3.12.3-slim

# Get the digest
docker inspect --format='{{index .RepoDigests 0}}' python:3.12.3-slim

# Or use crane (recommended)
crane digest python:3.12.3-slim
```

### Automated Digest Updates

Consider using tools like:
- **Renovate** - Automated dependency updates
- **Dependabot** - GitHub native updates
- **crane** - Manual digest lookup

---

## Language-Specific Guidance

### Python

```dockerfile
# Recommended for most cases
FROM python:3.12.3-slim@sha256:...

# For data science (needs compilation tools)
FROM python:3.12.3-slim@sha256:...
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Minimal production (no pip)
FROM gcr.io/distroless/python3-debian12@sha256:...
```

### Node.js

```dockerfile
# Recommended (good debugging, small)
FROM node:20.11-alpine@sha256:...

# If alpine causes issues
FROM node:20.11-slim@sha256:...

# Minimal production
FROM gcr.io/distroless/nodejs20-debian12@sha256:...
```

### Go

```dockerfile
# Builder
FROM golang:1.22-alpine@sha256:... AS builder
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app

# Runtime (static binary)
FROM scratch
COPY --from=builder /app /app
```

### Java

```dockerfile
# Recommended (JRE only, not JDK)
FROM eclipse-temurin:21-jre-alpine@sha256:...

# Minimal
FROM gcr.io/distroless/java21-debian12@sha256:...
```

---

## Security Considerations

### Image Scanning

Always scan base images for vulnerabilities:

```bash
# Trivy
trivy image python:3.12.3-slim

# Grype
grype python:3.12.3-slim

# Docker Scout
docker scout cves python:3.12.3-slim
```

### Update Strategy

| Environment | Strategy |
|-------------|----------|
| Development | Use version tags, update weekly |
| Staging | Use digest pins, update on PR |
| Production | Use digest pins, update with testing |

---

## Decision Matrix

```
Need smallest possible?
├── Yes → Can you statically link?
│   ├── Yes → scratch
│   └── No → distroless (appropriate variant)
└── No → Need shell for debugging?
    ├── Yes → Is musl compatible?
    │   ├── Yes → alpine
    │   └── No → slim
    └── No → distroless
```
