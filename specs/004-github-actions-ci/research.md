# Research: GitHub Actions CI Pipeline

**Date**: 2025-11-07
**Feature**: GitHub Actions CI Pipeline for Python 3.11-3.13

## Overview

This document contains research findings and decisions for implementing a GitHub Actions CI pipeline that runs pytest, ruff linting, and type checking across Python 3.11, 3.12, and 3.13 using uv package manager.

## Research Questions & Decisions

### 1. Type Checker Selection

**Decision**: Use **Pyright** as the primary type checker

**Rationale**:
- **Performance**: 3-5x faster than mypy due to lazy just-in-time type evaluation architecture
- **Python Version Support**: Full support for Python 3.11, 3.12, 3.13, and 3.14 with custom parser that handles newer syntax regardless of runtime version
- **Strictness**: More aggressive type checking by default, including unannotated code
- **Industry Trend**: Increasingly popular in 2025, especially with VS Code/Pylance integration
- **Zero Configuration**: Works out-of-the-box with minimal configuration

**Alternatives Considered**:
- **Mypy**: Traditional industry standard, but slower and requires more configuration. Still valid for compatibility checking.
- **Pytype**: Deprecated by Google in 2025, only supports up to Python 3.12
- **Hybrid Approach**: Run both Pyright (primary) and mypy (compatibility) - common in mature projects

**Configuration**:
```json
// pyrightconfig.json
{
  "pythonVersion": "3.11",
  "typeCheckingMode": "basic",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false
}
```

---

### 2. Linting and Type Checking Execution Strategy

**Decision**: Run linting (ruff) and type checking (pyright) on **ONE Python version only** (3.11 minimum)

**Rationale**:
- **Version Independence**: Linting and type checking results are identical across Python versions when properly configured
  - Ruff's `target-version` controls rules, not runtime version
  - Pyright can check any target version regardless of runtime
- **CI Optimization**: Running once saves 66% of CI time compared to running on all 3 versions
- **Industry Practice**: GitHub Actions official recommendation - "run lint with a single version of Python"
- **No Loss of Coverage**: Test matrix handles runtime behavior differences, static analysis is version-agnostic

**Configuration Strategy**:
```yaml
# Separate jobs:
# 1. lint-and-typecheck: Runs on Python 3.11 only
# 2. test: Matrix across Python 3.11, 3.12, 3.13
```

**Alternatives Considered**:
- **Run on all versions**: Wastes CI resources with no additional value
- **Run on latest version only (3.13)**: Could miss compatibility issues with minimum version

---

### 3. Pytest Configuration Best Practices

**Decision**: Implement parallel testing, enhanced markers, and branch coverage

**Markers Strategy**:
```ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require Plone instance)
    slow: Slow-running tests (>1 second)
    smoke: Smoke tests (critical path, run first)
    webauthn: Tests requiring WebAuthn/FIDO2 functionality
```

**Parallel Execution**:
- Use `pytest-xdist` with `-n auto` for automatic CPU detection
- Expected performance improvement: 60-80% faster test execution
- Requirement: Tests must be independent (no shared state)

**Coverage Configuration**:
```ini
[pytest]
addopts =
    -n auto
    -v
    --strict-markers
    --tb=short
    --cov=c2.pas.aal2
    --cov-report=term-missing
    --cov-report=xml
    --cov-branch

[coverage:run]
source = c2.pas.aal2
omit = */tests/*, */test_*.py, */__pycache__/*
branch = True
```

**CI Usage Patterns**:
- Fast feedback: `pytest -m "unit and not slow"`
- Smoke tests: `pytest -m smoke`
- Full suite: `pytest`
- Upload coverage to Codecov for tracking

**Rationale**:
- **Parallel execution**: PyPI achieved 81% faster tests using pytest-xdist
- **Markers**: Enable selective test running for faster feedback
- **Branch coverage**: Better than line coverage for conditional logic
- **Industry standard**: Widely adopted pattern in Python projects

**Alternatives Considered**:
- **No parallelization**: Simpler but slower
- **Manual worker count**: Less portable than `-n auto`

---

### 4. UV Dependency Caching Strategy

**Decision**: Manual cache management with `actions/cache@v4` using lockfile-based keys

**Cache Configuration**:
```yaml
- name: Cache uv dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      ~/.local/share/uv
      .venv
    key: ${{ runner.os }}-py${{ matrix.python-version }}-uv-${{ hashFiles('**/uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-py${{ matrix.python-version }}-uv-

- name: Install dependencies
  run: uv sync --frozen

- name: Prune cache
  run: uv cache prune --ci
```

**Key Strategy Components**:
1. **Cache Location**: Both uv's package cache (`~/.cache/uv`) and virtual environment (`.venv`)
2. **Cache Key**: Based on OS, Python version, and `uv.lock` hash for automatic invalidation
3. **Restore Keys**: Fallback to previous caches for partial hits
4. **Cache Pruning**: `uv cache prune --ci` minimizes cache size before saving

**Rationale**:
- **Automatic Invalidation**: Cache updates when dependencies change via `hashFiles('uv.lock')`
- **Matrix Awareness**: Separate caches per Python version for compiled dependencies
- **Size Optimization**: Pruning reduces cache storage and upload/download time
- **Best Practice**: Recommended by astral-sh/setup-uv official documentation

**Alternatives Considered**:
- **setup-uv's enable-cache**: Less control, not recommended for complex projects
- **hynek/setup-cached-uv**: Simplified third-party action, good for simple projects
- **No caching**: Significantly slower CI runs

---

## Technology Stack Summary

| Component | Choice | Version/Notes |
|-----------|--------|---------------|
| **Type Checker** | Pyright | Latest stable, configured for Python 3.11+ |
| **Linter** | Ruff | Pin version (e.g., `ruff>=0.8.0,<0.9.0`) |
| **Test Framework** | pytest | With pytest-xdist for parallelization |
| **Package Manager** | uv | With lockfile-based caching |
| **Coverage Tool** | coverage.py | Via pytest-cov plugin, branch coverage enabled |
| **CI Platform** | GitHub Actions | ubuntu-latest runners |

---

## Implementation Checklist

### Configuration Files to Create/Update

1. **pyrightconfig.json** or add to **pyproject.toml**:
   ```json
   {
     "pythonVersion": "3.11",
     "typeCheckingMode": "basic"
   }
   ```

2. **pytest.ini** updates:
   - Add new markers (slow, smoke, webauthn)
   - Add `-n auto` to addopts
   - Enable `--cov-branch`

3. **pyproject.toml** dependencies:
   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest>=8.0",
       "pytest-cov>=5.0",
       "pytest-xdist>=3.5",
       "pyright>=1.1",
       "ruff>=0.8.0,<0.9.0",
   ]
   ```

4. **.github/workflows/ci.yml**: Main CI workflow (created in Phase 1)

### Workflow Structure

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - Setup Python 3.11
      - Cache uv dependencies
      - Install dependencies with uv
      - Run ruff check
      - Run pyright

  test:
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    runs-on: ubuntu-latest
    steps:
      - Setup Python ${{ matrix.python-version }}
      - Cache uv dependencies
      - Install dependencies with uv
      - Run pytest with coverage
      - Upload coverage to Codecov
```

---

## Risk Mitigation

### Potential Issues & Solutions

1. **Flaky Tests in Parallel Execution**
   - **Risk**: Tests may fail intermittently when run in parallel
   - **Mitigation**: Use `pytest-randomly` to detect order dependencies, ensure test isolation with fixtures

2. **Cache Size Growth**
   - **Risk**: GitHub Actions cache has 10GB limit per repository
   - **Mitigation**: `uv cache prune --ci` keeps cache size minimal, consider periodic manual cleanup

3. **Version-Specific Failures**
   - **Risk**: Code works on 3.11 but fails on 3.12/3.13
   - **Mitigation**: Test matrix catches these, fast feedback via parallel jobs

4. **Type Checker False Positives**
   - **Risk**: Pyright may be stricter than expected
   - **Mitigation**: Start with `typeCheckingMode: "basic"`, gradually increase to "standard" or "strict"

5. **Dependency Installation Failures**
   - **Risk**: Network issues or package unavailability
   - **Mitigation**: `uv sync --frozen` ensures reproducible installs, cache reduces network dependency

---

## Performance Expectations

Based on research and benchmarks:

- **Linting (ruff)**: < 5 seconds (extremely fast, can lint large codebases in 0.5s)
- **Type Checking (pyright)**: 30-60 seconds (3-5x faster than mypy)
- **Test Execution**:
  - Sequential: ~2-5 minutes (estimated for current test suite)
  - Parallel (-n auto): ~1-2 minutes (60-80% improvement)
- **Dependency Installation**:
  - First run (no cache): 1-2 minutes
  - Cached runs: 10-30 seconds
- **Total CI Time**: Target < 10 minutes (requirement: FR-009)

**Estimated Breakdown**:
- Lint + Type Check job: ~1 minute
- Test matrix (3 versions in parallel): ~2-3 minutes (longest job)
- Total wall-clock time: ~3-4 minutes (well under 10-minute requirement)

---

## References

- [GitHub Actions Python setup best practices](https://docs.github.com/actions/automating-builds-and-tests/building-and-testing-python)
- [astral-sh/setup-uv caching documentation](https://github.com/astral-sh/setup-uv#caching)
- [Pyright documentation](https://microsoft.github.io/pyright/)
- [Ruff configuration guide](https://docs.astral.sh/ruff/configuration/)
- [pytest-xdist parallel execution](https://pytest-xdist.readthedocs.io/)
- Industry benchmarks: PyPI (81% faster with pytest-xdist), Ruff performance benchmarks

---

**Research Completed**: All NEEDS CLARIFICATION items from Technical Context have been resolved.
