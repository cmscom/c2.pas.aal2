# AAL2 カスタムCookieセッション実装

## 概要

パスキーログイン後のセッション永続化問題を解決するため、**AAL2独自の認証Cookie管理機構**を実装しました。

この実装は `/temp_folder/session_data` に依存せず、`plone.session.tktauth` の署名付きチケット形式を使用して安全な認証状態を維持します。

---

## 実装内容

### 1. 署名付き認証チケットの生成

**場所**: `/workspace/src/c2/pas/aal2/plugin.py:773-845`

**機能**:
- `ICredentialsUpdatePlugin.updateCredentials()` メソッドを実装
- パスキーログイン成功時に署名付き認証チケットを生成
- `__ac` Cookieとして設定

**セキュリティ特性**:
- HMAC SHA-256による署名（`mod_auth_tkt` より安全）
- IPアドレスベースの検証
- 7日間のタイムアウト
- 64バイト（512ビット）のランダムシークレット

**コード例**:
```python
def updateCredentials(self, request, response, login, new_password):
    secret = self._get_or_create_secret()
    ticket = createTicket(
        secret=secret,
        userid=login,
        tokens=(),
        user_data='',
        ip=remote_addr,
        timestamp=int(time.time()),
        mod_auth_tkt=False,  # HMAC SHA-256
    )
    response.setCookie('__ac', quote(ticket), path='/', http_only=True)
```

### 2. 認証チケットの検証

**場所**: `/workspace/src/c2/pas/aal2/plugin.py:103-151`

**機能**:
- `IExtractionPlugin.extractCredentials()` メソッドで `__ac` Cookieを読み取り
- 署名を検証し、タイムアウトをチェック
- 有効なチケットから認証情報を抽出

**検証手順**:
1. Cookieから `__ac` 値を取得
2. URLデコードしてバイト列に変換
3. `validateTicket()` で署名とタイムアウトを検証
4. 検証成功時、`aal2_ticket` extractorとして認証情報を返す

**コード例**:
```python
def extractCredentials(self, request):
    cookie = request.get('__ac')
    if cookie:
        ticket = unquote(cookie).encode('latin-1')
        secret = self._get_or_create_secret()
        result = validateTicket(
            secret=secret,
            ticket=ticket,
            ip=remote_addr,
            timeout=86400 * 7,
        )
        if result:
            digest, userid, tokens, user_data, timestamp = result
            return {
                'extractor': 'aal2_ticket',
                'login': userid,
                'aal2_authenticated': True,
            }
```

### 3. 認証情報の確認

**場所**: `/workspace/src/c2/pas/aal2/plugin.py:157-164`

**機能**:
- `IAuthenticationPlugin.authenticateCredentials()` で `aal2_ticket` extractorを処理
- チケットベース認証を許可

**コード例**:
```python
def authenticateCredentials(self, credentials):
    if credentials.get('extractor') == 'aal2_ticket':
        username = credentials.get('login')
        if username:
            return (username, username)
```

### 4. シークレット管理

**場所**: `/workspace/src/c2/pas/aal2/plugin.py:829-850`

**機能**:
- プラグインインスタンスに固有のシークレットを自動生成
- ZODBに永続化
- 初回アクセス時に自動生成、その後再利用

**コード例**:
```python
def _get_or_create_secret(self):
    if not hasattr(self, '_aal2_secret') or not self._aal2_secret:
        import secrets
        self._aal2_secret = secrets.token_bytes(64)
        self._p_changed = True  # ZODB persistence
    return self._aal2_secret
```

---

## 技術的な特徴

### セキュリティ

1. **署名付きチケット**: HMAC SHA-256で改ざん検知
2. **IPアドレス検証**: チケット生成時のIPと検証時のIPを照合
3. **タイムアウト**: 7日間で自動失効
4. **HttpOnly Cookie**: JavaScriptからアクセス不可
5. **ランダムシークレット**: 512ビットの高エントロピーシークレット

### Plone統合

- **PASプラグイン**: 標準的なPASインターフェイスを実装
- **既存認証との共存**: 他のPASプラグインと競合しない
- **ZODB永続化**: シークレットはZODBに保存され、再起動後も有効

### `plone.session` との違い

| 項目 | `plone.session` | AAL2カスタム実装 |
|------|-----------------|------------------|
| セッションコンテナ | 必要 (`/temp_folder/session_data`) | 不要 |
| 依存関係 | `SessionDataManager` | なし |
| Cookie形式 | 署名付きチケット | 署名付きチケット（同じ） |
| 署名アルゴリズム | 設定可能 | HMAC SHA-256固定 |
| シークレット管理 | 手動設定 | 自動生成 |

---

## 動作フロー

### 初回ログイン（パスキー認証）

```
1. ユーザーがパスキーでログイン
   ↓
2. PasskeyLoginVerifyView が WebAuthn検証を実行
   ↓
3. 検証成功時、AAL2Plugin.updateCredentials() を呼び出し
   ↓
4. 署名付きチケットを生成し、__ac Cookieを設定
   ↓
5. ブラウザにリダイレクト（Cookie付き）
```

### 2回目以降のアクセス

```
1. ブラウザが __ac Cookie付きでリクエスト
   ↓
2. AAL2Plugin.extractCredentials() が呼ばれる
   ↓
3. Cookieから認証チケットを取得・検証
   ↓
4. 有効なチケット → 認証情報を返す
   ↓
5. AAL2Plugin.authenticateCredentials() でユーザー認証
   ↓
6. ログイン状態でページ表示
```

---

## テスト手順

### 1. Ploneを起動

```bash
make start
```

### 2. パスキー登録

1. ユーザーでログイン（通常の方法）
2. パスキー登録画面にアクセス: `http://localhost:8080/Plone/@@passkey-register`
3. パスキーを登録

### 3. パスキーログイン

1. ログアウト
2. ログイン画面でパスキーログインを選択
3. パスキーで認証

### 4. セッション永続化の確認

1. ログイン成功後、別のページに遷移
2. **期待される動作**: ログイン状態が継続する
3. **確認方法**:
   - ブラウザ開発者ツールで `__ac` Cookieの存在を確認
   - サーバーログで `Valid authentication ticket for user <username>` を確認

### 5. ログの確認

```bash
tail -f var/log/instance.log | grep -E "(AAL2|authentication|ticket)"
```

**期待されるログ**:
```
INFO [c2.pas.aal2.plugin] Set AAL2 authentication cookie for user terada (IP: 127.0.0.1)
DEBUG [c2.pas.aal2.plugin] Valid authentication ticket for user terada
DEBUG [c2.pas.aal2.plugin] Authenticated user terada via AAL2 ticket
```

---

## トラブルシューティング

### Cookieが設定されない

**確認**:
```python
# views.py で updateCredentials() が呼ばれているか確認
logger.info(f"Called AAL2Plugin.updateCredentials() for user {user_id}")
```

**解決策**:
- レスポンスオブジェクトが正しく渡されているか確認
- CSRFプロテクションが無効化されているか確認

### チケット検証に失敗

**ログ**:
```
DEBUG [c2.pas.aal2.plugin] Invalid authentication ticket
```

**原因の可能性**:
1. IPアドレスの不一致（プロキシ経由など）
2. タイムアウト（7日間経過）
3. シークレットの再生成（Plone再起動など）

**解決策**:
- `validateTicket()` のIPパラメータを `"0.0.0.0"` に設定してIPチェックを無効化（開発環境のみ）

### シークレットが保存されない

**確認**:
```python
# ZODBへの書き込みが発生しているか確認
self._p_changed = True
```

**解決策**:
- トランザクションがコミットされているか確認
- ZODB設定を確認

---

## 今後の改善案

### 1. IPアドレス検証の柔軟化

現在、IPアドレスが固定されている環境を想定していますが、モバイル環境やプロキシ経由では問題になる可能性があります。

**提案**:
- 設定可能なIPチェックモード（strict / relaxed / disabled）
- プロキシ対応の改善

### 2. Remember Me 機能

現在、タイムアウトは7日間固定です。

**提案**:
- ユーザー選択可能な有効期限
- 短期セッション（ブラウザ閉じるまで）vs 長期セッション（30日間）

### 3. セッション管理UI

**提案**:
- アクティブセッション一覧表示
- リモートログアウト（他のデバイスからログアウト）

### 4. 監査ログの拡充

**提案**:
- Cookie認証イベントのロギング
- 不正なチケットの検出ログ

---

## まとめ

### 解決した問題

✅ `/temp_folder/session_data` への依存を除去
✅ パスキーログイン後のセッション永続化
✅ 安全な署名付きチケット認証
✅ ZODB統合によるシークレット管理

### 実装の利点

- **Plone標準から大きく外れない**: `plone.session.tktauth` を利用
- **保守性**: PAS標準インターフェイスを実装
- **セキュリティ**: HMAC SHA-256、IPチェック、タイムアウト
- **自己完結**: 外部依存なし（`/temp_folder` 不要）

---

**実装日**: 2025-11-10
**実装者**: Claude Code
**関連ファイル**:
- `/workspace/src/c2/pas/aal2/plugin.py`
- `/workspace/SESSION_ISSUE_ANALYSIS.md` (問題分析)
- `/workspace/REFACTORING_TODO.md` (将来の改善)
