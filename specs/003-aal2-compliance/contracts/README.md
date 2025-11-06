# API Contracts Overview

**Feature**: 003-aal2-compliance
**Date**: 2025-11-06

このディレクトリには、AAL2コンプライアンス機能の内部APIコントラクトが含まれています。

## Contracts

### 1. [Session API](./session-api.md)

**Module**: `c2.pas.aal2.session`

AAL2認証タイムスタンプの管理を担当します。

**Key Functions**:
- `set_aal2_timestamp(user, credential_id=None)` - タイムスタンプを設定
- `get_aal2_timestamp(user)` - タイムスタンプを取得
- `is_aal2_valid(user)` - AAL2有効性をチェック（15分ルール）
- `get_aal2_expiry(user)` - 有効期限を取得
- `clear_aal2_timestamp(user)` - タイムスタンプをクリア

**Use Cases**:
- パスキー認証成功時のタイムスタンプ記録
- AAL2保護リソースアクセス時の有効性チェック
- ユーザーダッシュボードでの有効期限表示

---

### 2. [Policy API](./policy-api.md)

**Module**: `c2.pas.aal2.policy`

AAL2ポリシーのチェックとステップアップ認証を担当します。

**Key Functions**:
- `is_aal2_required(context, user=None)` - AAL2要件をチェック
- `set_aal2_required(context, required=True)` - コンテンツにAAL2保護を設定
- `check_aal2_access(context, user, request)` - AAL2アクセス要件の包括的チェック
- `get_stepup_challenge_url(context, request)` - チャレンジURLを生成
- `list_aal2_protected_content()` - 保護コンテンツをリスト

**Use Cases**:
- PASプラグインの`validate()`メソッドでの統合
- 管理画面でのAAL2ポリシー設定
- Unauthorizedエラー発生時のチャレンジURLリダイレクト

---

## API Dependency Graph

```text
┌─────────────────────┐
│ AAL2Plugin          │
│ (plugin.py)         │
└──────────┬──────────┘
           │
           │ uses
           ↓
┌─────────────────────────────────────────┐
│ Policy API                              │
│ - check_aal2_access()                   │
│ - is_aal2_required()                    │
└──────────┬──────────────────────────────┘
           │
           │ uses
           ↓
┌─────────────────────────────────────────┐
│ Session API                             │
│ - is_aal2_valid()                       │
│ - get_aal2_timestamp()                  │
└─────────────────────────────────────────┘
```

**Dependency Rules**:
- ❌ Session API は Policy API に依存してはいけない（循環依存回避）
- ✅ Policy API は Session API を使用できる
- ✅ Plugin は両方のAPIを使用できる

---

## Contract Versioning

すべてのAPIコントラクトは[Semantic Versioning](https://semver.org/)に従います：

- **Major**: 互換性のない変更（例: 関数シグネチャ変更）
- **Minor**: 後方互換性のある機能追加（例: 新関数追加）
- **Patch**: バグ修正、ドキュメント更新

**Current Versions**:
- Session API: `1.0.0`
- Policy API: `1.0.0`

---

## Testing Requirements

各APIコントラクトには、以下のテストカバレッジが必要です：

| Test Type | Coverage Target | Location |
|-----------|-----------------|----------|
| Unit Tests | 90%+ | `tests/test_<module>.py` |
| Integration Tests | 主要フロー | `tests/test_integration_aal2.py` |
| Contract Tests | すべての公開関数 | `tests/test_<module>_contract.py` |

**Contract Test Example**:
```python
def test_session_api_contract():
    """Verify Session API adheres to contract."""
    from c2.pas.aal2.session import (
        set_aal2_timestamp,
        get_aal2_timestamp,
        is_aal2_valid,
        get_aal2_expiry,
        clear_aal2_timestamp
    )

    # Verify function signatures
    assert callable(set_aal2_timestamp)
    assert callable(get_aal2_timestamp)
    # ... etc
```

---

## Performance Contracts

すべてのAPIは以下のパフォーマンス要件を満たす必要があります：

| API | Operation | Target Latency | Max Latency |
|-----|-----------|----------------|-------------|
| Session API | `get_aal2_timestamp` | <5ms | <10ms |
| Session API | `set_aal2_timestamp` | <20ms | <50ms |
| Session API | `is_aal2_valid` | <5ms | <10ms |
| Policy API | `is_aal2_required` | <10ms | <20ms |
| Policy API | `check_aal2_access` | <30ms | <50ms |
| Policy API | `set_aal2_required` | <30ms | <100ms |

**Measurement**: 99パーセンタイル、本番相当環境

---

## Error Handling Standards

すべてのAPI関数は、以下のエラーハンドリングパターンに従う必要があります：

### 1. 入力検証エラー

```python
def function(param):
    if not is_valid(param):
        raise ValueError(f"Invalid parameter: {param}")
```

### 2. 権限エラー

```python
from AccessControl import Unauthorized

def function(context):
    if not has_permission(context):
        raise Unauthorized("Insufficient permissions")
```

### 3. 予期しないエラー

```python
import logging
logger = logging.getLogger(__name__)

def function():
    try:
        # Operation
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

---

## Documentation Requirements

各APIコントラクトドキュメントには、以下のセクションが必要です：

1. ✅ **Overview**: モジュールの目的と範囲
2. ✅ **Functions**: すべての公開関数の詳細
   - Parameters
   - Returns
   - Raises
   - Examples
3. ✅ **Constants**: モジュールレベルの定数
4. ✅ **Error Handling**: エラーハンドリングパターン
5. ✅ **Performance Contract**: パフォーマンス要件
6. ✅ **Testing Contract**: テスト要件とサンプル
7. ✅ **Change Log**: バージョン履歴

---

## Maintenance

### Contract Review Process

1. **Quarterly Review**: すべてのコントラクトを四半期ごとにレビュー
2. **Breaking Changes**: メジャーバージョンアップには、移行ガイドが必要
3. **Deprecation Policy**: 非推奨APIは、削除前に2つのマイナーバージョン期間サポート

### Contact

**Maintainer**: c2.pas.aal2開発チーム
**Last Updated**: 2025-11-06
