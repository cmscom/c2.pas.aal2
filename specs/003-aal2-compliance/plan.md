# Implementation Plan: AAL2 Compliance with Passkey Re-authentication

**Branch**: `003-aal2-compliance` | **Date**: 2025-11-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-aal2-compliance/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

この機能は、AAL2（Authentication Assurance Level 2）コンプライアンスを実現するために、既存のc2.pas.aal2パッケージを拡張します。主な要件は：

1. **新規パーミッション**: "Require AAL2 Authentication" - Plone.PASのカスタムパーミッション
2. **新規ロール**: "AAL2 Required User" - Plone.PASのカスタムロール
3. **15分タイムスタンプ管理**: パスキー認証後15分間のAAL2セッション管理
4. **パスキーチャレンジ**: 15分経過後の再認証フロー

既存のWebAuthnパスキー実装（002-passkey-login）を基盤として、AAL2レベルの検証とステップアップ認証を追加します。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Plone 5.2+, Plone.PAS (Pluggable Authentication Service), webauthn==2.7.0 (py_webauthn by Duo Labs), datetime (標準ライブラリ)
**Storage**: ZODB (Zope Object Database) - ユーザーオブジェクトにAAL2タイムスタンプ属性を追加、アノテーションでパーミッション設定を保存
**Testing**: pytest
**Target Platform**: Linux server (Plone CMS)
**Project Type**: 単一プロジェクト（既存のc2.pas.aal2パッケージの拡張）
**Performance Goals**:
  - AAL2チェック: <50ms（リクエストごと）
  - タイムスタンプ検証: <10ms
  - パスキーチャレンジ生成: <200ms
  - 10,000同時ユーザーをサポート
**Constraints**:
  - 15分タイムウィンドウの精度: ±5秒
  - 既存の認証フローに影響を与えない（下位互換性）
  - Ploneのパーミッションフレームワークとの統合
**Scale/Scope**:
  - 最大100,000ユーザー
  - AAL2保護リソース: 無制限（パフォーマンスへの影響最小化）
  - 既存コード: 約500行、新規コード: 約800-1000行（推定）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASSED (Constitution file is a template - no specific constraints to check)

プロジェクトの憲法（constitution.md）はテンプレートのままであり、具体的な制約が定義されていません。以下の一般的なベストプラクティスを適用します：

- ✅ **既存コードの拡張**: 新規プロジェクトではなく、既存のc2.pas.aal2パッケージの拡張
- ✅ **テスト駆動**: pytestを使用した包括的なテスト計画
- ✅ **シンプルさ**: 必要最小限の実装、YAGNIの原則
- ✅ **統合性**: Plone.PASフレームワークとの統合、標準パターンの使用
- ✅ **後方互換性**: 既存の認証フローに影響を与えない

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
src/c2/pas/aal2/
├── __init__.py
├── interfaces.py          # IAAL2Plugin interface（既存）
├── plugin.py              # AAL2Plugin main class（既存・拡張対象）
├── credential.py          # Passkey storage functions（既存）
├── permissions.py         # 新規: AAL2パーミッション定義
├── roles.py               # 新規: AAL2ロール定義
├── session.py             # 新規: AAL2セッション・タイムスタンプ管理
├── policy.py              # 新規: AAL2ポリシーチェック・ステップアップ
├── browser/
│   ├── __init__.py
│   ├── views.py           # WebAuthn認証ビュー（既存・拡張対象）
│   ├── viewlets.py        # UI要素（既存・拡張対象）
│   ├── aal2_challenge.pt  # 新規: AAL2再認証チャレンジテンプレート
│   └── configure.zcml     # Zope設定（拡張対象）
├── utils/
│   ├── __init__.py
│   ├── webauthn.py        # WebAuthn helper functions（既存）
│   ├── storage.py         # ZODB storage helpers（既存）
│   └── audit.py           # Audit logging（既存・拡張対象）
└── configure.zcml         # パッケージレベルZope設定（拡張対象）

tests/
├── test_plugin.py         # プラグインテスト（既存・拡張対象）
├── test_permissions.py    # 新規: パーミッションテスト
├── test_roles.py          # 新規: ロールテスト
├── test_session.py        # 新規: セッション管理テスト
├── test_policy.py         # 新規: ポリシーチェックテスト
├── test_integration_aal2.py  # 新規: AAL2統合テスト
└── fixtures/              # テストフィクスチャ
```

**Structure Decision**:

既存のc2.pas.aal2パッケージを拡張する形で実装します。Ploneの標準的な2ドット形式のパッケージ構造を維持し、以下の新規モジュールを追加：

- `permissions.py`: Plone.PASのカスタムパーミッション "Require AAL2 Authentication" を定義
- `roles.py`: カスタムロール "AAL2 Required User" を定義
- `session.py`: ユーザーのAAL2認証タイムスタンプを管理
- `policy.py`: AAL2ポリシーチェックとステップアップ認証ロジック

既存のファイル（`plugin.py`, `views.py`など）は、スタブメソッド（`get_aal_level`, `require_aal2`）を完全実装する形で拡張します。

## Complexity Tracking

**該当なし** - Constitution Checkに違反はありません。既存パッケージの拡張であり、Ploneの標準パターンに従った実装です。
