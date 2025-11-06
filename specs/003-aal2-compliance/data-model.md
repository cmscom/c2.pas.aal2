# Data Model: AAL2 Compliance

**Feature**: 003-aal2-compliance
**Date**: 2025-11-06
**Status**: Draft

## Overview

このドキュメントは、AAL2コンプライアンス機能で使用されるデータモデルを定義します。既存のPlone/PASデータモデルを拡張し、AAL2認証タイムスタンプ、パーミッション、ロールを追加します。

---

## Entity Definitions

### 1. AAL2 Authentication Timestamp

ユーザーが最後にパスキーで認証した時刻を記録するエンティティ。

**Storage**: ZODBアノテーション（ユーザーオブジェクト）
**Annotation Key**: `c2.pas.aal2.aal2_timestamp`

#### Attributes

| Attribute | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| `timestamp` | `datetime` (ISO 8601 string) | Yes | AAL2認証時刻（UTC） | 未来の時刻は無効 |
| `credential_id` | `str` | No | 使用されたパスキーのID | 長さ: 1-1024文字 |

#### Example

```python
{
    'timestamp': '2025-11-06T10:30:00.123456',
    'credential_id': 'AQIDBAUGBwgBAgMEBQYHCAECAwQFBgcI...'
}
```

#### Lifecycle

- **Created**: ユーザーがパスキーで認証成功時
- **Updated**: ユーザーが再度パスキーで認証成功時（上書き）
- **Deleted**: ユーザーアカウント削除時（カスケード削除）
- **Expires**: 15分経過後（論理的期限切れ、物理削除なし）

#### Relationships

- **User → AAL2 Timestamp**: 1対1（ユーザーごとに1つのタイムスタンプ）
- **Passkey → AAL2 Timestamp**: N対1（どのパスキーでも同じタイムスタンプを更新）

---

### 2. AAL2 Permission

コンテンツやリソースにAAL2認証を要求するパーミッション。

**Storage**: CMFCoreパーミッションレジストリ + コンテンツアノテーション

#### Definition

| Property | Value | Description |
|----------|-------|-------------|
| `permission_id` | `Require AAL2 Authentication` | 一意のパーミッション識別子 |
| `display_name` | `Require AAL2 Authentication` | UI表示名 |
| `description` | `AAL2レベルの認証を要求` | パーミッションの説明 |
| `default_roles` | `['Manager']` | 初期で付与されるロール |

#### Content-Level Application

コンテンツオブジェクトにAAL2パーミッション要件を設定する際、以下のアノテーションを使用：

**Annotation Key**: `c2.pas.aal2.require_aal2`
**Type**: `bool`
**Default**: `False`

```python
# コンテンツにAAL2保護を設定
annotations = IAnnotations(content)
annotations['c2.pas.aal2.require_aal2'] = True
```

#### Lifecycle

- **Created**: パッケージインストール時（GenericSetup）
- **Updated**: 管理者がロールマッピングを変更時
- **Deleted**: パッケージアンインストール時

#### Relationships

- **Permission → Roles**: N対M（複数のロールに割り当て可能）
- **Content → Permission Requirement**: 1対1（コンテンツごとにAAL2要件の有無）

---

### 3. AAL2 Role

ユーザーに割り当て可能なロール。このロールを持つユーザーは常にAAL2認証ポリシーの対象となる。

**Storage**: Ploneロールマネージャー（ZODB）

#### Definition

| Property | Value | Description |
|----------|-------|-------------|
| `role_id` | `AAL2 Required User` | 一意のロール識別子 |
| `display_name` | `AAL2 Required User` | UI表示名 |
| `description` | `このロールを持つユーザーは常にAAL2認証が必要` | ロールの説明 |
| `permissions` | `['Require AAL2 Authentication']` | 関連付けられたパーミッション |

#### Lifecycle

- **Created**: パッケージインストール時（GenericSetup `rolemap.xml`）
- **Assigned**: 管理者がユーザーにロールを付与
- **Revoked**: 管理者がユーザーからロールを削除
- **Deleted**: パッケージアンインストール時

#### Relationships

- **User → Role**: N対M（ユーザーは複数のロールを持つ、ロールは複数のユーザーに割り当てられる）
- **Role → Permission**: N対M（ロールは複数のパーミッションを持つ）

---

### 4. Passkey Credential (既存エンティティ)

002-passkey-login機能で定義済み。AAL2機能では参照のみ。

**Storage**: ZODBアノテーション（ユーザーオブジェクト）
**Annotation Key**: `c2.pas.aal2.passkeys`

#### Attributes (参照)

| Attribute | Type | Description |
|-----------|------|-------------|
| `credential_id` | `str` | WebAuthn credential ID（一意識別子） |
| `public_key` | `bytes` | 公開鍵 |
| `sign_count` | `int` | 署名カウンター（リプレイ攻撃防止） |
| `device_name` | `str` | デバイス名（ユーザー入力） |
| `device_type` | `str` | `'platform'` または `'cross-platform'` |
| `transports` | `list[str]` | `['usb', 'nfc', 'ble', 'internal']` |
| `created_at` | `datetime` | 登録日時 |
| `last_used_at` | `datetime` | 最終使用日時 |

#### Relationship to AAL2

- **Passkey → AAL2 Timestamp**: パスキー認証成功時にAAL2タイムスタンプを更新
- **User with Passkey → AAL2 Authentication**: パスキーがAAL2認証の唯一の方法

---

### 5. Protected Resource (概念エンティティ)

AAL2パーミッションが設定されたPloneコンテンツオブジェクト。

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `object_path` | `str` | コンテンツオブジェクトのパス（例: `/Plone/folder/document`） |
| `require_aal2` | `bool` | AAL2認証要件の有無（アノテーション） |
| `portal_type` | `str` | Ploneコンテンツタイプ（例: `Document`, `Folder`） |
| `workflow_state` | `str` | ワークフロー状態（例: `published`, `private`） |

#### Relationships

- **User → Protected Resource**: N対M（ユーザーは複数の保護リソースにアクセス可能）
- **Protected Resource → AAL2 Check**: 1対1（各保護リソースは1つのAAL2チェックをトリガー）

---

## Data Flow Diagrams

### 1. AAL2認証タイムスタンプの更新フロー

```text
┌─────────────────┐
│ User            │
│ (Plone User Obj)│
└────────┬────────┘
         │
         │ 1. パスキー認証成功
         ↓
┌─────────────────────────┐
│ AAL2Plugin              │
│ .verifyAuthentication() │
└────────┬────────────────┘
         │
         │ 2. タイムスタンプ更新
         ↓
┌─────────────────────────┐
│ session.py              │
│ set_aal2_timestamp()    │
└────────┬────────────────┘
         │
         │ 3. アノテーション書き込み
         ↓
┌─────────────────────────┐
│ IAnnotations(user)      │
│ ['c2.pas.aal2.          │
│  aal2_timestamp']       │
└─────────────────────────┘
```

### 2. AAL2要件チェックフロー

```text
┌──────────────────┐
│ HTTP Request     │
└────────┬─────────┘
         │
         │ 1. トラバーサル
         ↓
┌──────────────────────────┐
│ Published Object         │
│ (Plone Content)          │
└────────┬─────────────────┘
         │
         │ 2. セキュリティチェック
         ↓
┌──────────────────────────┐
│ AAL2Plugin               │
│ .validate(user, request) │
└────────┬─────────────────┘
         │
         │ 3. ポリシーチェック
         ↓
┌──────────────────────────┐
│ policy.py                │
│ is_aal2_required()       │
└────────┬─────────────────┘
         │
         ├─ Yes → 4a. タイムスタンプ検証
         │         ↓
         │    ┌──────────────────────┐
         │    │ session.py           │
         │    │ is_aal2_valid()      │
         │    └────────┬─────────────┘
         │             │
         │             ├─ Valid → 許可
         │             └─ Invalid → Unauthorized例外
         │
         └─ No → 許可
```

### 3. コンテンツレベルAAL2ポリシー設定フロー

```text
┌──────────────────┐
│ Administrator    │
└────────┬─────────┘
         │
         │ 1. AAL2設定画面にアクセス
         ↓
┌──────────────────────────┐
│ @@aal2-settings View     │
└────────┬─────────────────┘
         │
         │ 2. "AAL2保護を要求" チェック
         ↓
┌──────────────────────────┐
│ policy.py                │
│ set_aal2_required()      │
└────────┬─────────────────┘
         │
         │ 3. アノテーション書き込み
         ↓
┌──────────────────────────┐
│ IAnnotations(content)    │
│ ['c2.pas.aal2.           │
│  require_aal2'] = True   │
└──────────────────────────┘
```

---

## Validation Rules

### AAL2 Timestamp Validation

```python
def validate_aal2_timestamp(timestamp_str):
    """Validate AAL2 timestamp."""
    try:
        ts = datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        raise ValidationError("Invalid timestamp format")

    # Reject future timestamps
    if ts > datetime.utcnow():
        raise ValidationError("Timestamp cannot be in the future")

    # Reject very old timestamps (>24 hours)
    age = (datetime.utcnow() - ts).total_seconds()
    if age > 86400:  # 24 hours
        raise ValidationError("Timestamp too old (>24 hours)")

    return ts
```

### AAL2 Validity Check

```python
AAL2_TIMEOUT_SECONDS = 900  # 15 minutes

def is_aal2_valid(timestamp):
    """Check if AAL2 authentication is still valid."""
    if timestamp is None:
        return False

    if not isinstance(timestamp, datetime):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            return False

    now = datetime.utcnow()

    # Reject future timestamps
    if timestamp > now:
        return False

    elapsed = (now - timestamp).total_seconds()
    return 0 <= elapsed <= AAL2_TIMEOUT_SECONDS
```

---

## State Transitions

### AAL2 Authentication State Machine

```text
┌─────────────────┐
│ No AAL2 Auth    │ (初期状態)
└────────┬────────┘
         │
         │ パスキー認証成功
         ↓
┌─────────────────┐
│ AAL2 Valid      │ (15分間有効)
└────────┬────────┘
         │
         ├─ 15分経過 → ┌─────────────────┐
         │              │ AAL2 Expired    │
         │              └─────────────────┘
         │
         └─ 再認証 → [AAL2 Valid に戻る]
```

### Content AAL2 Policy State

```text
┌─────────────────────┐
│ No AAL2 Requirement │ (デフォルト)
└──────────┬──────────┘
           │
           │ 管理者が設定
           ↓
┌─────────────────────┐
│ AAL2 Required       │
└──────────┬──────────┘
           │
           │ 管理者が解除
           └── → [No AAL2 Requirement に戻る]
```

---

## Indexing & Query Patterns

### 1. ユーザーのAAL2ステータスクエリ

```python
def get_user_aal2_status(user_id):
    """Get user's current AAL2 authentication status."""
    user = get_user_object(user_id)
    if user is None:
        return {'valid': False, 'reason': 'user_not_found'}

    # Check if user has AAL2 role
    if 'AAL2 Required User' in user.getRoles():
        has_role = True
    else:
        has_role = False

    # Check timestamp
    timestamp = get_aal2_timestamp(user)
    is_valid = is_aal2_valid(timestamp)

    return {
        'valid': is_valid,
        'has_aal2_role': has_role,
        'timestamp': timestamp.isoformat() if timestamp else None,
        'expires_at': get_aal2_expiry(timestamp).isoformat() if timestamp else None
    }
```

### 2. AAL2保護コンテンツのリストクエリ

```python
def list_aal2_protected_content():
    """List all content requiring AAL2 authentication."""
    catalog = getToolByName(portal, 'portal_catalog')
    all_content = catalog()

    protected = []
    for brain in all_content:
        obj = brain.getObject()
        if is_aal2_required(obj):
            protected.append({
                'path': brain.getPath(),
                'title': brain.Title,
                'type': brain.portal_type,
                'url': brain.getURL()
            })

    return protected
```

**注意**: この実装はパフォーマンス的に非効率です。本番環境では、カタログインデックスを追加するか、専用のキャッシュを使用することを推奨します。

---

## Migration & Compatibility

### データ移行

**既存データへの影響**: なし

- 既存のユーザーは初期状態で AAL2タイムスタンプを持たない（`None`）
- 初回パスキー認証時にタイムスタンプが作成される
- 既存のコンテンツはデフォルトでAAL2不要（`False`）

### 後方互換性

- ✅ 既存の認証フローに影響なし
- ✅ パスキーを持たないユーザーは影響を受けない
- ✅ AAL2保護を設定していないコンテンツは通常通りアクセス可能

---

## Security Considerations

### 1. タイムスタンプ改ざん防止

- **対策**: ZODBのトランザクション整合性に依存
- **追加対策**: ログにタイムスタンプ変更を記録（監査証跡）

### 2. リプレイ攻撃防止

- **対策**: WebAuthnの`sign_count`メカニズム（既存実装）
- **AAL2への影響**: なし（パスキー認証レイヤーで処理済み）

### 3. セッションハイジャック対策

- **対策**: AAL2タイムスタンプは認証に依存、セッションIDのみでは無効化できない
- **追加対策**: IPアドレス変更時にAAL2タイムスタンプを無効化（オプション、初期実装では対象外）

---

## Performance Considerations

### 読み取りパフォーマンス

- **AAL2タイムスタンプ読み取り**: O(1) - アノテーション直接アクセス
- **AAL2ポリシーチェック**: O(1) - アノテーション直接アクセス
- **キャッシュ適用後**: リクエストスコープで再利用、ZODBアクセス最小化

### 書き込みパフォーマンス

- **AAL2タイムスタンプ更新**: O(1) - アノテーション上書き
- **競合リスク**: 低（ユーザーごとに独立したアノテーション）

### スケーラビリティ

- **100,000ユーザー**: ZODBは1M+オブジェクトに対応、AAL2タイムスタンプは問題なし
- **ボトルネック**: AAL2チェックの頻度、キャッシングで緩和

---

**Data Model Status**: ✅ Complete
**Review Date**: 2025-11-06
**Next Steps**: Phase 1 - Generate contracts/ and quickstart.md
