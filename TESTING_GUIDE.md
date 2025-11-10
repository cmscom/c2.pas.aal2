# パスキーログイン テストガイド

## クイックスタート

### 1. Plone起動

```bash
cd /workspace
make start
```

### 2. パスキー登録

1. ブラウザで `http://localhost:8080/Plone` にアクセス
2. 既存ユーザーでログイン（例: `admin`）
3. パスキー登録ページにアクセス: `http://localhost:8080/Plone/@@passkey-register`
4. 表示されたフォームで「Register Passkey」をクリック
5. ブラウザのパスキー登録プロンプトに従う

**期待される結果**:
- ✅ パスキーが登録される
- ✅ 成功メッセージが表示される
- ✅ 監査ログに記録される

### 3. ログアウト

1. Ploneの標準ログアウト機能を使用
2. Cookie `__ac` が削除されることを確認

### 4. パスキーログイン

1. `http://localhost:8080/Plone/@@passkey-login` にアクセス
2. ユーザー名を入力（例: `admin`）
3. 「Login with Passkey」をクリック
4. ブラウザのパスキー認証プロンプトに従う

**期待される結果**:
- ✅ パスキー認証が成功
- ✅ ログインページから自動的にリダイレクト
- ✅ ログイン状態になる
- ✅ Cookie `__ac` が設定される

### 5. **重要**: セッション永続化のテスト

#### 5-1. ページ遷移テスト

1. ログイン後、別のページに移動（例: `http://localhost:8080/Plone/folder_contents`）
2. **期待される結果**: ログイン状態が継続している ✅

#### 5-2. ブラウザリロードテスト

1. ページをリロード（F5 または Cmd+R）
2. **期待される結果**: ログイン状態が継続している ✅

#### 5-3. ブラウザ再起動テスト（Optional）

1. ブラウザを完全に閉じる
2. ブラウザを再起動し、`http://localhost:8080/Plone` にアクセス
3. **期待される結果**: ログイン状態が継続している ✅
   - ※Cookieの有効期限: 7日間

---

## デバッグ用の確認方法

### ブラウザ開発者ツールでCookieを確認

#### Chrome / Edge

1. 開発者ツールを開く（F12）
2. 「Application」タブ → 「Cookies」 → `http://localhost:8080`
3. `__ac` Cookieを確認

**期待される状態**:
```
Name: __ac
Value: %EB%3C%... (長いURL-encodedの値)
Path: /
HttpOnly: ✓ (チェック)
Secure: (空白)
SameSite: (デフォルト)
```

### サーバーログの確認

#### ログインCookie設定時

```bash
tail -f var/log/instance.log | grep -E "AAL2|authentication|ticket"
```

**期待されるログ**:

```
INFO [c2.pas.aal2.plugin:824] Set AAL2 authentication cookie for user admin (IP: 127.0.0.1)
INFO [c2.pas.aal2.browser.views:328] Called AAL2Plugin.updateCredentials() for user admin
```

#### 2回目以降のアクセス時

```
DEBUG [c2.pas.aal2.plugin:141] Valid authentication ticket for user admin
DEBUG [c2.pas.aal2.plugin:162] Authenticated user admin via AAL2 ticket
```

---

## トラブルシューティング

### 問題1: ログイン後、ページ遷移すると認証が失われる

**確認**:
1. ブラウザ開発者ツールで `__ac` Cookieの存在を確認
2. サーバーログで `Set AAL2 authentication cookie` を確認

**原因の可能性**:
- Cookieが設定されていない → `updateCredentials()` が呼ばれていない
- Cookieが読み取れない → パス設定の問題

**解決策**:
```python
# views.py で確認
plugin.updateCredentials(self.request, self.request.response, user_id, '')
```

### 問題2: Cookie検証エラー

**ログ**:
```
DEBUG [c2.pas.aal2.plugin] Invalid authentication ticket
```

**原因の可能性**:
1. IPアドレスの変更（プロキシ経由など）
2. チケットのタイムアウト（7日間）
3. Plone再起動後のシークレット再生成

**解決策（一時的・開発環境のみ）**:
```python
# plugin.py の validateTicket() で IP チェックを無効化
result = validateTicket(
    secret=secret,
    ticket=ticket,
    ip="0.0.0.0",  # IPチェック無効化
    timeout=86400 * 7,
)
```

### 問題3: シークレットが保存されない

**確認**:
```bash
# ZMI でプラグインオブジェクトを確認
http://localhost:8080/Plone/acl_users/aal2_plugin/manage_main
```

**解決策**:
- トランザクションコミットを確認
- `self._p_changed = True` が設定されているか確認

### 問題4: "WebAuthn Not Supported" エラー

**原因**:
- IPアドレス経由でアクセスしている（例: `http://192.168.1.10:8080`）

**解決策**:
- `http://localhost:8080` または `http://127.0.0.1:8080` を使用
- または HTTPS を設定

---

## テストチェックリスト

### 基本機能

- [ ] パスキー登録が成功する
- [ ] 登録したパスキーがデータベースに保存される
- [ ] パスキーログインが成功する
- [ ] ログイン後、`__ac` Cookieが設定される

### セッション永続化

- [ ] ログイン後、別ページに遷移してもログイン状態が継続
- [ ] ページリロード後もログイン状態が継続
- [ ] ブラウザ再起動後もログイン状態が継続（7日間以内）

### セキュリティ

- [ ] Cookie が `HttpOnly` である
- [ ] 異なるIPアドレスからのアクセスで検証が失敗する（IPチェック有効時）
- [ ] タイムアウト後（7日後）にチケットが無効になる

### 監査ログ

- [ ] パスキー登録イベントがログに記録される
- [ ] パスキーログイン成功イベントがログに記録される
- [ ] ログイン失敗イベントがログに記録される

### エラーハンドリング

- [ ] 無効なパスキーでログインしようとすると適切なエラーが表示される
- [ ] 存在しないユーザーでログインしようとすると適切なエラーが表示される
- [ ] 改ざんされたCookieは検証エラーになる

---

## 性能テスト（Optional）

### Cookie検証のオーバーヘッド

**テスト方法**:
```bash
# Apache Bench で負荷テスト
ab -n 1000 -c 10 -C "__ac=<valid_cookie_value>" http://localhost:8080/Plone/
```

**期待される結果**:
- Cookie検証によるオーバーヘッドは最小限（< 10ms）

---

## まとめ

このガイドに従ってテストを実施し、すべての項目が ✅ になれば、パスキーログインとセッション永続化が正しく動作しています。

**問題が発生した場合**:
1. サーバーログを確認
2. ブラウザ開発者ツールでCookieを確認
3. 上記のトラブルシューティングを参照

---

**作成日**: 2025-11-10
**作成者**: Claude Code
