# GitHub Actions Workflow Contract

**Date**: 2025-11-07
**Feature**: GitHub Actions CI Pipeline
**Contract Type**: Infrastructure Configuration

## Overview

This document defines the contract (interface) for the GitHub Actions CI workflow. Since this is infrastructure-as-code rather than a traditional API, the "contract" describes the expected inputs, outputs, behavior, and guarantees of the CI pipeline.

---

## Workflow Interface

### Trigger Contract

**Input Events**:
```yaml
# Contract: Workflow MUST trigger on these events
on:
  push:
    branches: ['**']          # Any branch
  pull_request:
    types:
      - opened                # New PR created
      - synchronize           # New commits pushed to PR
      - reopened              # Closed PR reopened
```

**Guarantees**:
- Workflow starts within 30 seconds of trigger event
- Each push/PR update gets a unique workflow run
- Concurrent runs are allowed (no queue limit)

---

## Job Contracts

### 1. Lint and Type Check Job

**Purpose**: Validate code quality and type safety

**Input Requirements**:
```yaml
# Contract: Job requires these inputs
- Python 3.11 available on runner
- Source code in /src directory
- Configuration files:
  - pyrightconfig.json (type checking rules)
  - pyproject.toml (project metadata, ruff config)
```

**Execution Contract**:
```yaml
steps:
  1. Checkout code (actions/checkout@v4)
  2. Setup uv (astral-sh/setup-uv@v5)
  3. Setup Python 3.11
  4. Restore cache (optional, non-blocking if missing)
  5. Install dependencies: uv sync --frozen
  6. Run linting: uv run ruff check .
  7. Run type checking: uv run pyright
  8. Prune cache: uv cache prune --ci
```

**Output Contract**:
```yaml
# Success Criteria
exit_code: 0
conditions:
  - No linting errors found by ruff
  - No type errors found by pyright
  - All steps completed successfully

# Failure Criteria
exit_code: non-zero
conditions:
  - Linting errors detected (style violations, unused imports, etc.)
  - Type errors detected (missing annotations, type mismatches, etc.)
  - Dependency installation failed
  - Any step failed

# Output Artifacts
- Job logs (stdout/stderr)
- Annotations on PR (if errors found)
- Cache saved (on success or failure)
```

**Performance Contract**:
- **Target Duration**: 1-2 minutes
- **Maximum Duration**: 3 minutes
- **Timeout**: Job cancelled if exceeds 360 minutes (GitHub default)

**Failure Examples**:
```python
# Linting failure example
import os  # unused import - ruff will fail

# Type error example
def add(a, b):  # missing type annotations - pyright will fail
    return a + b
```

---

### 2. Test Job (Matrix)

**Purpose**: Validate functionality across Python 3.11, 3.12, 3.13

**Input Requirements**:
```yaml
# Contract: Job requires these inputs per matrix version
- Python ${{ matrix.python-version }} available on runner
- Test files in /tests directory
- Configuration files:
  - pytest.ini (test configuration)
  - pyproject.toml (dependencies)
  - uv.lock (pinned dependencies)
```

**Matrix Contract**:
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
  fail-fast: false              # All versions run even if one fails

# Guarantees:
# - 3 jobs run in parallel (one per Python version)
# - Each job is independent
# - Each job uses version-specific cache
```

**Execution Contract**:
```yaml
steps:
  1. Checkout code (actions/checkout@v4)
  2. Setup uv (astral-sh/setup-uv@v5)
  3. Setup Python ${{ matrix.python-version }}
  4. Restore cache (version-specific, optional)
  5. Install dependencies: uv sync --frozen
  6. Run tests: uv run pytest --cov --cov-report=xml
  7. Upload coverage: codecov/codecov-action@v4
  8. Prune cache: uv cache prune --ci
```

**Output Contract**:
```yaml
# Success Criteria (per version)
exit_code: 0
conditions:
  - All tests passed
  - No test failures or errors
  - Coverage report generated
  - Coverage uploaded (warning if fails, not blocking)

# Failure Criteria
exit_code: non-zero
conditions:
  - One or more tests failed
  - Test timeout or crash
  - Dependency installation failed
  - Any step failed (except coverage upload)

# Output Artifacts (per version)
- Test results (passed/failed/skipped counts)
- Coverage report (XML format)
- Job logs (stdout/stderr with test output)
- Cache saved (on success or failure)
```

**Performance Contract**:
- **Target Duration**: 1-3 minutes (per Python version)
- **Maximum Duration**: 5 minutes (per version)
- **Parallel Execution**: pytest -n auto (uses all available CPU cores)

**Test Execution Guarantees**:
```yaml
# Test discovery
- All files matching test_*.py or *_test.py
- All functions starting with test_
- testpaths = tests (from pytest.ini)

# Test markers
- @pytest.mark.unit - Fast unit tests
- @pytest.mark.integration - Integration tests
- @pytest.mark.slow - Slow tests (>1 second)
- @pytest.mark.smoke - Critical path tests

# Coverage requirements
- Source package: c2.pas.aal2
- Minimum coverage: Not enforced (informational only)
- Branch coverage: Enabled (--cov-branch)
```

---

## Cache Contract

### Cache Interface

**Purpose**: Speed up dependency installation across CI runs

**Input Contract**:
```yaml
# Cache key formula
key: ${{ runner.os }}-py${{ matrix.python-version }}-uv-${{ hashFiles('**/uv.lock') }}

# Example keys:
# - Linux-py3.11-uv-a1b2c3d4e5f6...
# - Linux-py3.12-uv-a1b2c3d4e5f6...
# - Linux-py3.13-uv-a1b2c3d4e5f6...

# Restore fallback
restore-keys: |
  ${{ runner.os }}-py${{ matrix.python-version }}-uv-

# Cached paths
paths:
  - ~/.cache/uv          # UV package index
  - ~/.local/share/uv    # UV internal data
  - .venv                # Virtual environment
```

**Cache Behavior Contract**:
```yaml
# Cache Hit (Exact Match)
- Key matches exactly (lockfile unchanged)
- Full cache restored
- Result: Fast dependency installation (~10-30 seconds)

# Cache Hit (Partial Match)
- Restore key matches (same OS + Python version)
- Base dependencies restored
- uv updates changed packages only
- Result: Medium dependency installation (~30-60 seconds)

# Cache Miss
- No matching key found
- Fresh installation required
- Result: Slow dependency installation (~1-2 minutes)

# Cache Save
- Always saves after dependency installation
- Prunes unnecessary files first (uv cache prune --ci)
- Uploads with current key
- Result: Cache available for next run
```

**Cache Invalidation Contract**:
```yaml
# Automatic invalidation when:
- uv.lock file changes (new/updated/removed dependencies)
- Python version changes (e.g., upgrading from 3.11 to 3.12)
- OS changes (e.g., ubuntu-latest → macos-latest)

# Manual invalidation:
- Delete cache via GitHub UI: Settings → Actions → Caches
- Change cache key formula in workflow

# Cache expiration:
- 7 days since last access (GitHub Actions policy)
- 10GB repository limit (oldest caches evicted first)
```

---

## Status Reporting Contract

### GitHub Checks API

**Purpose**: Report CI status to pull requests and commits

**Status Contract**:
```yaml
# Check statuses
statuses:
  - name: "lint-and-typecheck"
    states: [pending, in_progress, success, failure]

  - name: "test (3.11)"
    states: [pending, in_progress, success, failure]

  - name: "test (3.12)"
    states: [pending, in_progress, success, failure]

  - name: "test (3.13)"
    states: [pending, in_progress, success, failure]

# Overall workflow status
workflow:
  success: All 4 checks passed
  failure: Any check failed
  cancelled: User cancelled or timeout
```

**PR Integration Contract**:
```yaml
# Pull request checks
checks:
  required: true                    # Blocks merge if failed
  display: GitHub UI PR checks section

  details:
    - Check name
    - Status (✓ success, ✗ failure, ⚠ in progress)
    - Duration
    - Link to job logs

# Branch protection rules (recommended)
protection:
  require_status_checks:
    strict: true                    # Require branches to be up to date
    contexts:
      - "lint-and-typecheck"
      - "test (3.11)"
      - "test (3.12)"
      - "test (3.13)"
```

---

## Failure Modes and Error Handling

### Error Categories and Responses

#### 1. Code Quality Failures (Expected)

**Linting Errors**:
```yaml
cause: ruff check finds violations
example: "Unused import at line 42"
exit_code: 1
blocking: Yes
retry: No (fix code and push)
logs: Shows specific file, line, rule violated
```

**Type Errors**:
```yaml
cause: pyright finds type issues
example: "Type mismatch: expected str, got int"
exit_code: 1
blocking: Yes
retry: No (fix code and push)
logs: Shows specific file, line, type issue
```

**Test Failures**:
```yaml
cause: pytest assertion fails
example: "AssertionError: expected True, got False"
exit_code: 1
blocking: Yes
retry: No (fix test or code and push)
logs: Shows failed test, assertion details, traceback
```

#### 2. Infrastructure Failures (Unexpected)

**Dependency Installation Failure**:
```yaml
cause: Package unavailable, network issue, lock corruption
example: "Failed to resolve package foo"
exit_code: 1
blocking: Yes
retry: Yes (GitHub Actions auto-retries transient failures)
logs: Shows UV error, missing package details
mitigation: Cache provides fallback dependencies
```

**Cache Failure**:
```yaml
cause: Cache corruption, network issue
exit_code: 0 (non-blocking)
blocking: No
retry: Yes (continues with fresh install)
logs: Warning message, fallback to fresh install
impact: Slower CI run (no functional impact)
```

**Runner Failure**:
```yaml
cause: Runner unavailable, timeout, crash
exit_code: varies
blocking: Yes
retry: Yes (GitHub Actions auto-retries)
logs: Shows runner error or timeout message
escalation: Rare, contact GitHub Support if persistent
```

---

## Performance Guarantees

### Time Budgets (per FR-009)

| Component | Target | Maximum | Breach Action |
|-----------|--------|---------|---------------|
| Total CI Pipeline | 3-5 min | 10 min | Investigate optimization |
| Lint + Type Check | 1-2 min | 3 min | Check ruff/pyright config |
| Test (per version) | 1-3 min | 5 min | Investigate slow tests |
| Dependency Install (cached) | 10-30 sec | 1 min | Check cache health |
| Dependency Install (no cache) | 1-2 min | 3 min | Check network/packages |

**Performance Monitoring**:
- GitHub Actions provides duration for each job/step
- Trends visible in Actions UI → Workflow runs
- Alerts: Manual monitoring (GitHub Actions has no built-in alerts)

---

## Compatibility Contract

### Python Version Support

**Guaranteed Support**:
```yaml
python-versions:
  - "3.11"  # Minimum version, used for linting/type checking
  - "3.12"  # Current stable
  - "3.13"  # Latest stable

# Version lifecycle
- Add new versions when released (e.g., 3.14 in Oct 2025)
- Remove EOL versions after project drops support
- Test matrix ensures compatibility across all supported versions
```

### Platform Support

**Guaranteed Platforms**:
```yaml
runners:
  - ubuntu-latest  # Primary platform, all jobs run here

# Rationale
- Plone.PAS is Linux-focused
- ubuntu-latest is fastest and cheapest runner
- Cross-platform testing not required for server-side code
```

**Future Platform Support** (if needed):
```yaml
# Example: Adding macOS/Windows testing
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.11", "3.12", "3.13"]
```

---

## Dependency Contract

### External Dependencies

**GitHub Actions**:
```yaml
actions/checkout@v4:
  purpose: Clone repository
  version: v4 (stable)
  breaking_changes: Review v5 when released

astral-sh/setup-uv@v5:
  purpose: Install uv package manager
  version: v5 (stable)
  breaking_changes: Follow Astral's changelog

actions/cache@v4:
  purpose: Cache dependencies
  version: v4 (stable)
  breaking_changes: Review v5 when released

codecov/codecov-action@v4:
  purpose: Upload coverage reports
  version: v4 (stable)
  breaking_changes: Optional, failure non-blocking
```

**Python Packages** (managed by UV):
```yaml
# Development dependencies (from pyproject.toml)
pytest: ">=8.0"             # Test framework
pytest-cov: ">=5.0"         # Coverage plugin
pytest-xdist: ">=3.5"       # Parallel execution
pyright: ">=1.1"            # Type checker
ruff: ">=0.8.0,<0.9.0"      # Linter (pinned)

# Version pinning strategy
- Pin exact versions for tools (ruff, pyright) to prevent CI breakage
- Use version ranges for libraries (pytest) for flexibility
- Lock all versions in uv.lock for reproducibility
```

---

## Extensibility Contract

### Adding New Checks

**Contract for Future Enhancements**:
```yaml
# Example: Adding security scanning
- name: Security scan
  run: uv run bandit -r src/

# Example: Adding code formatting check
- name: Check formatting
  run: uv run ruff format --check .

# Example: Adding docstring linting
- name: Check docstrings
  run: uv run pydocstyle src/
```

**Integration Points**:
- New checks added as steps in lint-and-typecheck job
- Each check MUST return non-zero exit code on failure
- Logs MUST be readable and actionable

---

## Rollback Contract

### Reverting CI Changes

**Safe Rollback Procedure**:
```yaml
# If CI workflow breaks:
1. Identify commit that introduced breakage
2. Revert workflow file: git revert <commit>
3. Push to main branch
4. Old workflow restored, CI working again

# If workflow syntax is invalid:
- GitHub Actions will show syntax error
- Fix syntax or revert to last known good version
- Invalid workflow does not block pushes (just CI reports)
```

**Backward Compatibility**:
- Workflow changes MUST NOT break on old code commits
- If new tool version breaks old code, pin tool version
- Feature flag new checks for gradual rollout (if needed)

---

## Service Level Expectations

### Availability

**CI Availability**:
- Depends on GitHub Actions availability (99.9% uptime SLA)
- GitHub status: https://www.githubstatus.com/
- Degraded service: CI may be slow but functional

**Failure Recovery**:
```yaml
transient_failures:
  retry: Automatic (GitHub Actions built-in)
  examples: Network timeout, runner unavailable

persistent_failures:
  retry: Manual (re-run workflow)
  escalation: Check GitHub Status, contact support
```

---

## Testing the Contract

### Validation Checklist

**Before Deploying Workflow**:
```yaml
- [ ] Syntax: Validate YAML with GitHub Actions linter
- [ ] Actions: Verify all actions exist and versions are valid
- [ ] Python Versions: Confirm 3.11, 3.12, 3.13 available on ubuntu-latest
- [ ] Tools: Verify ruff, pyright, pytest are in dependencies
- [ ] Paths: Confirm src/, tests/ directories exist
- [ ] Config: Ensure pyrightconfig.json, pytest.ini present
```

**After Deploying Workflow**:
```yaml
- [ ] Push commit: Trigger workflow on main branch
- [ ] View logs: Confirm all jobs start and complete
- [ ] Check status: Verify PR checks appear correctly
- [ ] Test failure: Introduce intentional error, verify CI fails
- [ ] Test success: Fix error, verify CI passes
- [ ] Check cache: Verify dependencies are cached (faster 2nd run)
```

---

## Summary

This contract defines:
- **Inputs**: Git events, source code, configuration files
- **Outputs**: Pass/fail status, job logs, coverage reports, cached dependencies
- **Behavior**: Parallel job execution, caching, status reporting
- **Guarantees**: 10-minute max duration, all Python versions tested, blocking on failure
- **Failure Modes**: Code quality failures (expected), infrastructure failures (retry)
- **Performance**: Sub-5-minute typical runs with caching

**Contract Compliance**: Any implementation of this CI pipeline MUST adhere to these interfaces and guarantees.
