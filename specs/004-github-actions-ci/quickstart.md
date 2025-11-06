# Quickstart: GitHub Actions CI Pipeline

**Date**: 2025-11-07
**Feature**: GitHub Actions CI Pipeline for Python 3.11-3.13

## Overview

This guide helps you set up and use the GitHub Actions CI pipeline for automated testing, linting, and type checking across Python 3.11, 3.12, and 3.13.

---

## Prerequisites

Before setting up CI, ensure:

- [ ] Repository hosted on GitHub
- [ ] Python project with source code in `src/` directory
- [ ] Tests in `tests/` directory
- [ ] Using `uv` as package manager (with `uv.lock` file)
- [ ] GitHub Actions enabled for repository (Settings → Actions → General)

---

## Quick Setup (5 Minutes)

### Step 1: Add Required Configuration Files

#### 1.1 Create Pyright Configuration

Create `/workspace/pyrightconfig.json`:

```json
{
  "pythonVersion": "3.11",
  "typeCheckingMode": "basic",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "exclude": [
    "**/node_modules",
    "**/__pycache__",
    "**/.*"
  ]
}
```

**Why?** Configures type checker to target Python 3.11+ with basic strictness.

#### 1.2 Update pytest.ini

Edit `/workspace/pytest.ini` to add parallel execution and enhanced markers:

```ini
[pytest]
minversion = 6.0
pythonpath = src
testpaths = tests
addopts =
    -n auto
    -v
    --strict-markers
    --tb=short
    --cov=c2.pas.aal2
    --cov-report=term-missing
    --cov-report=xml
    --cov-branch
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

**Why?** Enables parallel test execution (60-80% faster) and branch coverage.

#### 1.3 Add Development Dependencies

Edit `/workspace/pyproject.toml` to include CI tools:

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

**Why?** Ensures linting, type checking, and testing tools are available in CI.

#### 1.4 Update Lockfile

```bash
cd /workspace
uv lock
```

**Why?** Generates `uv.lock` with pinned versions for reproducible CI builds.

---

### Step 2: Create GitHub Actions Workflow

Create `/workspace/.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: ['**']
  pull_request:
    types: [opened, synchronize, reopened]

env:
  UV_CACHE_DIR: /tmp/.uv-cache

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python 3.11
        run: uv python install 3.11

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: |
            /tmp/.uv-cache
            .venv
          key: ${{ runner.os }}-py3.11-uv-${{ hashFiles('**/uv.lock') }}
          restore-keys: |
            ${{ runner.os }}-py3.11-uv-

      - name: Install dependencies
        run: uv sync --frozen --all-extras

      - name: Run ruff linting
        run: uv run ruff check .

      - name: Run pyright type checking
        run: uv run pyright

      - name: Prune cache
        run: uv cache prune --ci

  test:
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Cache uv dependencies
        uses: actions/cache@v4
        with:
          path: |
            /tmp/.uv-cache
            .venv
          key: ${{ runner.os }}-py${{ matrix.python-version }}-uv-${{ hashFiles('**/uv.lock') }}
          restore-keys: |
            ${{ runner.os }}-py${{ matrix.python-version }}-uv-

      - name: Install dependencies
        run: uv sync --frozen --all-extras

      - name: Run tests with coverage
        run: uv run pytest --cov --cov-report=xml --cov-report=term-missing

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
        env:
          CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

      - name: Prune cache
        run: uv cache prune --ci
```

**Why?** This workflow runs linting/type checking on Python 3.11 and tests on all three Python versions in parallel.

---

### Step 3: Commit and Push

```bash
git add .github/workflows/ci.yml pyrightconfig.json pytest.ini pyproject.toml uv.lock
git commit -m "Add GitHub Actions CI pipeline"
git push
```

**Result**: CI automatically runs on this push!

---

## Verifying CI Setup

### Check Workflow Runs

1. Go to GitHub repository
2. Click **Actions** tab
3. See your workflow running

**Expected**:
- 4 jobs running in parallel:
  - `lint-and-typecheck`
  - `test (3.11)`
  - `test (3.12)`
  - `test (3.13)`

### View Job Logs

Click on any job to see detailed logs:

- **Lint job**: Shows ruff output (any style violations)
- **Type check job**: Shows pyright output (any type errors)
- **Test jobs**: Shows pytest output (test results, coverage)

---

## Testing CI Pipeline

### Test 1: Verify CI Passes on Clean Code

**Expected**: All 4 jobs should pass with green checkmarks ✓

If any job fails, check logs for details and fix issues.

### Test 2: Introduce Intentional Linting Error

```bash
# Edit a Python file to add unused import
echo "import os  # This will fail linting" >> src/c2/pas/aal2/__init__.py
git add .
git commit -m "Test: Intentional linting error"
git push
```

**Expected**:
- `lint-and-typecheck` job FAILS ✗
- Error message: "Unused import: os"
- Other jobs may still pass

### Test 3: Fix the Error

```bash
# Remove the unused import
git revert HEAD
git push
```

**Expected**: All jobs pass again ✓

---

## Using CI in Pull Requests

### Creating a PR

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes, commit, push
3. Create pull request on GitHub

**CI Behavior**:
- CI runs automatically when PR is created
- CI re-runs on every new commit to PR
- PR shows status checks:
  - ✓ lint-and-typecheck
  - ✓ test (3.11)
  - ✓ test (3.12)
  - ✓ test (3.13)

### Requiring CI Before Merge

**Enable Branch Protection** (recommended):

1. Go to Settings → Branches
2. Add branch protection rule for `main`
3. Check **Require status checks to pass before merging**
4. Select these status checks:
   - `lint-and-typecheck`
   - `test (3.11)`
   - `test (3.12)`
   - `test (3.13)`

**Result**: PR cannot be merged if any CI check fails!

---

## Running CI Checks Locally

Before pushing, run CI checks locally to catch issues early:

### Run Linting

```bash
uv run ruff check .
```

**Fix automatically** (if possible):
```bash
uv run ruff check --fix .
```

### Run Type Checking

```bash
uv run pyright
```

### Run Tests

**All tests**:
```bash
uv run pytest
```

**With coverage**:
```bash
uv run pytest --cov --cov-report=term-missing
```

**Fast tests only**:
```bash
uv run pytest -m "unit and not slow"
```

**Specific Python version** (requires that version installed):
```bash
uv run --python 3.12 pytest
```

---

## Understanding CI Output

### Successful Run

```
✓ lint-and-typecheck (1m 23s)
  ✓ Run ruff linting - No issues found
  ✓ Run pyright type checking - 0 errors

✓ test (3.11) (2m 15s)
  ✓ Run tests - 45 passed, 0 failed
  ✓ Coverage: 87%

✓ test (3.12) (2m 18s)
  ✓ Run tests - 45 passed, 0 failed
  ✓ Coverage: 87%

✓ test (3.13) (2m 20s)
  ✓ Run tests - 45 passed, 0 failed
  ✓ Coverage: 87%

Total duration: 2m 20s (parallel execution)
```

### Failed Run (Example)

```
✗ lint-and-typecheck (0m 45s)
  ✓ Run ruff linting - No issues found
  ✗ Run pyright type checking - 3 errors
    src/c2/pas/aal2/plugin.py:42:12 - error: Type "None" cannot be assigned to type "str"
    src/c2/pas/aal2/utils.py:18:8 - error: Argument missing for parameter "username"
    ...

✓ test (3.11) (2m 10s)
✓ test (3.12) (2m 12s)
✗ test (3.13) (1m 05s)
  ✗ Run tests - 44 passed, 1 failed
    FAILED tests/test_auth.py::test_passkey_login - AssertionError: expected True
```

**Action**: Fix type errors and failing test, then push again.

---

## Troubleshooting

### Problem: "Command not found: ruff" or "pyright"

**Cause**: Development dependencies not installed

**Solution**:
```bash
uv sync --all-extras
```

### Problem: CI runs slow (>10 minutes)

**Check**:
1. Are tests parallelized? (Should see `-n auto` in pytest command)
2. Is cache working? (Check "Cache uv dependencies" step - should show "Cache hit")
3. Are there slow tests? (Run `pytest --durations=10` to find slowest tests)

**Solutions**:
- Mark slow tests: `@pytest.mark.slow`
- Exclude slow tests in CI: `pytest -m "not slow"`
- Optimize slow tests or run them in nightly builds

### Problem: Cache not working

**Symptoms**: "Cache restored: no" in logs, slow dependency installation every run

**Causes**:
1. `uv.lock` file changed (expected behavior)
2. Cache size exceeded 10GB (old caches evicted)
3. Cache key mismatch

**Solutions**:
1. Verify `uv.lock` is committed: `git ls-files uv.lock`
2. Check cache size: Settings → Actions → Caches
3. Review cache key in workflow file

### Problem: Tests pass locally but fail in CI

**Common Causes**:
1. **Missing dependencies**: Add to `pyproject.toml` dependencies
2. **Environment differences**: Check for hardcoded paths, environment variables
3. **Test isolation**: Tests may depend on execution order

**Solutions**:
1. Run tests locally with same Python version: `uv run --python 3.13 pytest`
2. Run tests in random order: `uv run pytest --random-order`
3. Check CI logs for specific error messages

### Problem: Type errors only in CI

**Cause**: Local pyright version differs from CI version

**Solution**:
```bash
# Use same version as CI
uv run pyright

# Check version
uv run pyright --version
```

---

## Performance Optimization Tips

### 1. Cache Optimization

**Monitor cache effectiveness**:
- Check "Cache uv dependencies" step in logs
- Cache hit: ~20 seconds to restore
- Cache miss: ~1-2 minutes to install

**Improve cache hits**:
- Commit `uv.lock` (enables exact cache matching)
- Avoid frequent dependency changes
- Use `uv sync --frozen` (prevents lock file updates)

### 2. Test Optimization

**Identify slow tests**:
```bash
uv run pytest --durations=10
```

**Mark and skip slow tests**:
```python
@pytest.mark.slow
def test_comprehensive_integration():
    # Long-running test
    pass
```

**CI**: Run fast tests on every push, slow tests nightly:
```yaml
# Fast tests (default)
- run: uv run pytest -m "not slow"

# Slow tests (scheduled workflow)
- run: uv run pytest -m slow
```

### 3. Parallel Execution

**Current**: `-n auto` uses all available CPU cores

**Customize**:
```yaml
# More workers (if tests are very fast)
- run: uv run pytest -n 8

# Fewer workers (if tests use a lot of memory)
- run: uv run pytest -n 2
```

---

## Advanced Usage

### Running Only Specific Checks

**Lint only**:
```yaml
- run: uv run ruff check .
```

**Type check only**:
```yaml
- run: uv run pyright
```

**Unit tests only**:
```yaml
- run: uv run pytest -m unit
```

**Integration tests only**:
```yaml
- run: uv run pytest -m integration
```

### Adding More Checks

**Security scanning** (bandit):
```yaml
- name: Security scan
  run: |
    uv pip install bandit
    uv run bandit -r src/
```

**Code formatting check** (ruff format):
```yaml
- name: Check formatting
  run: uv run ruff format --check .
```

**Documentation build** (sphinx):
```yaml
- name: Build documentation
  run: |
    uv pip install sphinx
    cd docs && uv run make html
```

### Matrix Expansion

**Test across multiple OSes**:
```yaml
test:
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest, windows-latest]
      python-version: ["3.11", "3.12", "3.13"]
  runs-on: ${{ matrix.os }}
```

---

## Monitoring and Maintenance

### Weekly Checklist

- [ ] Review CI run times (target: <5 minutes)
- [ ] Check cache hit rate (target: >80%)
- [ ] Review coverage trends (via Codecov dashboard)
- [ ] Update dependencies: `uv lock --upgrade`

### Monthly Checklist

- [ ] Update GitHub Actions versions (check for @v5, etc.)
- [ ] Review and update pinned tool versions (ruff, pyright)
- [ ] Clean up old caches (Settings → Actions → Caches)
- [ ] Review test suite performance (identify new slow tests)

---

## Getting Help

### CI Fails with Unclear Error

1. **Check job logs**: Click on failed job, expand failed step
2. **Reproduce locally**: Run the exact command from CI locally
3. **Check GitHub Actions status**: https://www.githubstatus.com/
4. **Re-run jobs**: Click "Re-run failed jobs" (may be transient issue)

### Need to Customize CI

- **Workflow documentation**: `.github/workflows/ci.yml` has inline comments
- **Research document**: `specs/004-github-actions-ci/research.md` explains all decisions
- **Contracts**: `specs/004-github-actions-ci/contracts/workflow-contract.md` defines behavior

### Questions?

- Check feature spec: `specs/004-github-actions-ci/spec.md`
- Review research: `specs/004-github-actions-ci/research.md`
- Read GitHub Actions docs: https://docs.github.com/actions

---

## Summary

You now have:

✓ Automated CI pipeline running on every push and PR
✓ Linting (ruff) and type checking (pyright) on Python 3.11
✓ Tests running on Python 3.11, 3.12, 3.13 in parallel
✓ Fast CI runs (~3-5 minutes) with dependency caching
✓ Coverage reports uploaded to Codecov
✓ PR status checks blocking merges on failures

**Next Steps**:
1. Enable branch protection rules (recommended)
2. Set up Codecov integration for coverage tracking
3. Add pre-commit hooks for local checks before push
4. Customize markers and test organization for your workflow
