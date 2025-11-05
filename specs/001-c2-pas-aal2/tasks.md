# Tasks: c2.pas.aal2 - Plone PAS AAL2認証プラグイン雛形

**Input**: Design documents from `/specs/001-c2-pas-aal2/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: 仕様書でテストが明示的に要求されているため、テストタスクを含みます。

**Organization**: タスクはユーザーストーリーごとにグループ化され、各ストーリーの独立した実装とテストを可能にします。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが属するユーザーストーリー（例: US1, US2, US3）
- 説明には正確なファイルパスを含む

## Path Conventions

このプロジェクトは2ドット形式のPloneパッケージ構造を採用：
- **パッケージコード**: `c2/pas/aal2/`
- **テスト**: `tests/`
- **ドキュメント**: `docs/`
- **設定ファイル**: ルートディレクトリ

## Phase 1: Setup（共有インフラストラクチャ）

**Purpose**: プロジェクトの初期化と基本構造の作成

- [ ] T001 Create root package directory `c2.pas.aal2/` per implementation plan
- [ ] T002 [P] Create namespace package structure `c2/__init__.py` (empty for namespace)
- [ ] T003 [P] Create namespace package structure `c2/pas/__init__.py` (empty for namespace)
- [ ] T004 [P] Create main package `c2/pas/aal2/__init__.py` with package exports
- [ ] T005 [P] Create test directory structure `tests/__init__.py`
- [ ] T006 [P] Configure pytest with `pytest.ini` for test discovery and coverage settings
- [ ] T007 [P] Create `.gitignore` for Python standard exclusions (__pycache__, *.pyc, dist/, *.egg-info/)
- [ ] T008 [P] Create `tox.ini` for multi-environment testing configuration

---

## Phase 2: Foundational（ブロッキング必須要件）

**Purpose**: すべてのユーザーストーリーの実装前に完了必須のコア設定

**⚠️ CRITICAL**: このフェーズが完了するまで、ユーザーストーリーの作業は開始できません

- [ ] T009 Create `setup.py` with package metadata, dependencies (Plone 5.2+, Python 3.11+), and namespace_packages configuration
- [ ] T010 [P] Create `MANIFEST.in` to include ZCML files, README, and non-Python files in package distribution
- [ ] T011 [P] Create `LICENSE` file with GPLv2 text (Plone standard)
- [ ] T012 [P] Create `CHANGES.rst` with initial version 0.1.0 entry (Plone standard format)

**Checkpoint**: 基盤の準備完了 - ユーザーストーリーの実装が並列で開始可能

---

## Phase 3: User Story 1 - パッケージ雛形のセットアップと登録 (Priority: P1) 🎯 MVP

**Goal**: 2ドット形式のPloneパッケージ構造を持つ雛形をセットアップし、PASプラグインとして正しく登録できることを確認

**Independent Test**: Plone管理インターフェースでパッケージをインストールし、PASプラグイン一覧に表示されることを確認。プラグインが正しく登録され、エラーなく有効化できる。

### Tests for User Story 1

> **NOTE: これらのテストを最初に記述し、実装前にFAILすることを確認**

- [ ] T013 [P] [US1] Create import test in `tests/test_import.py` - verify `import c2.pas.aal2` succeeds
- [ ] T014 [P] [US1] Create plugin registration test in `tests/test_plugin_registration.py` - verify AAL2Plugin implements IAuthenticationPlugin and IExtractionPlugin
- [ ] T015 [P] [US1] Create stub methods test in `tests/test_stub_methods.py` - verify authenticateCredentials() and extractCredentials() are callable and don't raise exceptions

### Implementation for User Story 1

- [ ] T016 [P] [US1] Create Zope interface definitions in `c2/pas/aal2/interfaces.py` - define IAAL2Plugin with get_aal_level() and require_aal2() method signatures
- [ ] T017 [US1] Create AAL2Plugin stub class in `c2/pas/aal2/plugin.py` - implement IAuthenticationPlugin and IExtractionPlugin with stub methods (authenticateCredentials returns None, extractCredentials returns empty dict)
- [ ] T018 [US1] Create ZCML configuration in `c2/pas/aal2/configure.zcml` - register AAL2Plugin as PAS plugin with proper namespace and i18n domain
- [ ] T019 [US1] Update `c2/pas/aal2/__init__.py` to export AAL2Plugin class and IAAL2Plugin interface
- [ ] T020 [US1] Verify plugin ID, title, and meta_type attributes are set correctly in AAL2Plugin class

**Checkpoint**: User Story 1が完全に機能し、独立してテスト可能

---

## Phase 4: User Story 2 - 基本的なテスト構造の提供 (Priority: P2)

**Goal**: Pytestを使用した基本的なテスト構造とサンプルテストを含む雛形を準備し、将来の開発者がテストを追加しやすくする

**Independent Test**: pytestを実行して、サンプルテスト（パッケージのインポート、基本的な構造確認など）が成功することを確認。

### Tests for User Story 2

> **NOTE: これらのテストは既にUser Story 1で作成済みのため、追加のテストタスクなし**

### Implementation for User Story 2

- [ ] T021 [P] [US2] Create pytest configuration in `tests/conftest.py` with common fixtures (if needed for future tests)
- [ ] T022 [US2] Add test documentation in `tests/README.md` - explain test structure, how to run tests, how to add new tests
- [ ] T023 [US2] Verify all 3 basic tests (import, plugin registration, stub methods) pass with `pytest tests/ -v`
- [ ] T024 [US2] Add pytest-cov configuration to `pytest.ini` for coverage reporting
- [ ] T025 [US2] Run coverage report with `pytest tests/ --cov=c2.pas.aal2 --cov-report=term-missing` and verify structure is testable

**Checkpoint**: User Stories 1とUser Story 2が両方とも独立して動作

---

## Phase 5: User Story 3 - ドキュメントと設定ファイルの雛形 (Priority: P3)

**Goal**: パッケージの目的、構造、将来の実装ガイドラインを理解するため、基本的なドキュメント（README、setup.py/pyproject.toml、ZCML設定ファイル等）を含む雛形を準備

**Independent Test**: README.mdが存在し、パッケージのインストール方法と基本構造が記載されていることを確認。setup.pyが適切な依存関係を定義していることを確認。

### Tests for User Story 3

> **NOTE: ドキュメントタスクのため、自動テストは不要。手動検証で十分**

### Implementation for User Story 3

- [ ] T026 [P] [US3] Create comprehensive `README.md` in root - include package purpose, installation instructions (pip install -e .), basic structure explanation, import example, future implementation TODOs
- [ ] T027 [P] [US3] Create implementation guide in `docs/implementation_guide.md` - document how to extend stub methods, add new PAS interfaces, implement AAL2 logic
- [ ] T028 [P] [US3] Add package classifiers to `setup.py` - Python 3.11+, Plone 5.2+, Development Status :: 3 - Alpha, Framework :: Plone
- [ ] T029 [US3] Verify `setup.py` install_requires includes correct Plone dependencies and extras_require defines [test] with pytest and pytest-cov
- [ ] T030 [US3] Add inline documentation to `c2/pas/aal2/plugin.py` - docstrings for AAL2Plugin class and all stub methods explaining future implementation requirements
- [ ] T031 [US3] Add inline documentation to `c2/pas/aal2/interfaces.py` - docstrings for IAAL2Plugin interface and method signatures
- [ ] T032 [US3] Add comments to `c2/pas/aal2/configure.zcml` explaining ZCML registration and how to extend for GenericSetup profiles

**Checkpoint**: すべてのユーザーストーリーが独立して機能的

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 複数のユーザーストーリーに影響する改善

- [ ] T033 [P] Run full test suite with `pytest tests/ -v --cov=c2.pas.aal2 --cov-report=term-missing` and verify all tests pass
- [ ] T034 [P] Verify package can be installed in development mode with `pip install -e .` without errors
- [ ] T035 [P] Test package import `python -c "import c2.pas.aal2; print('Success')"` succeeds
- [ ] T036 [P] Verify namespace package structure allows `import c2.pas.aal2` with correct module hierarchy
- [ ] T037 Run quickstart.md validation - follow all setup steps and verify they work within 10 minutes
- [ ] T038 [P] Code review for Python PEP 8 style compliance (can use black or autopep8 if desired)
- [ ] T039 [P] Add edge case handling to setup.py - verify Python version check (>=3.11) and Plone version requirement (>=5.2)
- [ ] T040 Final documentation review - ensure README.md installation steps match actual setup.py configuration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存関係なし - すぐに開始可能
- **Foundational (Phase 2)**: Setupフェーズ完了に依存 - すべてのユーザーストーリーをブロック
- **User Stories (Phase 3-5)**: すべてFoundationalフェーズ完了に依存
  - ユーザーストーリーは並列で進行可能（スタッフィング可能な場合）
  - または優先度順に順次実行（P1 → P2 → P3）
- **Polish (Phase 6)**: 希望するすべてのユーザーストーリーの完了に依存

### User Story Dependencies

- **User Story 1 (P1)**: Foundational (Phase 2)後に開始可能 - 他のストーリーへの依存なし
- **User Story 2 (P2)**: Foundational (Phase 2)後に開始可能 - US1と統合するが独立してテスト可能（US1のテストを再利用）
- **User Story 3 (P3)**: Foundational (Phase 2)後に開始可能 - US1/US2と統合するが独立してテスト可能

### Within Each User Story

- テスト（含まれる場合）は実装前に記述し、FAILすることを確認
- インターフェース定義 → プラグインクラス → ZCML設定 → 検証
- テストファースト → 実装 → 検証のサイクル
- 次の優先度に移る前にストーリー完了

### Parallel Opportunities

- Setup内のすべての[P]タスクは並列実行可能
- Foundational内のすべての[P]タスクは並列実行可能（Phase 2内）
- Foundationalフェーズ完了後、すべてのユーザーストーリーを並列で開始可能（チーム能力が許せば）
- ユーザーストーリー内の[P]マークのタスクは並列実行可能
- 異なるユーザーストーリーは異なるチームメンバーによって並列作業可能

---

## Parallel Example: User Story 1

```bash
# User Story 1のすべてのテストを同時に起動:
Task: "Create import test in tests/test_import.py"
Task: "Create plugin registration test in tests/test_plugin_registration.py"
Task: "Create stub methods test in tests/test_stub_methods.py"

# User Story 1の並列可能な実装タスクを同時に起動:
Task: "Create Zope interface definitions in c2/pas/aal2/interfaces.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup完了
2. Phase 2: Foundational完了（CRITICAL - すべてのストーリーをブロック）
3. Phase 3: User Story 1完了
4. **STOP and VALIDATE**: User Story 1を独立してテスト
5. 準備ができたらデプロイ/デモ

### Incremental Delivery

1. Setup + Foundational完了 → 基盤準備完了
2. User Story 1追加 → 独立してテスト → デプロイ/デモ（MVP！）
3. User Story 2追加 → 独立してテスト → デプロイ/デモ
4. User Story 3追加 → 独立してテスト → デプロイ/デモ
5. 各ストーリーは前のストーリーを壊さずに価値を追加

### Parallel Team Strategy

複数の開発者がいる場合:

1. チーム全体でSetup + Foundationalを完了
2. Foundational完了後:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. ストーリーは独立して完了し統合

---

## Notes

- [P]タスク = 異なるファイル、依存関係なし
- [Story]ラベルはタスクを特定のユーザーストーリーにマッピングしてトレーサビリティを確保
- 各ユーザーストーリーは独立して完了・テスト可能であるべき
- 実装前にテストがfailすることを確認
- 各タスクまたは論理的なグループ後にコミット
- 任意のチェックポイントで停止してストーリーを独立して検証
- 避けるべき: 曖昧なタスク、同じファイルの競合、独立性を壊すストーリー間依存
- パッケージ雛形のため実際の認証ロジック実装なし - スタブメソッドのみ
- Plone環境での動作確認は外部で実施（quickstart.mdに記載）
