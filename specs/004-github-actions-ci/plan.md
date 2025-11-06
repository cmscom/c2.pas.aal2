# Implementation Plan: GitHub Actions CI Pipeline

**Branch**: `004-github-actions-ci` | **Date**: 2025-11-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-github-actions-ci/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements a GitHub Actions CI pipeline that automatically runs code quality checks (ruff linting, type checking) and pytest test suite across Python 3.11, 3.12, and 3.13 on every push. The pipeline uses uv for fast dependency management and must complete within 10 minutes while providing clear failure feedback to developers.

## Technical Context

**Language/Version**: Python 3.11, 3.12, 3.13 (multi-version testing)
**Primary Dependencies**: uv (package manager), pytest (testing), ruff (linting), pyright (type checking)
**Storage**: N/A (CI configuration only)
**Testing**: pytest for unit/integration tests with pytest-xdist for parallel execution
**Target Platform**: GitHub Actions (ubuntu-latest runners)
**Project Type**: Infrastructure/DevOps (CI/CD configuration)
**Performance Goals**: Complete full CI pipeline within 10 minutes
**Constraints**:
- Must work with existing project structure (Plone.PAS plugin)
- Must cache dependencies for faster subsequent runs
- Must provide clear error messages for failures
- Must run on standard GitHub Actions runners (no self-hosted required)
**Scale/Scope**:
- 3 Python versions to test
- Multiple job types (lint, type check, test matrix)
- Single workflow file
- Linting and type checking run on ONE Python version (3.11) for efficiency
- Pytest uses markers (unit, integration, slow, smoke, webauthn) for selective test execution
- Parallel test execution enabled with -n auto for 60-80% performance improvement

**Decisions (from research.md)**:
- Type checker: Pyright (3-5x faster than mypy, better Python 3.11-3.13 support)
- Linting strategy: Run ruff on Python 3.11 only (results are version-independent)
- Caching: Manual cache management with lockfile-based keys for optimal performance
- Test optimization: Parallel execution with pytest-xdist, branch coverage enabled

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Check (Before Phase 0)**: ✅ PASS (N/A - Infrastructure feature)

**Re-evaluation (After Phase 1)**: ✅ PASS (N/A - Infrastructure feature)

**Rationale**: This feature creates CI/CD infrastructure configuration (GitHub Actions workflow files) rather than application code. The constitution template appears to be designed for application development (libraries, CLI tools, APIs). Since this is purely infrastructure configuration:

- No new libraries or services are being created
- No test-first development is required for YAML configuration (though workflow correctness will be verified)
- No versioning concerns (workflow files are version-controlled with the repository)
- No runtime observability requirements (GitHub Actions provides built-in logging)

The feature does align with good practices:
- Simple, declarative configuration
- Clear purpose (automated quality checks)
- Independently testable (can verify by triggering workflows)

**Post-Phase 1 Notes**:
- Design artifacts (data-model.md, contracts/, quickstart.md) have been created
- All NEEDS CLARIFICATION items from Technical Context have been resolved via research.md
- No constitutional violations identified in the design phase

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── ci.yml           # Main CI workflow (to be created)

src/                     # Existing Plone.PAS plugin source
└── c2/pas/aal2/

tests/                   # Existing test suite
```

**Structure Decision**: This feature only adds GitHub Actions workflow configuration. The existing project structure remains unchanged. The workflow file will be placed in the standard `.github/workflows/` directory following GitHub Actions conventions.

## Complexity Tracking

N/A - No constitution violations. This is an infrastructure configuration feature.
