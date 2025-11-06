# Data Model: GitHub Actions CI Pipeline

**Date**: 2025-11-07
**Feature**: GitHub Actions CI Pipeline

## Overview

This feature implements CI/CD infrastructure using GitHub Actions. Unlike application features, there is no traditional "data model" with entities stored in databases. Instead, this document describes the **workflow structure**, **job dependencies**, and **configuration schema** that define the CI pipeline.

## Workflow Structure

### CI Workflow Entity

Represents the complete CI pipeline that runs on push and pull request events.

**Attributes**:
- **Name**: "CI"
- **Triggers**:
  - Push events to any branch
  - Pull request events (opened, synchronized, reopened)
- **Environment Variables**:
  - `UV_CACHE_DIR`: Path for uv cache storage
- **Jobs**: Collection of lint-and-typecheck job and test matrix jobs
- **Status**: Pending, In Progress, Success, Failed, Cancelled

**Lifecycle**:
1. Triggered by git push or PR event
2. Spawns parallel jobs (lint-and-typecheck + test matrix)
3. Aggregates job results
4. Reports overall status to GitHub UI
5. Blocks PR merge if any job fails (via branch protection rules)

---

### Lint and Type Check Job

Represents static analysis checks that run on a single Python version.

**Attributes**:
- **Name**: "lint-and-typecheck"
- **Runner**: ubuntu-latest
- **Python Version**: 3.11 (minimum supported version)
- **Steps**: Sequential execution of setup, cache, lint, typecheck
- **Dependencies**: None (runs in parallel with test jobs)
- **Status**: Pending, In Progress, Success, Failed

**Execution Flow**:
```
1. Checkout code
2. Setup uv
3. Setup Python 3.11
4. Restore cache (if available)
5. Install dependencies (uv sync --frozen)
6. Run ruff linting
7. Run pyright type checking
8. Prune cache
9. Report status
```

**Failure Conditions**:
- Checkout fails (network/git issues)
- Dependency installation fails (package unavailable, lock file corruption)
- Ruff finds linting errors
- Pyright finds type errors
- Any step returns non-zero exit code

---

### Test Job Matrix

Represents parallel test execution across multiple Python versions.

**Attributes**:
- **Name**: "test"
- **Strategy**: Matrix with Python versions ["3.11", "3.12", "3.13"]
- **Runner**: ubuntu-latest
- **Parallelism**: 3 concurrent jobs (one per Python version)
- **Fail Fast**: false (all versions run even if one fails)
- **Status**: Pending, In Progress, Success, Failed (per version)

**Matrix Variables**:
```yaml
python-version: ["3.11", "3.12", "3.13"]
```

**Execution Flow (per version)**:
```
1. Checkout code
2. Setup uv
3. Setup Python ${{ matrix.python-version }}
4. Restore cache (version-specific)
5. Install dependencies (uv sync --frozen)
6. Run pytest with coverage (-n auto, --cov)
7. Upload coverage to Codecov
8. Prune cache
9. Report status
```

**Failure Conditions**:
- Any test fails in pytest suite
- Test timeout (exceeds job timeout)
- Coverage upload fails (non-blocking, but warning issued)

---

## Cache Configuration

### UV Cache Entity

Represents cached dependencies to speed up CI runs.

**Attributes**:
- **Cache Paths**:
  - `~/.cache/uv` - UV package index cache
  - `~/.local/share/uv` - UV internal data
  - `.venv` - Virtual environment with installed packages
- **Cache Key Pattern**: `{os}-py{version}-uv-{lockfile_hash}`
  - Example: `Linux-py3.11-uv-a1b2c3d4...`
- **Restore Keys**: Fallback patterns for partial cache hits
  - Example: `Linux-py3.11-uv-`
- **Invalidation**: Automatic when `uv.lock` changes
- **Size Limit**: GitHub Actions 10GB per repository
- **TTL**: 7 days since last access

**Cache Operations**:
1. **Restore**: Attempt to restore from cache using key + restore keys
2. **Install**: If cache miss or partial hit, install/update dependencies
3. **Prune**: `uv cache prune --ci` removes unnecessary files
4. **Save**: Upload cache with current key

**Cache Key Strategy**:
- **OS**: Ensures platform-specific binaries don't mix
- **Python Version**: Different versions have different compiled extensions
- **Lockfile Hash**: Automatic invalidation on dependency changes

---

## Configuration Files Schema

### Workflow Configuration (ci.yml)

**Location**: `.github/workflows/ci.yml`

**Schema Structure**:
```yaml
name: string                    # Workflow name displayed in UI
on: [events]                    # Trigger events (push, pull_request)
env:                            # Workflow-level environment variables
  UV_CACHE_DIR: string

jobs:
  lint-and-typecheck:
    runs-on: string             # Runner type (ubuntu-latest)
    steps: [Step]               # Sequential list of actions/commands

  test:
    strategy:
      matrix:
        python-version: [string]
    runs-on: string
    steps: [Step]
```

**Step Schema**:
```yaml
- name: string                  # Step name (optional)
  uses: string                  # Action reference (e.g., actions/checkout@v4)
  with:                         # Action inputs
    key: value
- name: string
  run: string                   # Shell command to execute
```

---

### Pyright Configuration (pyrightconfig.json)

**Location**: `/workspace/pyrightconfig.json`

**Schema**:
```json
{
  "pythonVersion": "3.11",           // Minimum supported Python version
  "typeCheckingMode": "basic",       // basic | standard | strict
  "reportMissingImports": true,      // Error on missing imports
  "reportMissingTypeStubs": false,   // Warn on missing type stubs
  "exclude": [                       // Paths to exclude
    "**/node_modules",
    "**/__pycache__"
  ]
}
```

**Type Checking Modes**:
- **basic**: Minimal type checking (recommended starting point)
- **standard**: Moderate strictness, good for most projects
- **strict**: Maximum strictness, requires full type annotations

---

### Pytest Configuration (pytest.ini)

**Location**: `/workspace/pytest.ini`

**Current Configuration**:
```ini
[pytest]
minversion = 6.0
pythonpath = src
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests

[coverage:run]
source = c2.pas.aal2
omit =
    */tests/*
    */test_*.py
```

**Enhanced Configuration** (from research):
```ini
[pytest]
minversion = 6.0
pythonpath = src
testpaths = tests
addopts =
    -n auto                    # Parallel execution (auto-detect CPUs)
    -v                         # Verbose output
    --strict-markers           # Error on unknown markers
    --tb=short                 # Shorter traceback format
    --cov=c2.pas.aal2         # Coverage for source package
    --cov-report=term-missing  # Show missing lines in terminal
    --cov-report=xml           # XML report for Codecov
    --cov-branch               # Branch coverage (not just line)
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require Plone instance)
    slow: Slow-running tests (>1 second)
    smoke: Smoke tests (critical path, run first)
    webauthn: Tests requiring WebAuthn/FIDO2 functionality

[coverage:run]
source = c2.pas.aal2
branch = True
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */conftest.py
```

---

## Job Dependencies and Execution Order

### Dependency Graph

```
Trigger Event (push/PR)
        |
        v
    +---+---+
    |       |
    v       v
[Lint]   [Test Matrix]
         [3.11|3.12|3.13]
    |       |
    +---+---+
        |
        v
  All Jobs Complete
        |
        v
  Report Status to GitHub
```

**Parallel Execution**:
- Lint and type checking job runs in parallel with test matrix
- All 3 Python version test jobs run in parallel
- Total parallelism: 4 concurrent jobs

**Status Aggregation**:
- Workflow succeeds only if ALL jobs succeed
- If any job fails, entire workflow fails
- Individual job statuses visible in GitHub Actions UI

---

## State Transitions

### Workflow State Machine

```
PENDING → IN_PROGRESS → {SUCCESS | FAILED | CANCELLED}
```

**Transitions**:
1. **PENDING**: Workflow queued, waiting for runner availability
2. **IN_PROGRESS**: At least one job is executing
3. **SUCCESS**: All jobs completed with exit code 0
4. **FAILED**: At least one job failed (exit code ≠ 0)
5. **CANCELLED**: User manually cancelled or timeout reached

### Job State Machine

```
QUEUED → RUNNING → {SUCCESS | FAILED}
```

**Transitions**:
1. **QUEUED**: Job waiting for runner assignment
2. **RUNNING**: Job executing steps sequentially
3. **SUCCESS**: All steps completed successfully
4. **FAILED**: Any step failed

---

## Validation Rules

### Workflow Validation

1. **Syntax**: YAML must be valid and conform to GitHub Actions schema
2. **Actions**: Referenced actions must exist and use valid versions (e.g., `@v4`)
3. **Matrix**: Python versions must be available on ubuntu-latest runners
4. **Timeouts**: Jobs should complete within 10 minutes (per FR-009)
5. **Cache**: Cache size should stay under 10GB repository limit

### Configuration Validation

1. **Pyright**: Configuration must be valid JSON, pythonVersion must match supported versions
2. **Pytest**: Markers must be declared before use (--strict-markers enforces this)
3. **Dependencies**: uv.lock must be in sync with pyproject.toml

---

## Performance Constraints

Based on research and FR-009 requirement:

| Job | Target Duration | Maximum Duration |
|-----|----------------|------------------|
| Lint + Type Check | 1-2 minutes | 3 minutes |
| Test (per Python version) | 1-3 minutes | 5 minutes |
| Total CI Pipeline | 3-5 minutes | 10 minutes |

**Optimization Techniques**:
- Dependency caching (saves 1-2 minutes per run)
- Parallel test execution with pytest-xdist (60-80% faster)
- Parallel job execution (lint + 3 test jobs run simultaneously)
- Fast tools (ruff is 10-100x faster than flake8, pyright is 3-5x faster than mypy)

---

## Error Handling

### Failure Scenarios and Responses

| Failure Type | Detection | Response |
|-------------|-----------|----------|
| Linting errors | Ruff exit code ≠ 0 | Fail job, show error lines, block PR |
| Type errors | Pyright exit code ≠ 0 | Fail job, show type issues, block PR |
| Test failures | Pytest exit code ≠ 0 | Fail job, show failed tests, block PR |
| Dependency installation failure | UV sync fails | Fail job, show error message, retry possible |
| Cache corruption | Cache restore fails | Continue with fresh install (degraded performance) |
| Runner timeout | Job exceeds 360 minutes (GitHub default) | Cancel job, fail workflow |

**Error Visibility**:
- All errors logged to GitHub Actions UI with expandable sections
- PR status checks show which specific job failed
- Annotations appear directly on PR files for linting/type errors (if configured)

---

## Integration Points

### GitHub API

Workflow interacts with GitHub via:
- **Status API**: Reports job status to PR checks
- **Annotations API**: Can add inline comments on code (linting/type errors)
- **Cache API**: Stores and retrieves cached dependencies
- **Artifacts API**: Can store test reports (future enhancement)

### External Services

- **Codecov**: Receives coverage reports via API upload
- **PyPI/Package Indexes**: UV downloads packages during dependency installation
- **GitHub Container Registry**: Pulls runner Docker images

---

## Security Considerations

1. **Secrets**: No secrets required for basic CI (all runs on public code)
2. **Permissions**: Workflow has default `GITHUB_TOKEN` with read/write to checks
3. **Cache Poisoning**: Cache is scoped per repository, cannot be shared across repos
4. **Dependency Trust**: UV verifies package hashes from lockfile
5. **Runner Security**: ubuntu-latest runners are ephemeral and isolated

---

**Summary**: This data model defines the structure, behavior, and constraints of the GitHub Actions CI pipeline, treating the workflow configuration as the "schema" and jobs as the "entities" in this infrastructure-as-code context.
