# Policy API Contract

**Module**: `c2.pas.aal2.policy`
**Purpose**: AAL2ポリシーチェックとステップアップ認証
**Type**: Internal Python API

---

## Functions

### `is_aal2_required(context, user=None)`

コンテンツオブジェクトまたはユーザーに対してAAL2認証が必要かチェックします。

**Parameters**:
- `context` (`Content | None`): Ploneコンテンツオブジェクト
- `user` (`PloneUser | None`, optional): Ploneユーザーオブジェクト（省略時は現在のユーザー）

**Returns**: `bool`
- `True`: AAL2認証が必要
- `False`: AAL2認証不要

**Logic**:
1. ユーザーが`AAL2 Required User`ロールを持つ場合 → `True`
2. コンテンツに`c2.pas.aal2.require_aal2`アノテーションが`True`の場合 → `True`
3. それ以外 → `False`

**Example**:
```python
from c2.pas.aal2.policy import is_aal2_required

# コンテンツベースのチェック
content = portal['sensitive-document']
if is_aal2_required(content):
    print("AAL2 authentication required for this content")

# ユーザーベースのチェック
user = acl_users.getUserById('admin')
if is_aal2_required(None, user):
    print("User has AAL2 Required role")
```

---

### `set_aal2_required(context, required=True)`

コンテンツオブジェクトにAAL2認証要件を設定します。

**Parameters**:
- `context` (`Content`): Ploneコンテンツオブジェクト
- `required` (`bool`, default=`True`): AAL2要件の有無

**Returns**: `None`

**Side Effects**:
- コンテンツアノテーションに`c2.pas.aal2.require_aal2`を設定
- ZODBトランザクションに変更をマーク
- キャッシュを無効化（`ram.cache`）

**Permissions**:
- 実行には`Manage portal`パーミッションが必要（呼び出し側で確認）

**Example**:
```python
from c2.pas.aal2.policy import set_aal2_required

content = portal['sensitive-document']
set_aal2_required(content, required=True)
```

---

### `check_aal2_access(context, user, request)`

ユーザーがコンテンツへのAAL2アクセス要件を満たしているかチェックします。

**Parameters**:
- `context` (`Content`): Ploneコンテンツオブジェクト
- `user` (`PloneUser`): Ploneユーザーオブジェクト
- `request` (`HTTPRequest`): HTTPリクエストオブジェクト

**Returns**: `dict`
```python
{
    'allowed': bool,           # アクセス許可の有無
    'reason': str | None,      # 拒否理由（allowedがFalseの場合）
    'requires_stepup': bool,   # ステップアップ認証が必要か
    'aal2_required': bool,     # AAL2が必要か
    'aal2_valid': bool         # AAL2認証が有効か
}
```

**Logic**:
1. `is_aal2_required(context, user)`でAAL2要件をチェック
2. AAL2不要の場合 → `{'allowed': True, 'requires_stepup': False}`
3. AAL2必要な場合:
   - `is_aal2_valid(user)`で有効性をチェック
   - 有効な場合 → `{'allowed': True, 'aal2_valid': True}`
   - 無効な場合 → `{'allowed': False, 'requires_stepup': True, 'reason': 'aal2_expired'}`

**Example**:
```python
from c2.pas.aal2.policy import check_aal2_access

content = portal['sensitive-document']
user = acl_users.getUserById('john_doe')
result = check_aal2_access(content, user, request)

if not result['allowed']:
    if result['requires_stepup']:
        # Redirect to AAL2 challenge
        return request.RESPONSE.redirect('@@aal2-challenge')
```

---

### `get_stepup_challenge_url(context, request)`

ステップアップ認証（AAL2チャレンジ）のURLを生成します。

**Parameters**:
- `context` (`Content`): Ploneコンテンツオブジェクト（アクセスしようとしたコンテンツ）
- `request` (`HTTPRequest`): HTTPリクエストオブジェクト

**Returns**: `str`
- AAL2チャレンジビューのURL（例: `/Plone/@@aal2-challenge?came_from=/Plone/document`）

**Example**:
```python
from c2.pas.aal2.policy import get_stepup_challenge_url

content = portal['sensitive-document']
challenge_url = get_stepup_challenge_url(content, request)
# Returns: '/Plone/@@aal2-challenge?came_from=/Plone/sensitive-document'
```

---

### `list_aal2_protected_content()`

AAL2保護が設定されているすべてのコンテンツをリストします。

**Parameters**: なし

**Returns**: `list[dict]`
```python
[
    {
        'path': str,           # コンテンツパス
        'title': str,          # コンテンツタイトル
        'portal_type': str,    # コンテンツタイプ
        'url': str             # コンテンツURL
    },
    ...
]
```

**Performance Note**:
- ⚠️ この関数は全コンテンツをスキャンするため、大規模サイトでは遅い
- 管理画面やレポート目的でのみ使用
- 本番環境では、専用のカタログインデックスの追加を推奨

**Example**:
```python
from c2.pas.aal2.policy import list_aal2_protected_content

protected = list_aal2_protected_content()
for item in protected:
    print(f"{item['title']} ({item['path']}) requires AAL2")
```

---

## Constants

### `AAL2_POLICY_KEY`

**Type**: `str`
**Value**: `'c2.pas.aal2.require_aal2'`
**Description**: コンテンツアノテーションのキー

---

## Error Handling

### `AAL2PolicyError`

カスタム例外クラス（AAL2ポリシー関連エラー）

**Base Class**: `Exception`

**Usage**:
```python
class AAL2PolicyError(Exception):
    """AAL2 policy-related error."""
    pass

# Example
if not has_permission('Manage portal', context):
    raise AAL2PolicyError("Insufficient permissions to set AAL2 policy")
```

---

## Caching Strategy

### Content Policy Cache

```python
from plone.memoize import ram

def _content_policy_cache_key(method, context):
    """Cache key for content AAL2 policy."""
    return (context.absolute_url_path(), time.time() // 300)  # 5 minutes

@ram.cache(_content_policy_cache_key)
def is_aal2_required(context, user=None):
    # Implementation
    pass
```

**Cache Invalidation**:
- `set_aal2_required()`呼び出し時に自動無効化
- キャッシュ期間: 5分（300秒）

---

## Integration with PAS Plugin

### `AAL2Plugin.validate()` Integration

```python
# plugin.py
from c2.pas.aal2.policy import check_aal2_access, get_stepup_challenge_url

class AAL2Plugin(BasePlugin):
    def validate(self, user, request):
        """Validate AAL2 requirements."""
        published = request.get('PUBLISHED')
        if published is None:
            return True

        context = getattr(published, 'context', None)
        if context is None:
            return True

        result = check_aal2_access(context, user, request)
        if not result['allowed']:
            if result['requires_stepup']:
                # Store redirect URL in session
                request.SESSION['aal2_came_from'] = request.URL
                # Raise Unauthorized
                from AccessControl import Unauthorized
                raise Unauthorized('AAL2 authentication required')

        return True
```

---

## Testing Contract

### Unit Tests

```python
def test_is_aal2_required_by_content():
    """Test AAL2 requirement by content annotation."""
    content = create_test_content('Document', 'test-doc')
    assert is_aal2_required(content) == False
    set_aal2_required(content, required=True)
    assert is_aal2_required(content) == True

def test_is_aal2_required_by_role():
    """Test AAL2 requirement by user role."""
    user = create_test_user('test_user', roles=['AAL2 Required User'])
    assert is_aal2_required(None, user) == True

def test_check_aal2_access_allowed():
    """Test AAL2 access check when allowed."""
    content = create_test_content('Document', 'test-doc')
    user = create_test_user('test_user')
    result = check_aal2_access(content, user, request)
    assert result['allowed'] == True
    assert result['requires_stepup'] == False

def test_check_aal2_access_requires_stepup():
    """Test AAL2 access check when stepup required."""
    content = create_test_content('Document', 'test-doc')
    set_aal2_required(content, required=True)
    user = create_test_user('test_user')
    result = check_aal2_access(content, user, request)
    assert result['allowed'] == False
    assert result['requires_stepup'] == True
    assert result['reason'] == 'aal2_expired'
```

### Integration Tests

```python
def test_stepup_authentication_flow():
    """Test complete stepup authentication flow."""
    # 1. Set up protected content
    content = create_test_content('Document', 'protected-doc')
    set_aal2_required(content, required=True)

    # 2. User without AAL2 tries to access
    user = create_test_user('test_user')
    login_as(user)
    response = browser.open(content.absolute_url())
    # Should redirect to AAL2 challenge
    assert '@@aal2-challenge' in response.url

    # 3. User authenticates with passkey
    authenticate_with_passkey(user)

    # 4. User can now access content
    response = browser.open(content.absolute_url())
    assert response.status == 200
    assert 'protected-doc' in response.text
```

---

## Performance Contract

| Operation | Time Complexity | Target | Notes |
|-----------|-----------------|--------|-------|
| `is_aal2_required` | O(1) | <10ms | アノテーション読み取り（キャッシュ付き） |
| `set_aal2_required` | O(1) | <50ms | アノテーション書き込み |
| `check_aal2_access` | O(1) | <50ms | 複数のO(1)操作の組み合わせ |
| `list_aal2_protected_content` | O(N) | <5s | N=全コンテンツ数、管理操作のみ |

---

## Security Considerations

### 1. Permission Checks

`set_aal2_required()`を呼び出すビューは、適切なパーミッションチェックを実装する必要があります：

```python
from AccessControl import getSecurityManager

def aal2_settings_view(self):
    """AAL2 settings view with permission check."""
    sm = getSecurityManager()
    if not sm.checkPermission('Manage portal', self.context):
        raise Unauthorized("You don't have permission to change AAL2 settings")

    # Proceed with settings
    set_aal2_required(self.context, required=True)
```

### 2. CSRF Protection

AAL2設定変更には、PloneのCSRFトークン（`authenticator`）が必要です。

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-06 | Initial contract definition |
