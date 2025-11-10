# Tasks: Implementation Refinements and Production Readiness

**Input**: Design documents from `/specs/005-implementation-refinements/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: This is a refinement feature with extensive existing test coverage. New test tasks focus on validating that refinements don't break existing functionality (zero regressions).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each refinement.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

This is a Plone add-on package with existing structure:
- **Main package**: `src/c2/pas/aal2/`
- **Tests**: `tests/` at repository root
- **Browser layer**: `src/c2/pas/aal2/browser/`
- **Profiles**: `src/c2/pas/aal2/profiles/default/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare repository for refinement implementation

- [ ] T001 Verify branch 005-implementation-refinements is checked out
- [ ] T002 Verify existing tests pass as baseline (run pytest tests/)
- [ ] T003 [P] Create new directories: src/c2/pas/aal2/storage/, src/c2/pas/aal2/locales/, src/c2/pas/aal2/controlpanel/, src/c2/pas/aal2/catalog/
- [ ] T004 [P] Create __init__.py files for new modules: storage, controlpanel, catalog
- [ ] T005 [P] Create profiles/default/upgrades/ directory for migration code
- [ ] T006 Document current JavaScript inline code for comparison in tests/fixtures/baseline_js.txt

**Checkpoint**: Repository structure ready for refinement work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core changes that multiple user stories depend on

**⚠️ CRITICAL**: These tasks enable multiple user stories but don't complete any single story

- [ ] T007 Update src/c2/pas/aal2/profiles/default/metadata.xml to increment version to 1.0.5
- [ ] T008 Create src/c2/pas/aal2/profiles/default/upgrades/configure.zcml for upgrade step registration
- [ ] T009 Create src/c2/pas/aal2/profiles/default/upgrades/upgrade_to_005.py with placeholder upgrade function

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Externalized JavaScript Assets (Priority: P1) 🎯 MVP

**Goal**: Move all inline JavaScript from .pt templates to external .js files for better maintainability and debugging

**Independent Test**: All WebAuthn flows (registration, login, AAL2 challenge, management) work identically to before. External .js files are visible in browser DevTools Sources tab.

### JavaScript File Creation (Already Complete from Earlier Work)

> **NOTE**: These files were already created during the planning phase. Verify they exist:

- [✓] webauthn-utils.js exists at src/c2/pas/aal2/browser/static/js/webauthn-utils.js
- [✓] webauthn-register.js exists at src/c2/pas/aal2/browser/static/js/webauthn-register.js
- [✓] webauthn-login.js exists at src/c2/pas/aal2/browser/static/js/webauthn-login.js
- [✓] webauthn-aal2.js exists at src/c2/pas/aal2/browser/static/js/webauthn-aal2.js
- [✓] passkey-management.js exists at src/c2/pas/aal2/browser/static/js/passkey-management.js

### Resource Registry Configuration

- [ ] T010 [US1] Create src/c2/pas/aal2/profiles/default/jsregistry.xml with Plone resource registry configuration for all 5 JavaScript files
- [ ] T011 [US1] Add resource dependency order: webauthn-utils.js loads first, then others

### Template Updates

- [ ] T012 [P] [US1] Update src/c2/pas/aal2/browser/templates/register_passkey.pt to remove inline JS and call initPasskeyRegistration()
- [ ] T013 [P] [US1] Update src/c2/pas/aal2/browser/templates/login_with_passkey.pt to remove inline JS and call initPasskeyLogin()
- [ ] T014 [P] [US1] Update src/c2/pas/aal2/browser/templates/enhanced_login.pt to remove inline JS and call initEnhancedLogin()
- [ ] T015 [P] [US1] Update src/c2/pas/aal2/browser/aal2_challenge.pt to remove inline JS and call initAAL2Challenge()
- [ ] T016 [P] [US1] Update src/c2/pas/aal2/browser/templates/manage_passkeys.pt to remove inline JS and call initPasskeyManagement()

### Browser Views for Resource Loading

- [ ] T017 [US1] Add WebAuthnResourcesRegister view class to src/c2/pas/aal2/browser/views.py
- [ ] T018 [US1] Add WebAuthnResourcesLogin view class to src/c2/pas/aal2/browser/views.py
- [ ] T019 [US1] Add WebAuthnResourcesAAL2 view class to src/c2/pas/aal2/browser/views.py
- [ ] T020 [US1] Add WebAuthnResourcesManagement view class to src/c2/pas/aal2/browser/views.py
- [ ] T021 [US1] Register all resource views in src/c2/pas/aal2/browser/configure.zcml

### Testing

- [ ] T022 [US1] Add test_javascript_externalization() to tests/test_browser_views.py - verify no inline <script> tags with JS code in templates
- [ ] T023 [US1] Add test_javascript_resources_loaded() to tests/test_browser_views.py - verify resource registry returns .js files
- [ ] T024 [US1] Manual browser test: Register new passkey and verify flow works (document in test report)
- [ ] T025 [US1] Manual browser test: Login with passkey and verify flow works (document in test report)
- [ ] T026 [US1] Manual browser test: AAL2 challenge and verify flow works (document in test report)
- [ ] T027 [US1] Manual browser test: Manage passkeys and verify flow works (document in test report)
- [ ] T028 [US1] Manual browser test: Open DevTools → Sources and verify external .js files are loaded with correct paths

**Checkpoint**: User Story 1 complete - JavaScript is fully externalized, all WebAuthn flows work identically

---

## Phase 4: User Story 2 - Persistent Audit Logging (Priority: P2)

**Goal**: Store authentication audit events in persistent ZODB storage with query and export capabilities

**Independent Test**: Perform auth actions (register, login, AAL2), query audit logs via Python API, export to CSV/JSON, verify all events recorded with correct timestamps and metadata.

### Storage Module Implementation

- [ ] T029 [P] [US2] Create src/c2/pas/aal2/storage/audit.py with AuditEvent and AuditLogContainer classes per data-model.md
- [ ] T030 [US2] Implement get_audit_container() function in storage/audit.py to retrieve/create container from portal annotations
- [ ] T031 [US2] Implement log_audit_event() function in storage/audit.py with graceful error handling (fail open)
- [ ] T032 [P] [US2] Create src/c2/pas/aal2/storage/query.py with query_audit_logs() function supporting filters
- [ ] T033 [US2] Implement export_audit_logs() function in storage/query.py with CSV and JSON formats
- [ ] T034 [US2] Implement cleanup_old_logs() function in storage/query.py for retention policy enforcement

### Integration with Existing Audit Code

- [ ] T035 [US2] Update src/c2/pas/aal2/utils/audit.py log_registration_start() to call persistent storage
- [ ] T036 [US2] Update src/c2/pas/aal2/utils/audit.py log_registration_success() to call persistent storage
- [ ] T037 [US2] Update src/c2/pas/aal2/utils/audit.py log_registration_failure() to call persistent storage
- [ ] T038 [US2] Update src/c2/pas/aal2/utils/audit.py log_authentication_start() to call persistent storage
- [ ] T039 [US2] Update src/c2/pas/aal2/utils/audit.py log_authentication_success() to call persistent storage
- [ ] T040 [US2] Update src/c2/pas/aal2/utils/audit.py log_authentication_failure() to call persistent storage
- [ ] T041 [US2] Update src/c2/pas/aal2/utils/audit.py log_credential_deleted() to call persistent storage
- [ ] T042 [US2] Update src/c2/pas/aal2/utils/audit.py log_aal2_timestamp_set() to call persistent storage
- [ ] T043 [US2] Update src/c2/pas/aal2/utils/audit.py log_aal2_access_granted() to call persistent storage
- [ ] T044 [US2] Update src/c2/pas/aal2/utils/audit.py log_aal2_access_denied() to call persistent storage

### API Browser Views

- [ ] T045 [US2] Create src/c2/pas/aal2/browser/audit_views.py with AuditLogQueryView class implementing query API from contracts/audit-log-api.yaml
- [ ] T046 [US2] Add AuditLogExportView class to audit_views.py implementing export API
- [ ] T047 [US2] Add AuditLogStatsView class to audit_views.py implementing statistics API
- [ ] T048 [US2] Add AuditLogCleanupView class to audit_views.py implementing manual cleanup API
- [ ] T049 [US2] Register audit views in src/c2/pas/aal2/browser/configure.zcml with "Manage portal" permission

### Testing

- [ ] T050 [P] [US2] Create tests/test_audit_storage.py with test_audit_event_creation()
- [ ] T051 [P] [US2] Add test_audit_container_indexing() to tests/test_audit_storage.py
- [ ] T052 [P] [US2] Add test_query_by_user() to tests/test_audit_storage.py
- [ ] T053 [P] [US2] Add test_query_by_action_type() to tests/test_audit_storage.py
- [ ] T054 [P] [US2] Add test_query_by_date_range() to tests/test_audit_storage.py
- [ ] T055 [P] [US2] Add test_export_csv() to tests/test_audit_storage.py
- [ ] T056 [P] [US2] Add test_export_json() to tests/test_audit_storage.py
- [ ] T057 [P] [US2] Add test_cleanup_old_logs() to tests/test_audit_storage.py
- [ ] T058 [P] [US2] Add test_graceful_failure() to tests/test_audit_storage.py - verify operations continue if audit logging fails
- [ ] T059 [US2] Integration test: Register passkey, query audit logs, verify event exists with correct metadata
- [ ] T060 [US2] Integration test: Perform AAL2 re-auth, query logs, verify timestamp and outcome

**Checkpoint**: User Story 2 complete - Audit logs persist in ZODB, queries work, existing functionality unaffected

---

## Phase 5: User Story 3 - Internationalization Support (Priority: P2)

**Goal**: Add translation catalogs for English, Japanese, Spanish, French, and German

**Independent Test**: Change browser language to Japanese/Spanish/French/German and verify UI displays in that language. Add new translatable string and verify it appears in .pot template.

### Locales Directory Setup

- [ ] T061 [US3] Create directory structure: src/c2/pas/aal2/locales/{en,ja,es,fr,de}/LC_MESSAGES/
- [ ] T062 [US3] Install i18ndude tool (pip install i18ndude) if not present

### Translation Catalog Generation

- [ ] T063 [US3] Run i18ndude rebuild-pot to create src/c2/pas/aal2/locales/c2.pas.aal2.pot template from all source files
- [ ] T064 [US3] Run i18ndude sync to create src/c2/pas/aal2/locales/en/LC_MESSAGES/c2.pas.aal2.po (English baseline)
- [ ] T065 [US3] Run i18ndude sync to create src/c2/pas/aal2/locales/ja/LC_MESSAGES/c2.pas.aal2.po (Japanese)
- [ ] T066 [US3] Run i18ndude sync to create src/c2/pas/aal2/locales/es/LC_MESSAGES/c2.pas.aal2.po (Spanish)
- [ ] T067 [US3] Run i18ndude sync to create src/c2/pas/aal2/locales/fr/LC_MESSAGES/c2.pas.aal2.po (French)
- [ ] T068 [US3] Run i18ndude sync to create src/c2/pas/aal2/locales/de/LC_MESSAGES/c2.pas.aal2.po (German)

### Translation Work

- [ ] T069 [P] [US3] Translate high-priority strings (error messages, button labels) in locales/ja/LC_MESSAGES/c2.pas.aal2.po
- [ ] T070 [P] [US3] Translate high-priority strings in locales/es/LC_MESSAGES/c2.pas.aal2.po
- [ ] T071 [P] [US3] Translate high-priority strings in locales/fr/LC_MESSAGES/c2.pas.aal2.po
- [ ] T072 [P] [US3] Translate high-priority strings in locales/de/LC_MESSAGES/c2.pas.aal2.po

**Note**: Machine translation (DeepL/Google Translate) + human review is acceptable for initial translations. Professional translation service recommended for production.

### Compilation

- [ ] T073 [US3] Compile .po to .mo files for all languages using msgfmt (ja, es, fr, de)
- [ ] T074 [US3] Verify .mo files exist in locales/*/LC_MESSAGES/ directories

### Python Code i18n

- [ ] T075 [US3] Add MessageFactory import to src/c2/pas/aal2/browser/views.py and wrap user-facing strings with _()
- [ ] T076 [US3] Update error messages in src/c2/pas/aal2/utils/webauthn.py to use MessageFactory
- [ ] T077 [US3] Update status messages in src/c2/pas/aal2/browser/audit_views.py to use MessageFactory (if not already)

### Testing

- [ ] T078 [P] [US3] Create tests/test_i18n.py with test_pot_file_exists()
- [ ] T079 [P] [US3] Add test_po_files_exist_for_all_languages() to tests/test_i18n.py
- [ ] T080 [P] [US3] Add test_mo_files_compiled() to tests/test_i18n.py
- [ ] T081 [P] [US3] Add test_message_factory_import() to tests/test_i18n.py
- [ ] T082 [US3] Manual browser test: Set browser language to Japanese, verify passkey registration page displays in Japanese
- [ ] T083 [US3] Manual browser test: Set browser language to Spanish, trigger WebAuthn error, verify error message in Spanish
- [ ] T084 [US3] Manual browser test: Verify fallback to English if browser language is unsupported (e.g., Korean)

**Checkpoint**: User Story 3 complete - UI supports 5 languages, translation workflow established

---

## Phase 6: User Story 4 - Plone Control Panel Integration (Priority: P3)

**Goal**: Make AAL2 settings configurable through standard Plone control panel UI

**Independent Test**: Access Plone control panel, find "AAL2 Settings", change timeout from 900 to 600 seconds, verify change takes effect in AAL2 validation logic.

### Control Panel Module Implementation

- [ ] T085 [P] [US4] Create src/c2/pas/aal2/controlpanel/interfaces.py with IAAL2Settings schema interface per data-model.md
- [ ] T086 [P] [US4] Create src/c2/pas/aal2/controlpanel/views.py with AAL2SettingsEditForm class
- [ ] T087 [US4] Create src/c2/pas/aal2/controlpanel/configure.zcml to register control panel view
- [ ] T088 [US4] Create src/c2/pas/aal2/profiles/default/controlpanel.xml to register control panel configlet
- [ ] T089 [US4] Create src/c2/pas/aal2/profiles/default/registry.xml to define plone.app.registry records for IAAL2Settings

### Code Migration from Constants to Registry

- [ ] T090 [US4] Update src/c2/pas/aal2/session.py to replace AAL2_TIMEOUT_SECONDS constant with get_aal2_timeout() function reading from registry
- [ ] T091 [US4] Update src/c2/pas/aal2/session.py is_aal2_valid() to use get_aal2_timeout() instead of hardcoded value
- [ ] T092 [US4] Update src/c2/pas/aal2/session.py get_aal2_expiry() to use get_aal2_timeout()
- [ ] T093 [US4] Add get_aal2_enabled() function to session.py to check aal2_enabled registry setting
- [ ] T094 [US4] Update src/c2/pas/aal2/policy.py check_aal2_access() to respect aal2_enabled setting
- [ ] T095 [US4] Update src/c2/pas/aal2/storage/query.py cleanup_old_logs() to use audit_retention_days from registry

### Upgrade Step for Existing Installations

- [ ] T096 [US4] Update src/c2/pas/aal2/profiles/default/upgrades/upgrade_to_005.py to migrate AAL2_TIMEOUT_SECONDS to registry record
- [ ] T097 [US4] Add registry initialization to upgrade_to_005.py to set default values if missing
- [ ] T098 [US4] Add registry records import step to upgrade_to_005.py

### Testing

- [ ] T099 [P] [US4] Create tests/test_controlpanel.py with test_control_panel_registered()
- [ ] T100 [P] [US4] Add test_settings_schema() to tests/test_controlpanel.py
- [ ] T101 [P] [US4] Add test_settings_view() to tests/test_controlpanel.py
- [ ] T102 [P] [US4] Add test_registry_records_exist() to tests/test_controlpanel.py
- [ ] T103 [P] [US4] Add test_aal2_timeout_from_registry() to tests/test_controlpanel.py
- [ ] T104 [P] [US4] Add test_aal2_enabled_flag() to tests/test_controlpanel.py
- [ ] T105 [US4] Integration test: Change timeout via control panel, perform AAL2 auth, verify new timeout is enforced
- [ ] T106 [US4] Manual browser test: Navigate to @@overview-controlpanel, verify "AAL2 Settings" appears under Products
- [ ] T107 [US4] Manual browser test: Change timeout to 600, verify setting persists after browser refresh

**Checkpoint**: User Story 4 complete - AAL2 settings fully integrated with Plone control panel

---

## Phase 7: User Story 5 - Performance Optimization (Priority: P3)

**Goal**: Add catalog indexes for fast queries of AAL2-protected content

**Independent Test**: Create 5000 test content items with AAL2 protection, time list_aal2_protected_content() before and after adding indexes, verify <2 second query time with indexes.

### Catalog Module Implementation

- [ ] T108 [P] [US5] Create src/c2/pas/aal2/catalog/indexes.py with aal2_protected indexer function
- [ ] T109 [P] [US5] Add aal2_required_roles indexer function to catalog/indexes.py
- [ ] T110 [US5] Create src/c2/pas/aal2/profiles/default/catalog.xml to register aal2_protected FieldIndex
- [ ] T111 [US5] Add aal2_required_roles KeywordIndex to catalog.xml
- [ ] T112 [US5] Register indexer adapters in src/c2/pas/aal2/configure.zcml

### Policy Module Updates

- [ ] T113 [US5] Update src/c2/pas/aal2/policy.py list_aal2_protected_content() to use catalog query instead of iteration
- [ ] T114 [US5] Add RAM cache decorator to policy.py is_aal2_required() function with 60-second TTL
- [ ] T115 [US5] Add request-level cache to policy.py check_aal2_access() to avoid redundant checks

### Event Subscribers for Reindexing

- [ ] T116 [US5] Create src/c2/pas/aal2/catalog/subscribers.py with reindex_aal2_on_change() subscriber
- [ ] T117 [US5] Add reindex_aal2_on_policy_set() subscriber to subscribers.py
- [ ] T118 [US5] Register event subscribers in src/c2/pas/aal2/configure.zcml

### Upgrade Step for Index Creation

- [ ] T119 [US5] Update src/c2/pas/aal2/profiles/default/upgrades/upgrade_to_005.py to add catalog indexes
- [ ] T120 [US5] Add full catalog reindex to upgrade_to_005.py for aal2_protected and aal2_required_roles indexes

### Testing

- [ ] T121 [P] [US5] Create tests/test_catalog_indexes.py with test_aal2_protected_index_registered()
- [ ] T122 [P] [US5] Add test_aal2_required_roles_index_registered() to tests/test_catalog_indexes.py
- [ ] T123 [P] [US5] Add test_indexer_aal2_protected() to tests/test_catalog_indexes.py
- [ ] T124 [P] [US5] Add test_indexer_aal2_required_roles() to tests/test_catalog_indexes.py
- [ ] T125 [P] [US5] Add test_catalog_query_protected_content() to tests/test_catalog_indexes.py
- [ ] T126 [P] [US5] Add test_reindex_on_policy_change() to tests/test_catalog_indexes.py
- [ ] T127 [P] [US5] Add test_cache_aal2_checks() to tests/test_catalog_indexes.py
- [ ] T128 [US5] Performance benchmark: Create 5000 test items, time old O(n) iteration vs new catalog query, verify 10x+ speedup
- [ ] T129 [US5] Manual test: Set AAL2 on content, verify it appears in catalog query results immediately

**Checkpoint**: User Story 5 complete - Catalog indexes provide fast AAL2 content queries

---

## Phase 8: Integration & Upgrade Testing

**Purpose**: Verify all refinements work together and existing functionality is not broken

- [ ] T130 Run full test suite (pytest tests/) and verify all tests pass including new tests for US1-US5
- [ ] T131 Run existing integration tests (tests/test_integration_aal2.py) to verify no regressions
- [ ] T132 Manual test: Full passkey registration → login → AAL2 challenge flow end-to-end
- [ ] T133 Manual test: Query audit logs via browser view API and verify CSV export works
- [ ] T134 Manual test: Switch language to Japanese, complete full passkey flow, verify all UI in Japanese
- [ ] T135 Manual test: Change AAL2 timeout via control panel, verify it affects session validation
- [ ] T136 Manual test: Create 100 content items with AAL2, verify catalog query returns all items quickly
- [ ] T137 Test upgrade step: Apply upgrade_to_005 to test database, verify migration completes without errors
- [ ] T138 Verify JavaScript files load correctly in production mode (minified, cached)

---

## Phase 9: Documentation & Polish

**Purpose**: Update documentation and prepare for deployment

- [ ] T139 [P] Update docs/README.md with new features: external JS, audit logging, i18n, control panel, performance
- [ ] T140 [P] Update /workspace/README.md with upgrade instructions for existing installations
- [ ] T141 [P] Create docs/audit-log-api.md documenting query API endpoints from contracts/audit-log-api.yaml
- [ ] T142 [P] Create docs/translation-guide.md documenting how to add new languages
- [ ] T143 [P] Add JSDoc comments to all JavaScript functions if not already present
- [ ] T144 [P] Add docstrings to all new Python modules (storage, controlpanel, catalog)
- [ ] T145 Code review: Check for any hardcoded strings that should be i18n marked
- [ ] T146 Code review: Verify all audit log calls include appropriate metadata
- [ ] T147 Security review: Verify no sensitive data in audit logs (passwords, tokens)
- [ ] T148 Run ruff check . and fix any linting issues
- [ ] T149 Update CHANGELOG.md with all changes in feature 005
- [ ] T150 Create release notes for feature 005 in docs/releases/005-implementation-refinements.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - **US1 (Phase 3 - P1)**: Can start immediately after Foundational - **MVP TARGET**
  - **US2 (Phase 4 - P2)**: Can start after Foundational - Independent of US1
  - **US3 (Phase 5 - P2)**: Can start after Foundational - Independent of US1, US2
  - **US4 (Phase 6 - P3)**: Can start after Foundational - Independent of other stories
  - **US5 (Phase 7 - P3)**: Can start after Foundational - Independent of other stories
- **Integration Testing (Phase 8)**: Depends on completion of desired user stories
- **Documentation (Phase 9)**: Depends on all implementation completion

### User Story Independence

All user stories (US1-US5) are **fully independent** and can be implemented in parallel after Foundational phase:

- **US1 (JavaScript externalization)**: Affects only templates and static files
- **US2 (Audit logging)**: Adds new storage module, updates existing audit calls
- **US3 (Internationalization)**: Adds locales directory, translation catalogs
- **US4 (Control panel)**: Adds controlpanel module, migrates settings to registry
- **US5 (Performance)**: Adds catalog indexes, updates query code

**Zero cross-story dependencies** - each can be developed, tested, and deployed independently.

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T003 (create directories) [P]
- T004 (create __init__.py files) [P]
- T005 (create upgrades directory) [P]
- T006 (document baseline) [P]

**Within User Story 1**:
- T012-T016 (all template updates) [P]
- T017-T020 (all view classes) [P]

**Within User Story 2**:
- T029, T032 (storage and query modules) [P]
- T050-T058 (all unit tests) [P]

**Within User Story 3**:
- T069-T072 (all translation work) [P]
- T078-T081 (all unit tests) [P]

**Within User Story 4**:
- T085-T086 (interfaces and views) [P]
- T099-T104 (all unit tests) [P]

**Within User Story 5**:
- T108-T109 (both indexers) [P]
- T121-T127 (all unit tests) [P]

**Across User Stories** (if team has multiple developers):
- After Phase 2 completes, Phases 3, 4, 5, 6, 7 can all run in parallel
- Developer A: US1 (P1) - 28 tasks
- Developer B: US2 (P2) - 32 tasks
- Developer C: US3 (P2) - 24 tasks
- Developer D: US4 (P3) - 23 tasks
- Developer E: US5 (P3) - 22 tasks

---

## Parallel Example: User Story 1

```bash
# All template updates can be done simultaneously (different files):
Task T012: "Update register_passkey.pt"
Task T013: "Update login_with_passkey.pt"
Task T014: "Update enhanced_login.pt"
Task T015: "Update aal2_challenge.pt"
Task T016: "Update manage_passkeys.pt"

# All view classes can be added simultaneously:
Task T017: "Add WebAuthnResourcesRegister view"
Task T018: "Add WebAuthnResourcesLogin view"
Task T019: "Add WebAuthnResourcesAAL2 view"
Task T020: "Add WebAuthnResourcesManagement view"
```

---

## Parallel Example: Across User Stories

```bash
# After completing Phase 2, launch all user stories in parallel:

# Developer A starts US1:
Task T010: "Create jsregistry.xml"
Task T012: "Update register_passkey.pt"
# ... (continues with US1 tasks)

# Developer B starts US2 (simultaneously):
Task T029: "Create storage/audit.py"
Task T032: "Create storage/query.py"
# ... (continues with US2 tasks)

# Developer C starts US3 (simultaneously):
Task T061: "Create locales directory structure"
Task T063: "Generate .pot template"
# ... (continues with US3 tasks)

# All three (or all five) developers work independently with zero conflicts
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - ~2-3 hours)

**Fastest path to demonstrable value:**

1. Complete Phase 1: Setup (6 tasks - 15 min)
2. Complete Phase 2: Foundational (3 tasks - 15 min)
3. Complete Phase 3: User Story 1 (19 tasks - 2-3 hours)
4. **STOP and VALIDATE**:
   - Run tests: `pytest tests/test_browser_views.py -k javascript`
   - Manual test: Open browser, register passkey, verify DevTools shows external .js
   - Verify: No inline JavaScript in templates
5. **Result**: JavaScript is externalized, code is more maintainable ✅

**Benefit**: Addresses highest priority technical debt immediately

---

### Incremental Delivery (All User Stories - 16-22 hours)

**Recommended approach for full feature implementation:**

1. **Setup + Foundational** (30 min) → Infrastructure ready
2. **Add US1** (2-3 hours) → Test independently → **MVP deployed** ✅
3. **Add US2** (3-4 hours) → Test independently → Audit logging available ✅
4. **Add US3** (3-4 hours) → Test independently → Multi-language support ✅
5. **Add US4** (2-3 hours) → Test independently → Control panel integrated ✅
6. **Add US5** (2-3 hours) → Test independently → Performance optimized ✅
7. **Integration Testing** (1-2 hours) → Verify everything works together
8. **Documentation** (1-2 hours) → Polish and release notes

**Total**: 16-22 hours for complete feature

**Benefit**: Each story adds value without breaking previous stories. Can stop at any checkpoint.

---

### Parallel Team Strategy (Fastest - ~4-6 hours)

**With 5 developers available:**

1. **All team members**: Complete Setup + Foundational together (30 min)
2. **Split into parallel tracks** (once Foundational done):
   - Developer A: US1 (P1) - 2-3 hours
   - Developer B: US2 (P2) - 3-4 hours
   - Developer C: US3 (P2) - 3-4 hours
   - Developer D: US4 (P3) - 2-3 hours
   - Developer E: US5 (P3) - 2-3 hours
3. **All developers**: Integration testing together (1 hour)
4. **All developers**: Documentation together (1 hour)

**Total wall-clock time**: ~4-6 hours (vs. 16-22 hours sequential)

**Benefit**: Maximum parallelism, fastest completion

---

## Task Count Summary

| Phase | Task Count | Estimated Time |
|-------|------------|----------------|
| Phase 1: Setup | 6 tasks | 15 minutes |
| Phase 2: Foundational | 3 tasks | 15 minutes |
| Phase 3: US1 (P1) - JavaScript | 19 tasks | 2-3 hours |
| Phase 4: US2 (P2) - Audit Logging | 32 tasks | 3-4 hours |
| Phase 5: US3 (P2) - i18n | 24 tasks | 3-4 hours |
| Phase 6: US4 (P3) - Control Panel | 23 tasks | 2-3 hours |
| Phase 7: US5 (P3) - Performance | 22 tasks | 2-3 hours |
| Phase 8: Integration Testing | 9 tasks | 1-2 hours |
| Phase 9: Documentation | 12 tasks | 1-2 hours |
| **Total** | **150 tasks** | **16-22 hours** |

**Parallel opportunities**: 58 tasks marked [P] can run simultaneously

**MVP (US1 only)**: 28 tasks, 2-3 hours

---

## Notes

- **[P] tasks**: Different files, no dependencies - safe to parallelize
- **[Story] labels**: Map each task to user story for traceability and independent testing
- **Zero regressions**: Extensive test coverage ensures existing features continue working
- **Independent stories**: Each user story can be implemented, tested, and deployed separately
- **Commit frequency**: Commit after each task or logical group of related tasks
- **Checkpoints**: Stop at any phase checkpoint to validate story independently
- **Manual tests**: Required because this is UI-heavy refinement work affecting browser behavior
- **Upgrade safety**: upgrade_to_005.py ensures existing installations migrate cleanly

---

## Success Criteria Validation

After completing all tasks, verify these success criteria from spec.md:

- **SC-001**: All WebAuthn functionality operates identically with externalized JavaScript ✅
- **SC-002**: Developers can locate JavaScript code in under 30 seconds ✅
- **SC-003**: Security admins can query 90 days of audit logs in under 5 seconds ✅
- **SC-004**: Audit log storage grows at ~1KB per event ✅
- **SC-005**: Users see interface in browser's language for 5 supported languages ✅
- **SC-006**: Translation coverage reaches 100% for P1, 80%+ for P2/P3 ✅
- **SC-007**: Admins configure AAL2 settings through control panel without custom views ✅
- **SC-008**: Listing 5000+ AAL2-protected items completes in under 2 seconds ✅
- **SC-009**: AAL2 policy checks complete in under 100ms for 95% of requests ✅
- **SC-010**: Zero regressions in existing functionality ✅
