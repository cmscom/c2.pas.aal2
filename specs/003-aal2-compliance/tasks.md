# Tasks: AAL2 Compliance with Passkey Re-authentication

**Input**: Design documents from `/specs/003-aal2-compliance/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: テストタスクは、TDD（テスト駆動開発）アプローチに従って含まれています。各ユーザーストーリーで、テストを**先に書いて失敗を確認**してから実装を進めてください。

**Organization**: タスクはユーザーストーリーごとにグループ化されており、各ストーリーを独立して実装・テスト可能です。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが属するユーザーストーリー（US1, US2, US3, US4）
- 説明に正確なファイルパスを含む

## Path Conventions

既存のc2.pas.aal2パッケージを拡張：
- **Source**: `src/c2/pas/aal2/`
- **Tests**: `tests/`
- **Configuration**: `profiles/default/` (GenericSetup)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: プロジェクト初期化と基本構造の準備

- [ ] T001 Verify existing c2.pas.aal2 package structure in src/c2/pas/aal2/
- [ ] T002 Verify test infrastructure and pytest configuration in tests/
- [ ] T003 [P] Create test fixtures directory at tests/fixtures/
- [ ] T004 [P] Review and understand existing plugin.py in src/c2/pas/aal2/plugin.py
- [ ] T005 [P] Review and understand existing interfaces.py in src/c2/pas/aal2/interfaces.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: すべてのユーザーストーリーに必要なコア基盤。このフェーズ完了前にユーザーストーリーの実装は開始できません。

**⚠️ CRITICAL**: ユーザーストーリーの作業を開始する前に、このフェーズを完全に完了する必要があります。

- [ ] T006 [P] Create permissions module at src/c2/pas/aal2/permissions.py with RequireAAL2Authentication permission definition
- [ ] T007 [P] Create GenericSetup profile directory at profiles/default/
- [ ] T008 Create rolemap.xml at profiles/default/rolemap.xml with AAL2 Required User role definition
- [ ] T009 Update configure.zcml at src/c2/pas/aal2/configure.zcml to register permissions and GenericSetup profile
- [ ] T010 Verify permission and role registration by running setuptools installation

**Checkpoint**: 基盤準備完了 - ユーザーストーリーの並列実装が可能になります

---

## Phase 3: User Story 3 - Authentication Session Tracking (Priority: P1) 🎯 MVP Foundation

**Goal**: ユーザーの認証タイムスタンプを正確に追跡し、15分の有効期限を管理する。パスキー認証が成功するたびに、タイムスタンプが更新される。

**Why First**: このストーリーは他のすべてのAAL2機能の基盤です。タイムスタンプ管理なしでは、15分ルールを実装できません。

**Independent Test**: ユーザーがパスキーで認証し、システムが認証時刻を記録し、15分後に自動的に期限切れとなることで、独立してテスト可能。

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US3] Create test_session.py at tests/test_session.py with test fixtures for Plone users
- [ ] T012 [P] [US3] Write unit test for set_aal2_timestamp() in tests/test_session.py
- [ ] T013 [P] [US3] Write unit test for get_aal2_timestamp() in tests/test_session.py
- [ ] T014 [P] [US3] Write unit test for is_aal2_valid() with fresh timestamp in tests/test_session.py
- [ ] T015 [P] [US3] Write unit test for is_aal2_valid() with expired timestamp (16 minutes) in tests/test_session.py
- [ ] T016 [P] [US3] Write unit test for get_aal2_expiry() in tests/test_session.py
- [ ] T017 [P] [US3] Write unit test for clear_aal2_timestamp() in tests/test_session.py
- [ ] T018 [P] [US3] Write edge case test for future timestamps (should be invalid) in tests/test_session.py
- [ ] T019 [US3] Run pytest tests/test_session.py to confirm all tests FAIL (module doesn't exist yet)

### Implementation for User Story 3

- [ ] T020 [US3] Create session.py module at src/c2/pas/aal2/session.py with imports and constants (ANNOTATION_KEY, AAL2_TIMEOUT_SECONDS)
- [ ] T021 [US3] Implement set_aal2_timestamp(user, credential_id=None) in src/c2/pas/aal2/session.py
- [ ] T022 [US3] Implement get_aal2_timestamp(user) in src/c2/pas/aal2/session.py
- [ ] T023 [US3] Implement is_aal2_valid(user) with 15-minute check in src/c2/pas/aal2/session.py
- [ ] T024 [US3] Implement get_aal2_expiry(user) in src/c2/pas/aal2/session.py
- [ ] T025 [US3] Implement clear_aal2_timestamp(user) in src/c2/pas/aal2/session.py
- [ ] T026 [US3] Add error handling and logging to all session functions in src/c2/pas/aal2/session.py
- [ ] T027 [US3] Add docstrings with type hints to all functions in src/c2/pas/aal2/session.py
- [ ] T028 [US3] Run pytest tests/test_session.py to confirm all tests PASS
- [ ] T029 [US3] Update existing plugin.py to use set_aal2_timestamp() after successful passkey authentication in src/c2/pas/aal2/plugin.py

**Checkpoint**: セッション管理機能が完全に機能し、独立してテスト可能。他のストーリーの基盤として使用可能。

---

## Phase 4: User Story 1 - Elevated Permission Protection (Priority: P1) 🎯 MVP Core

**Goal**: 管理者が特定のコンテンツやリソースに対して、AAL2レベルの認証を要求する保護を設定できる。ユーザーが保護されたリソースにアクセスする際、最後の認証が15分以上前であれば、パスキーによる再認証を求められる。

**Why Second**: セキュリティの核心機能であり、AAL2コンプライアンスの実現に必要不可欠。US3のタイムスタンプ管理を基盤とする。

**Independent Test**: 管理者がコンテンツに新しいパーミッションを設定し、ユーザーが15分経過後にアクセスを試みてパスキーチャレンジが表示されることで、独立してテスト可能。

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T030 [P] [US1] Create test_policy.py at tests/test_policy.py with fixtures for Plone content objects
- [ ] T031 [P] [US1] Write unit test for is_aal2_required(context) checking content annotation in tests/test_policy.py
- [ ] T032 [P] [US1] Write unit test for set_aal2_required(context, required=True) in tests/test_policy.py
- [ ] T033 [P] [US1] Write unit test for check_aal2_access() when AAL2 not required in tests/test_policy.py
- [ ] T034 [P] [US1] Write unit test for check_aal2_access() when AAL2 required and valid in tests/test_policy.py
- [ ] T035 [P] [US1] Write unit test for check_aal2_access() when AAL2 required and expired in tests/test_policy.py
- [ ] T036 [P] [US1] Write unit test for get_stepup_challenge_url() in tests/test_policy.py
- [ ] T037 [P] [US1] Create test_integration_aal2.py at tests/test_integration_aal2.py with full workflow tests
- [ ] T038 [US1] Write integration test for complete AAL2 protection flow in tests/test_integration_aal2.py
- [ ] T039 [US1] Run pytest tests/test_policy.py tests/test_integration_aal2.py to confirm all tests FAIL

### Implementation for User Story 1

- [ ] T040 [US1] Create policy.py module at src/c2/pas/aal2/policy.py with imports and constants (AAL2_POLICY_KEY)
- [ ] T041 [US1] Implement is_aal2_required(context, user=None) with content annotation check in src/c2/pas/aal2/policy.py
- [ ] T042 [US1] Implement set_aal2_required(context, required=True) with annotation write in src/c2/pas/aal2/policy.py
- [ ] T043 [US1] Implement check_aal2_access(context, user, request) integrating session.is_aal2_valid() in src/c2/pas/aal2/policy.py
- [ ] T044 [US1] Implement get_stepup_challenge_url(context, request) in src/c2/pas/aal2/policy.py
- [ ] T045 [US1] Implement list_aal2_protected_content() utility function in src/c2/pas/aal2/policy.py
- [ ] T046 [US1] Add plone.memoize caching for is_aal2_required() in src/c2/pas/aal2/policy.py
- [ ] T047 [US1] Add error handling and logging to policy module in src/c2/pas/aal2/policy.py
- [ ] T048 [US1] Add docstrings with type hints to all policy functions in src/c2/pas/aal2/policy.py
- [ ] T049 [US1] Run pytest tests/test_policy.py to confirm all unit tests PASS
- [ ] T050 [US1] Update plugin.py to implement get_aal_level(user_id) using session.is_aal2_valid() in src/c2/pas/aal2/plugin.py
- [ ] T051 [US1] Update plugin.py to implement require_aal2(user_id, context) using policy.is_aal2_required() in src/c2/pas/aal2/plugin.py
- [ ] T052 [US1] Add validate() method to plugin.py for AAL2 requirement checking in src/c2/pas/aal2/plugin.py
- [ ] T053 [US1] Register AAL2Plugin as IValidationPlugin in configure.zcml at src/c2/pas/aal2/configure.zcml
- [ ] T054 [US1] Create AAL2 challenge view class at src/c2/pas/aal2/browser/views.py (AAL2ChallengeView)
- [ ] T055 [US1] Create AAL2 challenge template at src/c2/pas/aal2/browser/aal2_challenge.pt with WebAuthn integration
- [ ] T056 [US1] Create AAL2 settings view for administrators at src/c2/pas/aal2/browser/views.py (AAL2SettingsView)
- [ ] T057 [US1] Register AAL2 views in browser configure.zcml at src/c2/pas/aal2/browser/configure.zcml
- [ ] T058 [US1] Run pytest tests/test_integration_aal2.py to confirm integration tests PASS
- [ ] T059 [US1] Manual test: Set AAL2 protection on content, verify challenge appears after 15 minutes

**Checkpoint**: AAL2コンテンツ保護が完全に機能。管理者が保護を設定でき、ユーザーが15分後に再認証を求められる。MVP機能完成。

---

## Phase 5: User Story 2 - AAL2 Role Management (Priority: P2)

**Goal**: 管理者が「AAL2 Required」などのロールを作成し、そのロールを持つユーザーには常にAAL2レベルの認証を要求できる。これにより、特権ユーザー（経理、人事、システム管理者など）に対して、包括的なセキュリティポリシーを適用できる。

**Why Third**: ユーザーグループ全体にセキュリティポリシーを適用する効率的な方法を提供。US1の個別コンテンツ保護を補完する機能。

**Independent Test**: 管理者が新しいAAL2ロールを作成し、ユーザーに割り当てて、そのユーザーが任意のリソースにアクセスする際に15分ルールが適用されることで、独立してテスト可能。

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T060 [P] [US2] Create test_roles.py at tests/test_roles.py with fixtures for Plone users with roles
- [ ] T061 [P] [US2] Write unit test for AAL2 role assignment in tests/test_roles.py
- [ ] T062 [P] [US2] Write unit test for is_aal2_required() with user having AAL2 role in tests/test_roles.py
- [ ] T063 [P] [US2] Write unit test for check_aal2_access() with AAL2 role user in tests/test_roles.py
- [ ] T064 [US2] Write integration test for AAL2 role enforcement across multiple resources in tests/test_integration_aal2.py
- [ ] T065 [US2] Run pytest tests/test_roles.py to confirm all tests FAIL

### Implementation for User Story 2

- [ ] T066 [US2] Verify AAL2 Required User role exists in profiles/default/rolemap.xml (should exist from Phase 2)
- [ ] T067 [US2] Update policy.is_aal2_required() to check for AAL2 Required User role in src/c2/pas/aal2/policy.py
- [ ] T068 [US2] Create role management utility functions (list_aal2_users, assign_aal2_role, revoke_aal2_role) in new file src/c2/pas/aal2/roles.py
- [ ] T069 [US2] Add docstrings and type hints to roles module in src/c2/pas/aal2/roles.py
- [ ] T070 [US2] Create AAL2 role management view at src/c2/pas/aal2/browser/views.py (AAL2RoleManagementView)
- [ ] T071 [US2] Create role management template at src/c2/pas/aal2/browser/aal2_roles.pt
- [ ] T072 [US2] Register role management view in browser configure.zcml at src/c2/pas/aal2/browser/configure.zcml
- [ ] T073 [US2] Run pytest tests/test_roles.py to confirm all unit tests PASS
- [ ] T074 [US2] Run pytest tests/test_integration_aal2.py (role tests) to confirm integration tests PASS
- [ ] T075 [US2] Manual test: Assign AAL2 role to user, verify global AAL2 enforcement

**Checkpoint**: AAL2ロール管理が完全に機能。管理者がユーザーにロールを割り当てでき、グローバルAAL2ポリシーが適用される。

---

## Phase 6: User Story 4 - Clear User Feedback (Priority: P3)

**Goal**: ユーザーがAAL2保護リソースにアクセスしようとした際、なぜ再認証が必要なのか、いつ認証が期限切れになるのかを明確に理解できる。

**Why Last**: ユーザー体験の向上。基本機能は動作するが、より良いUXを提供。

**Independent Test**: ユーザーインターフェースにアクセスして、メッセージの明確さと情報の正確性を確認することで、独立してテスト可能。

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T076 [P] [US4] Create test_views.py at tests/test_views.py with fixtures for browser views
- [ ] T077 [P] [US4] Write unit test for AAL2ChallengeView message clarity in tests/test_views.py
- [ ] T078 [P] [US4] Write unit test for AAL2 expiry time display in tests/test_views.py
- [ ] T079 [P] [US4] Write unit test for user-friendly error messages in tests/test_views.py
- [ ] T080 [US4] Write integration test for complete user feedback flow in tests/test_integration_aal2.py
- [ ] T081 [US4] Run pytest tests/test_views.py to confirm all tests FAIL

### Implementation for User Story 4

- [ ] T082 [US4] Update AAL2 challenge template at src/c2/pas/aal2/browser/aal2_challenge.pt with clear explanation messages
- [ ] T083 [US4] Add i18n (internationalization) message IDs to challenge template at src/c2/pas/aal2/browser/aal2_challenge.pt
- [ ] T084 [US4] Create user dashboard viewlet at src/c2/pas/aal2/browser/viewlets.py (AAL2StatusViewlet) showing AAL2 status and expiry time
- [ ] T085 [US4] Create viewlet template at src/c2/pas/aal2/browser/aal2_status.pt with status display
- [ ] T086 [US4] Register viewlet in browser configure.zcml at src/c2/pas/aal2/browser/configure.zcml
- [ ] T087 [US4] Update AAL2ChallengeView to include helpful context (original URL, reason) in src/c2/pas/aal2/browser/views.py
- [ ] T088 [US4] Add CSS styling for AAL2 UI elements at src/c2/pas/aal2/browser/static/aal2.css
- [ ] T089 [US4] Register static resources in browser configure.zcml at src/c2/pas/aal2/browser/configure.zcml
- [ ] T090 [US4] Create help documentation at docs/aal2_user_guide.md
- [ ] T091 [US4] Run pytest tests/test_views.py to confirm all unit tests PASS
- [ ] T092 [US4] Run pytest tests/test_integration_aal2.py (UI tests) to confirm integration tests PASS
- [ ] T093 [US4] Manual test: Navigate through AAL2 protected content and verify all messages are clear and helpful

**Checkpoint**: AAL2ユーザー体験が向上。すべてのメッセージが明確で、ユーザーがAAL2状態を簡単に理解できる。

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 複数のユーザーストーリーに影響する改善

- [ ] T094 [P] Add comprehensive logging to audit module at src/c2/pas/aal2/utils/audit.py with AAL2-specific events
- [ ] T095 [P] Create test_permissions.py at tests/test_permissions.py for permission registration tests
- [ ] T096 [P] Write contract tests for Session API in tests/test_session_contract.py
- [ ] T097 [P] Write contract tests for Policy API in tests/test_policy_contract.py
- [ ] T098 [P] Update existing test_plugin.py at tests/test_plugin.py with AAL2 plugin tests
- [ ] T099 Run full test suite with coverage: pytest --cov=c2.pas.aal2 --cov-report=html tests/
- [ ] T100 Verify test coverage is >90% and fix any gaps
- [ ] T101 [P] Add performance benchmarks for AAL2 operations at tests/test_performance.py
- [ ] T102 Run performance tests and verify <50ms for AAL2 checks
- [ ] T103 [P] Create migration guide at docs/migration_guide.md for upgrading from stub to full AAL2
- [ ] T104 [P] Update README at src/c2/pas/aal2/README.md with AAL2 feature documentation
- [ ] T105 Code review: Check all functions have docstrings and type hints
- [ ] T106 Code review: Verify error handling follows established patterns
- [ ] T107 Run ruff check src/c2/pas/aal2/ to verify code style compliance
- [ ] T108 Security review: Verify no AAL2 bypass vulnerabilities exist
- [ ] T109 Security review: Check for CSRF protection in AAL2 settings views
- [ ] T110 Run all quickstart.md validation steps to ensure developer guide is accurate
- [ ] T111 Final integration test: Complete end-to-end AAL2 workflow with all features enabled

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存関係なし - 即座に開始可能
- **Foundational (Phase 2)**: Setup完了に依存 - すべてのユーザーストーリーをブロック
- **User Story 3 (Phase 3)**: Foundational完了に依存 - 他のストーリーの基盤
- **User Story 1 (Phase 4)**: US3完了に依存（タイムスタンプ管理が必要）
- **User Story 2 (Phase 5)**: US1完了に依存（policy.pyの拡張が必要）
- **User Story 4 (Phase 6)**: US1完了に依存（チャレンジUIの拡張が必要）
- **Polish (Phase 7)**: 望ましいすべてのユーザーストーリー完了に依存

### User Story Dependencies

```text
US3 (P1) - Session Tracking
    ↓
US1 (P1) - Permission Protection  ←─── MVP Complete Here
    ↓
    ├─→ US2 (P2) - Role Management
    └─→ US4 (P3) - User Feedback
```

- **US3**: 他のストーリーに依存しない - 最初に実装
- **US1**: US3に依存 - タイムスタンプ管理を使用
- **US2**: US1に依存 - policy.pyを拡張
- **US4**: US1に依存 - チャレンジUIを改善

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Models before services
3. Services before views/endpoints
4. Core implementation before UI/integration
5. Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T003, T004, T005 can run in parallel

**Foundational Phase (Phase 2)**:
- T006, T007 can run in parallel
- T008, T009 must run sequentially after T007

**User Story 3 Tests (Phase 3)**:
- T011-T018 can all run in parallel (writing tests)

**User Story 1 Tests (Phase 4)**:
- T030-T037 can all run in parallel (writing tests)

**User Story 2 Tests (Phase 5)**:
- T060-T064 can all run in parallel (writing tests)

**User Story 4 Tests (Phase 6)**:
- T076-T080 can all run in parallel (writing tests)

**Polish Phase (Phase 7)**:
- T094-T098, T101, T103, T104 can all run in parallel

**Team Strategy**: Foundational完了後、US3とUS1を並列に進めることも可能（経験豊富な開発者の場合）

---

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Write unit test for set_aal2_timestamp() in tests/test_session.py"
Task: "Write unit test for get_aal2_timestamp() in tests/test_session.py"
Task: "Write unit test for is_aal2_valid() with fresh timestamp in tests/test_session.py"
Task: "Write unit test for is_aal2_valid() with expired timestamp in tests/test_session.py"
Task: "Write unit test for get_aal2_expiry() in tests/test_session.py"
Task: "Write unit test for clear_aal2_timestamp() in tests/test_session.py"
Task: "Write edge case test for future timestamps in tests/test_session.py"
```

---

## Implementation Strategy

### MVP First (User Stories 3 + 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T010) - **CRITICAL: Must complete before stories**
3. Complete Phase 3: User Story 3 (T011-T029) - Session tracking
4. Complete Phase 4: User Story 1 (T030-T059) - Permission protection
5. **STOP and VALIDATE**: Test US3 + US1 independently
6. Deploy/demo MVP (Core AAL2 functionality working)

**MVP Deliverable**:
- 管理者がコンテンツにAAL2保護を設定可能
- ユーザーがパスキーで認証後15分間アクセス可能
- 15分経過後、再認証が要求される
- すべてのコア機能が動作

### Incremental Delivery

1. Setup + Foundational (T001-T010) → 基盤準備完了
2. Add User Story 3 (T011-T029) → タイムスタンプ管理機能完成
3. Add User Story 1 (T030-T059) → Test independently → **Deploy/Demo (MVP!)**
4. Add User Story 2 (T060-T075) → Test independently → Deploy/Demo (ロール管理追加)
5. Add User Story 4 (T076-T093) → Test independently → Deploy/Demo (UX改善)
6. Polish (T094-T111) → 本番品質達成

各ストーリーが価値を追加し、以前のストーリーを壊さない。

### Parallel Team Strategy

複数の開発者がいる場合：

1. チーム全員でSetup + Foundationalを完了（T001-T010）
2. Foundational完了後：
   - **Developer A**: User Story 3 (T011-T029) - 基盤実装
   - **Developer B**: User Story 1 tests (T030-T039) - テスト準備
3. US3完了後：
   - **Developer A**: User Story 1 implementation (T040-T059)
   - **Developer B**: User Story 2 tests (T060-T065)
4. US1完了後：
   - **Developer A**: User Story 2 implementation (T066-T075)
   - **Developer B**: User Story 4 tests (T076-T081)
5. All complete → Polish together (T094-T111)

---

## Task Summary

**Total Tasks**: 111
**Task Breakdown by Phase**:
- Setup (Phase 1): 5 tasks
- Foundational (Phase 2): 5 tasks
- User Story 3 (Phase 3): 19 tasks (9 tests + 10 implementation)
- User Story 1 (Phase 4): 30 tasks (10 tests + 20 implementation)
- User Story 2 (Phase 5): 16 tasks (6 tests + 10 implementation)
- User Story 4 (Phase 6): 18 tasks (6 tests + 12 implementation)
- Polish (Phase 7): 18 tasks

**Parallel Opportunities**: 42 tasks marked with [P]

**MVP Scope** (Recommended first release):
- Phase 1: Setup (T001-T005)
- Phase 2: Foundational (T006-T010)
- Phase 3: User Story 3 (T011-T029)
- Phase 4: User Story 1 (T030-T059)
- **Total MVP tasks: 59** (53% of total)

**Test Coverage**:
- Unit tests: 31 tasks
- Integration tests: 4 tasks
- Contract tests: 2 tasks
- Performance tests: 1 task
- **Total test tasks: 38** (34% of total)

---

## Format Validation

✅ All tasks follow the required checklist format:
- `- [ ]` checkbox present
- Task ID (T001-T111) sequential
- `[P]` marker for parallelizable tasks
- `[Story]` label for user story tasks (US1, US2, US3, US4)
- Clear descriptions with exact file paths

✅ Organization verified:
- Tasks grouped by user story
- Each story has independent test criteria
- Dependencies clearly documented
- MVP scope identified (US3 + US1)

---

## Notes

- **[P]** tasks = 異なるファイル、依存関係なし
- **[Story]** label = タスクを特定のユーザーストーリーにマップ（トレーサビリティ）
- 各ユーザーストーリーは独立して完成・テスト可能
- 実装前にテストが失敗することを確認
- 各タスクまたは論理グループ後にコミット
- チェックポイントでストーリーを独立して検証
- 避けるべき: 曖昧なタスク、同じファイルの競合、ストーリーの独立性を壊す依存関係
