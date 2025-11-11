# Tasks: AAL2 Protection for Plone Admin Interfaces

**Input**: Design documents from `/specs/006-aal2-admin-protection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in specification - focusing on implementation tasks

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This is a Plone add-on package extending `c2.pas.aal2`:
- **Main package**: `src/c2/pas/aal2/`
- **Tests**: `tests/` at repository root
- **Profiles**: `src/c2/pas/aal2/profiles/default/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and module structure

- [X] T001 Create admin module directory structure at src/c2/pas/aal2/admin/
- [X] T002 [P] Create admin/__init__.py module initialization file
- [X] T003 [P] Create tests/test_admin_protection.py test file
- [X] T004 [P] Create tests/test_admin_challenge.py test file
- [X] T005 [P] Create tests/test_admin_config.py test file
- [X] T006 [P] Create tests/test_admin_status.py test file
- [X] T007 [P] Create tests/test_integration_admin.py integration test file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create registry schema interface in src/c2/pas/aal2/admin/interfaces.py with IAAL2AdminSettings
- [X] T009 [P] Create admin/configure.zcml with subscriber registration boilerplate
- [X] T010 [P] Update src/c2/pas/aal2/configure.zcml to include admin/configure.zcml
- [X] T011 Create profiles/default/registry.xml with protected_patterns and enabled settings
- [X] T012 [P] Create upgrade step file src/c2/pas/aal2/profiles/default/upgrades/upgrade_to_006.py
- [X] T013 [P] Update profiles/default/upgrades/configure.zcml to register upgrade_to_006
- [X] T014 [P] Update profiles/default/metadata.xml to version 006

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Admin Interface AAL2 Protection (Priority: P1) 🎯 MVP

**Goal**: Intercept admin requests, check AAL2 validity, redirect to challenge if expired

**Independent Test**: Admin user logs in, waits 20 minutes, accesses control panel, gets redirected to challenge page, authenticates with passkey, successfully accesses control panel

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement get_protected_patterns() with RAM caching in src/c2/pas/aal2/admin/protection.py
- [X] T016 [P] [US1] Implement is_protected_url(url) with fnmatch pattern matching in src/c2/pas/aal2/admin/protection.py
- [X] T017 [US1] Implement check_admin_access(request, user) in src/c2/pas/aal2/admin/protection.py (depends on T015, T016)
- [X] T018 [P] [US1] Implement store_redirect_context(request, original_url) in src/c2/pas/aal2/admin/protection.py
- [X] T019 [P] [US1] Implement get_redirect_context(request) in src/c2/pas/aal2/admin/protection.py
- [X] T020 [P] [US1] Implement clear_redirect_context(request) in src/c2/pas/aal2/admin/protection.py
- [X] T021 [US1] Create check_admin_aal2_subscriber(event) in src/c2/pas/aal2/admin/subscriber.py (depends on T017, T018)
- [X] T022 [US1] Register subscriber in admin/configure.zcml for IPubBeforeCommit event (depends on T021)
- [X] T023 [P] [US1] Add admin access audit logging to utils/audit.py for admin_access_allowed and admin_access_challenged events
- [X] T024 [US1] Integrate audit logging in subscriber.py (depends on T021, T023)
- [X] T025 [US1] Add cache invalidation handler for registry changes in src/c2/pas/aal2/admin/protection.py

**Checkpoint**: At this point, admin URLs should be intercepted, AAL2 checked, and redirects issued for expired sessions

---

## Phase 4: User Story 3 - Clear Re-authentication UX (Priority: P2)

**Goal**: Display clear challenge page with context, handle passkey authentication, redirect to original URL

**Independent Test**: Access protected admin URL with expired AAL2, see challenge page with original URL displayed, complete passkey auth, automatically redirect to original page

**Note**: Implementing US3 before US2 because challenge UX is needed for US1 to be fully functional

### Implementation for User Story 3

- [X] T026 [P] [US3] Create AdminAAL2ChallengeView class in src/c2/pas/aal2/browser/views.py with __call__ method
- [X] T027 [P] [US3] Implement handle_authentication() method in AdminAAL2ChallengeView for POST handling
- [X] T028 [P] [US3] Create admin_aal2_challenge.pt template in src/c2/pas/aal2/browser/templates/
- [X] T029 [US3] Register @@admin-aal2-challenge view in browser/configure.zcml (depends on T026, T028)
- [X] T030 [P] [US3] Add admin challenge audit logging events (admin_challenge_success, admin_challenge_failure) to utils/audit.py
- [X] T031 [US3] Integrate audit logging in AdminAAL2ChallengeView (depends on T027, T030)
- [X] T032 [P] [US3] Add JavaScript for passkey authentication UI in browser/static/js/admin-aal2-challenge.js
- [X] T033 [US3] Link JavaScript resource in admin_aal2_challenge.pt template (depends on T028, T032)
- [X] T034 [P] [US3] Register JavaScript resource in profiles/default/jsregistry.xml (if not already managed by feature 005)

**Checkpoint**: Challenge page should display with context, accept passkey auth, and redirect users back to original admin page

---

## Phase 5: User Story 2 - Protected Admin Interface Configuration (Priority: P2)

**Goal**: Provide control panel interface for managing protected URL patterns

**Independent Test**: Access AAL2 admin settings, view default protected patterns, add new pattern, save, verify new pattern triggers AAL2 check

### Implementation for User Story 2

- [X] T035 [P] [US2] Extend IAAL2ControlPanel schema in src/c2/pas/aal2/controlpanel/interfaces.py with admin protection fields
- [X] T036 [P] [US2] Create AAL2AdminProtectionControlPanelView in src/c2/pas/aal2/controlpanel/views.py
- [X] T037 [P] [US2] Create admin_protection_settings.pt template in src/c2/pas/aal2/controlpanel/templates/
- [X] T038 [US2] Register control panel view in controlpanel/configure.zcml (depends on T036, T037)
- [X] T039 [US2] Update profiles/default/controlpanel.xml to add AAL2 Admin Protection panel entry (depends on T036)
- [X] T040 [P] [US2] Add pattern validation logic in controlpanel/views.py to prevent invalid patterns
- [X] T041 [P] [US2] Add UI feedback for pattern testing (show which URLs match patterns) in template
- [X] T042 [US2] Integrate pattern testing JavaScript in browser/static/js/admin-pattern-tester.js

**Checkpoint**: Control panel should allow viewing, adding, removing protected patterns with validation and testing

---

## Phase 6: User Story 4 - AAL2 Status Visibility (Priority: P3)

**Goal**: Display AAL2 authentication status in admin interface header with countdown

**Independent Test**: Log in as admin, view header showing remaining AAL2 time, wait for countdown, see warning when <2 minutes remain

### Implementation for User Story 4

- [X] T043 [P] [US4] Create AdminAAL2StatusViewlet class in src/c2/pas/aal2/browser/viewlets.py
- [X] T044 [P] [US4] Implement aal2_info() method returning status dict in AdminAAL2StatusViewlet
- [X] T045 [P] [US4] Create admin_aal2_status.pt viewlet template in src/c2/pas/aal2/browser/templates/
- [X] T046 [US4] Register viewlet in profiles/default/viewlets.xml for plone.portalheader manager (depends on T043, T045)
- [X] T047 [P] [US4] Create admin-aal2-status.js for countdown timer in browser/static/js/
- [X] T048 [US4] Link JavaScript in admin_aal2_status.pt template (depends on T045, T047)
- [X] T049 [P] [US4] Register JavaScript resource in profiles/default/jsregistry.xml
- [X] T050 [P] [US4] Add CSS styling for status display and warnings in browser/static/css/admin-aal2-status.css
- [X] T051 [US4] Register CSS resource in profiles/default/cssregistry.xml (or equivalent Plone 5.2 resource registry)

**Checkpoint**: All user stories should now be independently functional with full UX

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T052 [P] Add comprehensive docstrings to all admin protection modules
- [X] T053 [P] Update README.md with admin protection feature documentation
- [X] T054 [P] Add inline comments for complex pattern matching and caching logic
- [X] T055 [P] Verify performance targets (<10ms AAL2 check, <5ms pattern match) with profiling
- [X] T056 [P] Add security validation for redirect URL (same-origin check)
- [X] T057 [P] Add loop prevention logic (max 3 challenge attempts)
- [X] T058 [P] Test multi-tab scenario (authenticate in one tab, verify other tabs work)
- [X] T059 [P] Test edge cases: AAL2 disabled, no patterns configured, anonymous user
- [X] T060 [P] Verify backward compatibility with features 001-005
- [X] T061 Run quickstart.md validation steps
- [X] T062 Code review and refactoring for clarity

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - **User Story 1 (P1)**: Core protection - start first after Foundational
  - **User Story 3 (P2)**: Challenge UX - needed for US1 to be complete, so next priority
  - **User Story 2 (P2)**: Configuration UI - can proceed once US1+US3 work
  - **User Story 4 (P3)**: Status display - purely additive, can proceed anytime after US1
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after US1 tasks T015-T020 complete (needs protection.py functions) - Completes US1 functionality
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent but benefits from US1 being testable
- **User Story 4 (P3)**: Can start after US1 complete - Uses AAL2 session data

### Within Each User Story

- **US1**: Pattern matching → Access checking → Session management → Subscriber → Audit logging → Cache invalidation
- **US3**: View class → Template → Authentication handler → JavaScript → Audit logging
- **US2**: Schema → View → Template → Registration → Validation → Testing UI
- **US4**: Viewlet class → Template → JavaScript countdown → CSS styling → Registration

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T002-T007 can all run in parallel (different files)

**Foundational Phase (Phase 2)**:
- T009, T010, T012, T013, T014 can run in parallel (different files)

**User Story 1**:
- T015, T016, T018, T019, T020, T023 can run in parallel (different functions/files)
- After T015-T020 complete: T021 can start
- T025 can run anytime after T015

**User Story 3**:
- T026, T027, T028, T030, T032 can run in parallel
- T034 can run independently

**User Story 2**:
- T035, T036, T037, T040, T041 can run in parallel
- T042 can run independently

**User Story 4**:
- T043, T044, T045, T047, T050 can run in parallel
- T049, T051 can run independently

**Polish Phase**:
- T052-T060 can all run in parallel (documentation, testing, validation)

---

## Parallel Example: User Story 1

```bash
# After Foundational phase complete, launch these User Story 1 tasks together:
Task: "Implement get_protected_patterns() with RAM caching in src/c2/pas/aal2/admin/protection.py"
Task: "Implement is_protected_url(url) with fnmatch pattern matching in src/c2/pas/aal2/admin/protection.py"
Task: "Implement store_redirect_context(request, original_url) in src/c2/pas/aal2/admin/protection.py"
Task: "Implement get_redirect_context(request) in src/c2/pas/aal2/admin/protection.py"
Task: "Implement clear_redirect_context(request) in src/c2/pas/aal2/admin/protection.py"
Task: "Add admin access audit logging to utils/audit.py for admin_access_allowed and admin_access_challenged events"

# After those complete, continue with:
Task: "Implement check_admin_access(request, user) in src/c2/pas/aal2/admin/protection.py"
Task: "Create check_admin_aal2_subscriber(event) in src/c2/pas/aal2/admin/subscriber.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (core protection)
4. Complete Phase 4: User Story 3 (challenge UX to complete US1)
5. **STOP and VALIDATE**: Test admin protection end-to-end
   - Access control panel → get challenge → authenticate → access granted
   - Verify AAL2 timestamp check works
   - Verify redirect preserves original URL
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + 3 → Test independently → Deploy/Demo (MVP - core protection works!)
3. Add User Story 2 → Test independently → Deploy/Demo (configuration added)
4. Add User Story 4 → Test independently → Deploy/Demo (status display added)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (T015-T025)
   - Developer B: User Story 2 (T035-T042) - can start immediately
   - Developer C: User Story 4 (T043-T051) - waits for US1 T015-T020
3. Once US1 T015-T020 complete:
   - Developer A or C: User Story 3 (T026-T034)
4. Stories integrate naturally through shared infrastructure

---

## Task Summary

**Total Tasks**: 62
- **Setup**: 7 tasks
- **Foundational**: 7 tasks (BLOCKING)
- **User Story 1 (P1)**: 11 tasks - Core admin protection
- **User Story 3 (P2)**: 9 tasks - Challenge UX (completes US1)
- **User Story 2 (P2)**: 8 tasks - Configuration UI
- **User Story 4 (P3)**: 9 tasks - Status display
- **Polish**: 11 tasks

**Parallel Opportunities**: 35 tasks marked [P] can run in parallel within their phase

**Independent Test Criteria**:
- **US1**: Admin with expired AAL2 redirected to challenge, valid AAL2 passes through
- **US3**: Challenge page displays context, authenticates passkey, redirects to original URL
- **US2**: Control panel lists patterns, allows add/remove, changes take effect immediately
- **US4**: Header shows AAL2 status, countdown updates, warning appears when <2 minutes

**Suggested MVP**: User Story 1 + User Story 3 (Tasks T001-T034) = Full admin protection with challenge flow

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Dependencies within US1 managed through task ordering
- US3 depends on US1 protection.py functions, but provides the UX to complete US1
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests not included as they were not explicitly requested in specification
