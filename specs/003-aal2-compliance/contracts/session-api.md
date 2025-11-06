# Session API Contract

**Module**: `c2.pas.aal2.session`
**Purpose**: AAL2認証タイムスタンプの管理
**Type**: Internal Python API

---

## Functions

### `set_aal2_timestamp(user, credential_id=None)`

ユーザーのAAL2認証タイムスタンプを現在時刻に設定します。

**Parameters**:
- `user` (`PloneUser`): Ploneユーザーオブジェクト
- `credential_id` (`str`, optional): 使用されたパスキーのcredential ID

**Returns**: `None`

**Raises**:
- `ValueError`: ユーザーオブジェクトが無効な場合

**Side Effects**:
- ユーザーアノテーションに`c2.pas.aal2.aal2_timestamp`を書き込み
- ZODBトランザクションに変更をマーク

**Example**:
```python
from c2.pas.aal2.session import set_aal2_timestamp

user = acl_users.getUserById('john_doe')
set_aal2_timestamp(user, credential_id='AQIDBAUGBwg...')
```

---

### `get_aal2_timestamp(user)`

ユーザーのAAL2認証タイムスタンプを取得します。

**Parameters**:
- `user` (`PloneUser`): Ploneユーザーオブジェクト

**Returns**: `datetime | None`
- `datetime`: AAL2認証タイムスタンプ（UTC）
- `None`: タイムスタンプが設定されていない場合

**Raises**:
- `ValueError`: ユーザーオブジェクトが無効な場合

**Example**:
```python
from c2.pas.aal2.session import get_aal2_timestamp

user = acl_users.getUserById('john_doe')
timestamp = get_aal2_timestamp(user)
if timestamp:
    print(f"AAL2 authenticated at: {timestamp.isoformat()}")
```

---

### `is_aal2_valid(user)`

ユーザーのAAL2認証が有効（15分以内）かチェックします。

**Parameters**:
- `user` (`PloneUser`): Ploneユーザーオブジェクト

**Returns**: `bool`
- `True`: AAL2認証が有効（15分以内）
- `False`: 無効（タイムスタンプなし、または15分経過）

**Algorithm**:
1. `get_aal2_timestamp(user)`でタイムスタンプを取得
2. タイムスタンプが`None`の場合、`False`を返す
3. 現在時刻（UTC）との差分を計算
4. 差分が900秒（15分）以内であれば`True`、それ以外は`False`

**Example**:
```python
from c2.pas.aal2.session import is_aal2_valid

user = acl_users.getUserById('john_doe')
if is_aal2_valid(user):
    print("AAL2 authentication is still valid")
else:
    print("AAL2 re-authentication required")
```

---

### `get_aal2_expiry(user)`

ユーザーのAAL2認証有効期限を取得します。

**Parameters**:
- `user` (`PloneUser`): Ploneユーザーオブジェクト

**Returns**: `datetime | None`
- `datetime`: AAL2認証有効期限（UTC）
- `None`: タイムスタンプが設定されていない場合

**Formula**: `timestamp + timedelta(seconds=900)`

**Example**:
```python
from c2.pas.aal2.session import get_aal2_expiry

user = acl_users.getUserById('john_doe')
expiry = get_aal2_expiry(user)
if expiry:
    print(f"AAL2 expires at: {expiry.isoformat()}")
```

---

### `clear_aal2_timestamp(user)`

ユーザーのAAL2認証タイムスタンプをクリア（削除）します。

**Parameters**:
- `user` (`PloneUser`): Ploneユーザーオブジェクト

**Returns**: `None`

**Side Effects**:
- ユーザーアノテーションから`c2.pas.aal2.aal2_timestamp`を削除
- ZODBトランザクションに変更をマーク

**Use Cases**:
- テスト時のクリーンアップ
- 管理者による強制ログアウト（将来実装）

**Example**:
```python
from c2.pas.aal2.session import clear_aal2_timestamp

user = acl_users.getUserById('john_doe')
clear_aal2_timestamp(user)
```

---

## Constants

### `AAL2_TIMEOUT_SECONDS`

**Type**: `int`
**Value**: `900` (15分)
**Description**: AAL2認証の有効期限（秒）

### `ANNOTATION_KEY`

**Type**: `str`
**Value**: `'c2.pas.aal2.aal2_timestamp'`
**Description**: ユーザーアノテーションのキー

---

## Error Handling

すべての関数は以下のエラーハンドリングパターンに従います：

```python
try:
    # Operation
except AttributeError:
    raise ValueError("Invalid user object")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

---

## Performance Contract

| Operation | Time Complexity | Notes |
|-----------|-----------------|-------|
| `set_aal2_timestamp` | O(1) | アノテーション書き込み |
| `get_aal2_timestamp` | O(1) | アノテーション読み取り |
| `is_aal2_valid` | O(1) | 単純な算術比較 |
| `get_aal2_expiry` | O(1) | 単純な加算 |
| `clear_aal2_timestamp` | O(1) | アノテーション削除 |

**Target**: すべての操作 <10ms（ZODBキャッシュヒット時）

---

## Thread Safety

- ✅ **Thread-safe**: ZODBのトランザクション分離により保証
- ✅ **Concurrent writes**: `ConflictError`が発生する可能性があるが、ZODBが自動リトライ

---

## Testing Contract

### Unit Tests

```python
def test_set_and_get_aal2_timestamp():
    """Test setting and getting AAL2 timestamp."""
    user = create_test_user('test_user')
    set_aal2_timestamp(user)
    timestamp = get_aal2_timestamp(user)
    assert timestamp is not None
    assert isinstance(timestamp, datetime)
    assert timestamp <= datetime.utcnow()

def test_is_aal2_valid_fresh():
    """Test AAL2 validity check for fresh timestamp."""
    user = create_test_user('test_user')
    set_aal2_timestamp(user)
    assert is_aal2_valid(user) == True

def test_is_aal2_valid_expired():
    """Test AAL2 validity check for expired timestamp."""
    user = create_test_user('test_user')
    # Set timestamp 16 minutes ago
    old_timestamp = datetime.utcnow() - timedelta(minutes=16)
    annotations = IAnnotations(user)
    annotations[ANNOTATION_KEY] = old_timestamp.isoformat()
    assert is_aal2_valid(user) == False

def test_clear_aal2_timestamp():
    """Test clearing AAL2 timestamp."""
    user = create_test_user('test_user')
    set_aal2_timestamp(user)
    clear_aal2_timestamp(user)
    assert get_aal2_timestamp(user) is None
```

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-06 | Initial contract definition |
