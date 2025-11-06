# Tasks: GitHub Actions CI Pipeline

**Input**: Design documents from `/specs/004-github-actions-ci/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are NOT required for this infrastructure feature. Configuration correctness will be validated by actually running the CI workflow.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **CI Configuration**: `.github/workflows/` at repository root
- **Project Configuration**: Repository root (`pyrightconfig.json`, `pytest.ini`, `pyproject.toml`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare project configuration files and development dependencies

- [ ] T001 Create `.github/workflows/` directory structure
- [ ] T002 [P] Add development dependencies to `/workspace/pyproject.toml` (pytest>=8.0, pytest-cov>=5.0, pytest-xdist>=3.5, pyright>=1.1, ruff>=0.8.0,<0.9.0)
- [ ] T003 [P] Create pyrightconfig.json in `/workspace/pyrightconfig.json` with Python 3.11 target and basic type checking mode
- [ ] T004 [P] Update pytest.ini in `/workspace/pytest.ini` to add new markers (slow, smoke, webauthn) and enable parallel execution with -n auto

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Update lockfile by running `uv lock` to include new development dependencies
- [ ] T006 Verify existing tests pass with new pytest configuration by running `uv run pytest`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automated Code Quality Checks on Pull Requests (Priority: P1) 🎯 MVP

**Goal**: Developers get immediate feedback on code quality, linting, and type errors when submitting pull requests

**Independent Test**: Create a PR with intentionally failing code (linting error) and verify CI reports failure with clear error message

### Implementation for User Story 1

- [ ] T007 [US1] Create base CI workflow file in `.github/workflows/ci.yml` with name, triggers (push, pull_request), and environment variables (UV_CACHE_DIR)
- [ ] T008 [US1] Add lint-and-typecheck job to `.github/workflows/ci.yml` that runs on ubuntu-latest with Python 3.11
- [ ] T009 [US1] Configure checkout step in lint-and-typecheck job using actions/checkout@v4
- [ ] T010 [US1] Configure uv setup step in lint-and-typecheck job using astral-sh/setup-uv@v5
- [ ] T011 [US1] Configure Python 3.11 installation step in lint-and-typecheck job
- [ ] T012 [US1] Add cache configuration step for uv dependencies with lockfile-based cache key in lint-and-typecheck job
- [ ] T013 [US1] Add dependency installation step using `uv sync --frozen --all-extras` in lint-and-typecheck job
- [ ] T014 [US1] Add ruff linting step using `uv run ruff check .` in lint-and-typecheck job
- [ ] T015 [US1] Add pyright type checking step using `uv run pyright` in lint-and-typecheck job
- [ ] T016 [US1] Add cache pruning step using `uv cache prune --ci` in lint-and-typecheck job

**Checkpoint**: At this point, lint and type check CI should run automatically on pushes/PRs and report quality issues

---

## Phase 4: User Story 2 - Multi-Version Test Coverage (Priority: P1)

**Goal**: Development team has confidence that code works across Python 3.11, 3.12, and 3.13

**Independent Test**: Introduce version-specific syntax (e.g., Python 3.12+ feature) and verify CI catches incompatibility in appropriate version job

### Implementation for User Story 2

- [ ] T017 [US2] Add test job with matrix strategy to `.github/workflows/ci.yml` for Python versions ["3.11", "3.12", "3.13"]
- [ ] T018 [US2] Configure test job to run on ubuntu-latest with fail-fast: false
- [ ] T019 [US2] Add checkout step to test job using actions/checkout@v4
- [ ] T020 [US2] Add uv setup step to test job using astral-sh/setup-uv@v5
- [ ] T021 [US2] Add Python version installation step using matrix.python-version variable in test job
- [ ] T022 [US2] Add version-specific cache configuration with Python version in cache key for test job
- [ ] T023 [US2] Add dependency installation step using `uv sync --frozen --all-extras` in test job
- [ ] T024 [US2] Add pytest execution step with coverage using `uv run pytest --cov --cov-report=xml --cov-report=term-missing` in test job
- [ ] T025 [US2] Add Codecov upload step using codecov/codecov-action@v4 with fail_ci_if_error: false in test job
- [ ] T026 [US2] Add cache pruning step using `uv cache prune --ci` in test job

**Checkpoint**: At this point, tests should run on all three Python versions in parallel, with version-specific failures clearly attributed

---

## Phase 5: User Story 3 - Automated CI Execution on Every Push (Priority: P2)

**Goal**: Developers get immediate feedback on every push to any branch, enabling rapid iteration

**Independent Test**: Push a commit to a feature branch and verify CI triggers automatically within seconds, showing real-time progress

### Implementation for User Story 3

- [ ] T027 [US3] Verify workflow triggers are configured for all branches (push on `branches: ['**']` already configured in T007)
- [ ] T028 [US3] Add descriptive job names and step names to improve visibility in GitHub Actions UI
- [ ] T029 [US3] Test workflow by pushing to a feature branch and verifying all jobs appear in Actions tab
- [ ] T030 [US3] Verify job failure notifications include links to specific failing jobs and clear error messages

**Checkpoint**: All user stories should now be independently functional - CI runs on every push with comprehensive feedback

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and optimizations that affect multiple user stories

- [ ] T031 [P] Add comments to `.github/workflows/ci.yml` explaining cache strategy, Python version choice for linting, and performance optimizations
- [ ] T032 [P] Create `.github/PULL_REQUEST_TEMPLATE.md` with CI checklist reminder (optional enhancement)
- [ ] T033 Verify complete workflow file follows all recommendations from research.md
- [ ] T034 Test workflow with intentional failures (linting error, type error, test failure) to verify error reporting quality
- [ ] T035 Test workflow with clean code to verify all jobs pass and caching works on second run
- [ ] T036 Measure CI execution time and verify it meets <10 minute requirement (target: 3-5 minutes)
- [ ] T037 Document CI setup in project README with badges for build status (optional enhancement)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start immediately after Foundational
  - User Story 2 (P1): Can run in parallel with US1 (different sections of workflow file)
  - User Story 3 (P2): Builds on US1 and US2 (validates complete workflow)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - Delivers: Lint and type checking CI job
  - Independently testable: Create PR with linting errors

- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on User Story 1
  - Delivers: Multi-version test matrix
  - Independently testable: Push code with version-specific issues
  - NOTE: While both US1 and US2 modify same file, they edit different sections (different job definitions)

- **User Story 3 (P2)**: Depends on US1 and US2 being complete
  - Delivers: Validation that complete workflow triggers correctly and provides good UX
  - Independently testable: Push to branch and observe CI behavior

### Within Each User Story

**User Story 1** (T007-T016):
- T007 creates base file (blocking for T008-T016)
- T008-T016 build up lint-and-typecheck job sequentially
- Each step adds to the same job definition

**User Story 2** (T017-T026):
- T017 adds test job definition (can start after T007 exists)
- T018-T026 build up test job sequentially
- Parallel with US1 if editing different job sections carefully

**User Story 3** (T027-T030):
- All tasks depend on complete workflow from US1 and US2
- Focuses on validation and UX polish

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks marked [P] can run in parallel:
- T002 (pyproject.toml)
- T003 (pyrightconfig.json)
- T004 (pytest.ini)
- Different files, no conflicts

**Phase 2 (Foundational)**: Sequential
- T005 must run after T002 completes (updates lockfile based on new deps)
- T006 must run after T005 completes (validates new config)

**Phase 3-4 (User Stories 1 & 2)**: Limited parallelism
- US1 and US2 both modify `.github/workflows/ci.yml`
- Can work in parallel with careful coordination (different job sections)
- Safer to complete US1 first, then US2

**Phase 6 (Polish)**: All [P] tasks can run in parallel:
- T031 (workflow comments)
- T032 (PR template)
- Different files, no conflicts

---

## Parallel Example: Setup Phase

```bash
# Launch all Phase 1 setup tasks together:
Task: "Add development dependencies to /workspace/pyproject.toml"
Task: "Create pyrightconfig.json in /workspace/pyrightconfig.json"
Task: "Update pytest.ini in /workspace/pytest.ini"
```

## Parallel Example: Polish Phase

```bash
# Launch all Phase 6 polish tasks together:
Task: "Add comments to .github/workflows/ci.yml"
Task: "Create .github/PULL_REQUEST_TEMPLATE.md"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

Both User Story 1 and User Story 2 are marked P1 (highest priority) because:
- US1: Code quality checks are the foundation of any CI pipeline
- US2: Multi-version testing is the core requirement from user request

**MVP Delivery**:
1. Complete Phase 1: Setup (T001-T004) → ~10 minutes
2. Complete Phase 2: Foundational (T005-T006) → ~5 minutes
3. Complete Phase 3: User Story 1 (T007-T016) → ~30 minutes
4. **STOP and VALIDATE**: Push code with linting errors, verify CI fails appropriately
5. Complete Phase 4: User Story 2 (T017-T026) → ~30 minutes
6. **STOP and VALIDATE**: Push code with version-specific test, verify matrix works
7. **MVP READY**: CI pipeline detects code quality issues and version incompatibilities

Total MVP time estimate: ~90 minutes

### Full Feature Delivery

Add User Story 3 for complete UX polish:
1. Complete MVP (Phases 1-4)
2. Complete Phase 5: User Story 3 (T027-T030) → ~20 minutes
3. Complete Phase 6: Polish (T031-T037) → ~30 minutes
4. **COMPLETE**: Full-featured CI pipeline with excellent developer experience

Total feature time estimate: ~2.5 hours

### Incremental Delivery Strategy

1. **Iteration 1 (MVP)**: Complete US1 & US2
   - Delivers core value: Automated quality checks across Python versions
   - Can deploy/use immediately
   - Provides immediate developer value

2. **Iteration 2 (Polish)**: Add US3 & Polish phase
   - Improves UX and documentation
   - Validates complete workflow behavior
   - Adds nice-to-have enhancements

### Parallel Team Strategy

With 2 developers:

1. **Together**: Complete Phase 1 (Setup) and Phase 2 (Foundational)
2. **Split work**:
   - Developer A: User Story 1 (T007-T016) - Lint and type check job
   - Developer B: Prepare for User Story 2 (review research.md, plan test job structure)
3. **Sequential**: After US1 complete, Developer B implements US2 (T017-T026)
4. **Together**: Validate and test complete workflow (US3)
5. **Split work**: Polish tasks (T031-T032 in parallel, then T033-T037 together)

**Note**: Because both US1 and US2 edit the same file (ci.yml), true parallel work requires careful coordination or git merge conflict resolution. Sequential implementation (US1 → US2) is safer and only slightly slower.

---

## Validation Checklist

After completing each user story, validate independently:

**User Story 1 Validation**:
- [ ] Lint job appears in GitHub Actions UI
- [ ] Pushing code with unused import triggers lint failure
- [ ] Error message clearly identifies the linting issue
- [ ] Pushing code with type error triggers type check failure
- [ ] Error message clearly identifies the type issue
- [ ] Pushing clean code results in green checkmark for lint-and-typecheck job

**User Story 2 Validation**:
- [ ] Test matrix shows 3 parallel jobs (Python 3.11, 3.12, 3.13)
- [ ] All jobs run even if one fails (fail-fast: false works)
- [ ] Test failure clearly shows which Python version failed
- [ ] Coverage report uploads successfully to Codecov
- [ ] Cache works (second run is faster than first run)

**User Story 3 Validation**:
- [ ] CI triggers within 30 seconds of pushing to any branch
- [ ] GitHub Actions UI shows real-time progress
- [ ] Job failure includes link to specific failing job
- [ ] Error messages are actionable and clear
- [ ] PR shows all 4 status checks (lint-and-typecheck, test 3.11, test 3.12, test 3.13)

**Complete Feature Validation** (after all phases):
- [ ] Total CI time < 10 minutes (target: 3-5 minutes with caching)
- [ ] All jobs pass on clean code
- [ ] Cache hit on second run (visible in logs)
- [ ] Workflow file has clear comments explaining design decisions
- [ ] Documentation exists for using and troubleshooting CI

---

## Notes

- **[P] tasks** = Different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- **No test tasks**: This is infrastructure configuration, validated by running the actual workflow
- **File path conflicts**: US1 and US2 both edit `.github/workflows/ci.yml` - coordinate carefully or run sequentially
- **Incremental value**: Each user story adds standalone value - US1 alone provides useful linting, US2 adds version testing
- **Cache behavior**: First CI run will be slower (no cache), second run should be significantly faster
- **Performance target**: Complete pipeline should run in 3-5 minutes with caching, well under 10-minute requirement

---

## Task Count Summary

- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 2 tasks
- **Phase 3 (User Story 1 - P1)**: 10 tasks
- **Phase 4 (User Story 2 - P1)**: 10 tasks
- **Phase 5 (User Story 3 - P2)**: 4 tasks
- **Phase 6 (Polish)**: 7 tasks

**Total**: 37 tasks

**MVP Scope** (US1 + US2): 26 tasks
**Full Feature**: 37 tasks

**Parallel Opportunities**:
- Phase 1: 3 tasks can run in parallel (T002, T003, T004)
- Phase 6: 2 tasks can run in parallel (T031, T032)
- Total parallelizable tasks: 5 (13.5% of all tasks)

**Critical Path** (sequential tasks that determine minimum time):
Phase 1 (T001) → Phase 2 (T005 → T006) → Phase 3 (T007-T016) → Phase 4 (T017-T026) → Phase 5 (T027-T030) → Phase 6 (T033-T037)

**Estimated Implementation Time**:
- With 1 developer: ~2.5 hours (sequential execution)
- With 2 developers: ~2 hours (some parallel work in Setup and Polish phases)
