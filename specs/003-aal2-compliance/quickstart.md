# Quickstart Guide: AAL2 Compliance Development

**Feature**: 003-aal2-compliance
**Date**: 2025-11-06
**Target Audience**: 開発者

このガイドは、AAL2コンプライアンス機能の開発を開始するための手順を提供します。

---

## Prerequisites

開始する前に、以下が準備されていることを確認してください：

- ✅ Python 3.11以上
- ✅ Plone 5.2以上の開発環境
- ✅ Git（リポジトリクローン済み）
- ✅ c2.pas.aal2パッケージの既存コード（002-passkey-login機能）

---

## 1. 環境セットアップ

### Step 1: ブランチの確認

```bash
# 現在のブランチを確認
git branch

# 003-aal2-complianceブランチにいることを確認
# 出力: * 003-aal2-compliance
```

### Step 2: 仮想環境のアクティベート

```bash
# Python仮想環境をアクティベート（既存の場合）
source .venv/bin/activate

# または新規作成
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 3: 依存関係のインストール

```bash
# 既存の依存関係をインストール
pip install -e ".[test]"

# または
python setup.py develop
```

### Step 4: Plone開発サーバーの起動（オプション）

```bash
# Ploneサーバーを起動
bin/instance fg

# ブラウザで http://localhost:8080/Plone にアクセス
```

---

## 2. コードベースの理解

### 既存のファイル構造

```text
src/c2/pas/aal2/
├── __init__.py
├── interfaces.py          # IAAL2Plugin interface（既存）
├── plugin.py              # AAL2Plugin main class（拡張対象）
├── credential.py          # Passkey storage（既存）
├── browser/
│   ├── views.py           # WebAuthn views（既存）
│   └── viewlets.py        # UI elements（既存）
└── utils/
    ├── webauthn.py        # WebAuthn helpers（既存）
    └── audit.py           # Audit logging（既存）
```

### 新規作成するファイル

```text
src/c2/pas/aal2/
├── permissions.py         # 新規: AAL2パーミッション定義
├── roles.py               # 新規: AAL2ロール定義
├── session.py             # 新規: AAL2タイムスタンプ管理
├── policy.py              # 新規: AAL2ポリシーチェック
└── browser/
    └── aal2_challenge.pt  # 新規: チャレンジUIテンプレート
```

---

## 3. TDD開発フロー

AAL2機能は**テスト駆動開発（TDD）**で実装します。

### TDDサイクル

1. **Red**: テストを書く → 失敗することを確認
2. **Green**: 最小限のコードで実装 → テストをパス
3. **Refactor**: コードをリファクタリング → テストは引き続きパス

### Step 1: テストファイルの作成

```bash
# テストディレクトリに移動
cd tests/

# 新規テストファイルを作成
touch test_session.py
touch test_policy.py
touch test_permissions.py
touch test_roles.py
```

### Step 2: 最初のテストを書く（例: session.py）

```python
# tests/test_session.py
import pytest
from datetime import datetime, timedelta
from c2.pas.aal2.session import (
    set_aal2_timestamp,
    get_aal2_timestamp,
    is_aal2_valid,
)

def test_set_and_get_aal2_timestamp(plone_user):
    """Test setting and getting AAL2 timestamp."""
    set_aal2_timestamp(plone_user)
    timestamp = get_aal2_timestamp(plone_user)

    assert timestamp is not None
    assert isinstance(timestamp, datetime)
    assert timestamp <= datetime.utcnow()

def test_is_aal2_valid_fresh(plone_user):
    """Test AAL2 validity for fresh timestamp."""
    set_aal2_timestamp(plone_user)
    assert is_aal2_valid(plone_user) == True

def test_is_aal2_valid_expired(plone_user):
    """Test AAL2 validity for expired timestamp."""
    # タイムスタンプを16分前に設定
    old_timestamp = datetime.utcnow() - timedelta(minutes=16)
    annotations = IAnnotations(plone_user)
    annotations['c2.pas.aal2.aal2_timestamp'] = old_timestamp.isoformat()

    assert is_aal2_valid(plone_user) == False
```

### Step 3: テストを実行（失敗を確認）

```bash
# pytestを実行
pytest tests/test_session.py

# 期待される結果: FAILED (モジュールが存在しないため)
```

### Step 4: 実装を書く

```python
# src/c2/pas/aal2/session.py
"""AAL2 session management."""
from datetime import datetime, timedelta
from zope.annotation.interfaces import IAnnotations
import logging

logger = logging.getLogger('c2.pas.aal2.session')

ANNOTATION_KEY = 'c2.pas.aal2.aal2_timestamp'
AAL2_TIMEOUT_SECONDS = 900  # 15 minutes

def set_aal2_timestamp(user, credential_id=None):
    """Set AAL2 authentication timestamp for user."""
    annotations = IAnnotations(user)
    timestamp = datetime.utcnow().isoformat()
    annotations[ANNOTATION_KEY] = timestamp
    logger.info(f"Set AAL2 timestamp for user {user.getId()}")

def get_aal2_timestamp(user):
    """Get AAL2 authentication timestamp for user."""
    annotations = IAnnotations(user)
    timestamp_str = annotations.get(ANNOTATION_KEY)
    if timestamp_str:
        return datetime.fromisoformat(timestamp_str)
    return None

def is_aal2_valid(user):
    """Check if AAL2 authentication is still valid."""
    timestamp = get_aal2_timestamp(user)
    if timestamp is None:
        return False

    now = datetime.utcnow()
    if timestamp > now:  # Future timestamp is invalid
        return False

    elapsed = (now - timestamp).total_seconds()
    return 0 <= elapsed <= AAL2_TIMEOUT_SECONDS
```

### Step 5: テストを再実行（パスを確認）

```bash
pytest tests/test_session.py

# 期待される結果: PASSED
```

### Step 6: リファクタリング（必要に応じて）

コードをよりクリーンに、よりメンテナンス可能にリファクタリングします。

---

## 4. 開発の優先順位

以下の順序で開発を進めることを推奨します：

### Phase 1: Core Functionality（P1）

1. ✅ **session.py** - AAL2タイムスタンプ管理
   - `set_aal2_timestamp()`
   - `get_aal2_timestamp()`
   - `is_aal2_valid()`
   - Tests: `test_session.py`

2. ✅ **permissions.py** - AAL2パーミッション定義
   - `RequireAAL2Authentication`定数
   - Tests: `test_permissions.py`

3. ✅ **roles.py** - AAL2ロール定義（GenericSetup）
   - `profiles/default/rolemap.xml`
   - Tests: `test_roles.py`

4. ✅ **policy.py** - AAL2ポリシーチェック
   - `is_aal2_required()`
   - `check_aal2_access()`
   - Tests: `test_policy.py`

### Phase 2: PAS Integration（P1）

5. ✅ **plugin.py拡張** - スタブメソッドの実装
   - `get_aal_level()` - 実装
   - `require_aal2()` - 実装
   - `validate()` - AAL2チェックの統合
   - Tests: `test_plugin.py`（既存に追加）

### Phase 3: UI & UX（P2-P3）

6. ✅ **aal2_challenge.pt** - チャレンジUIテンプレート
   - ZPTテンプレート
   - WebAuthn JavaScript統合

7. ✅ **views.py拡張** - AAL2チャレンジビュー
   - `AAL2ChallengeView`クラス
   - Tests: `test_views.py`

8. ✅ **管理画面** - AAL2設定ビュー
   - `@@aal2-settings`ビュー
   - コンテンツにAAL2保護を設定するUI

---

## 5. 重要なコード例

### Example 1: Session API Usage

```python
from c2.pas.aal2.session import set_aal2_timestamp, is_aal2_valid

# パスキー認証成功時
user = acl_users.getUserById('john_doe')
set_aal2_timestamp(user, credential_id='AQIDBAUGBwg...')

# AAL2保護リソースアクセス時
if not is_aal2_valid(user):
    # Redirect to AAL2 challenge
    return request.RESPONSE.redirect('@@aal2-challenge')
```

### Example 2: Policy API Usage

```python
from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

# コンテンツにAAL2保護を設定
content = portal['sensitive-document']
set_aal2_required(content, required=True)

# AAL2要件をチェック
if is_aal2_required(content):
    print("This content requires AAL2 authentication")
```

### Example 3: Plugin Integration

```python
# plugin.py
from c2.pas.aal2.session import is_aal2_valid
from c2.pas.aal2.policy import is_aal2_required

class AAL2Plugin(BasePlugin):
    def get_aal_level(self, user_id):
        """Get the current AAL level for a user."""
        user = self._get_user(user_id)
        if user is None:
            return 1

        if is_aal2_valid(user):
            return 2
        return 1

    def require_aal2(self, user_id, context):
        """Determine if AAL2 is required."""
        user = self._get_user(user_id)
        return is_aal2_required(context, user)
```

---

## 6. デバッグとトラブルシューティング

### ログの確認

AAL2機能は詳細なログを出力します：

```bash
# Ploneログを確認
tail -f var/log/instance.log | grep 'c2.pas.aal2'

# 期待されるログメッセージ:
# INFO c2.pas.aal2.session Set AAL2 timestamp for user john_doe
# INFO c2.pas.aal2.plugin AAL2 authentication valid for user john_doe
```

### デバッグモードの有効化

```python
# buildout.cfg または instance.cfg
[instance]
debug-mode = on
verbose-security = on
```

### よくある問題

#### 問題1: "ImportError: No module named c2.pas.aal2.session"

**原因**: モジュールがインストールされていない

**解決**:
```bash
python setup.py develop
# または
pip install -e .
```

#### 問題2: "AttributeError: 'NoneType' object has no attribute 'getId'"

**原因**: ユーザーオブジェクトが`None`

**解決**: ユーザー存在チェックを追加
```python
user = acl_users.getUserById(user_id)
if user is None:
    raise ValueError(f"User not found: {user_id}")
```

#### 問題3: "ConflictError" during tests

**原因**: ZODBトランザクション競合

**解決**: テストで明示的にコミット
```python
import transaction
transaction.commit()
```

---

## 7. テスト実行

### 全テストを実行

```bash
# すべてのテストを実行
pytest tests/

# カバレッジ付きで実行
pytest --cov=c2.pas.aal2 --cov-report=html tests/

# カバレッジレポートを表示
open htmlcov/index.html
```

### 特定のテストを実行

```bash
# 特定のテストファイル
pytest tests/test_session.py

# 特定のテスト関数
pytest tests/test_session.py::test_is_aal2_valid_fresh

# キーワードマッチング
pytest -k "aal2 and valid"
```

### テストの並列実行

```bash
# pytest-xdistを使用（高速化）
pip install pytest-xdist
pytest -n auto tests/
```

---

## 8. コードレビューチェックリスト

プルリクエストを作成する前に、以下を確認してください：

- [ ] すべてのテストがパス（`pytest tests/`）
- [ ] テストカバレッジが90%以上（`pytest --cov`）
- [ ] ドキュメント文字列（docstrings）がすべての公開関数にある
- [ ] ログメッセージが適切なレベル（INFO, WARNING, ERROR）
- [ ] エラーハンドリングが適切（例外のキャッチとログ）
- [ ] コードスタイルがPEP 8に準拠（`ruff check .`）
- [ ] 型ヒント（type hints）が可能な限り追加されている
- [ ] パフォーマンス要件を満たしている（<50ms）
- [ ] セキュリティ考慮事項が文書化されている
- [ ] 既存のテストが壊れていない（回帰テスト）

---

## 9. リソース

### ドキュメント

- [spec.md](./spec.md) - 機能仕様書
- [research.md](./research.md) - 技術調査
- [data-model.md](./data-model.md) - データモデル
- [contracts/](./contracts/) - APIコントラクト
- [plan.md](./plan.md) - 実装計画

### 外部リソース

- [Plone.PAS Documentation](https://docs.plone.org/develop/plone/security/pas.html)
- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [NIST AAL2 Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [Zope Annotations](https://zope.readthedocs.io/en/latest/zopebook/AnnotationStuff.html)

---

## 10. ヘルプとサポート

### 質問や問題

- **Issues**: GitHubリポジトリのIssuesページ
- **Discussion**: プロジェクトのディスカッションフォーラム

### 貢献ガイドライン

新機能や改善を貢献する際は、以下に従ってください：

1. Issueを作成して提案を議論
2. ブランチを作成（例: `feature/improve-aal2-caching`）
3. TDDで実装（テスト → コード → リファクタ）
4. プルリクエストを作成
5. コードレビューを受ける
6. マージ後、ブランチを削除

---

**Quickstart Version**: 1.0.0
**Last Updated**: 2025-11-06
**Next Steps**: [tasks.md](./tasks.md)を実行して具体的な実装タスクを生成（`/speckit.tasks`コマンド）
