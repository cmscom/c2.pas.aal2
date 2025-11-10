# セッション永続化問題の分析

## 現状の問題

パスキーログインは成功するが、**ログイン状態が継続しない**。
Cookieは設定されるが、Ploneがそれを認証に使用できていない。

---

## 実装履歴

### フェーズ1: 初期実装
- **US1**: JavaScript externalization (完了✅)
- **US2**: Persistent audit logging (完了✅)
- パスキー登録: 動作確認済み✅
- パスキーログイン: 認証は成功するが、セッション継続せず❌

### フェーズ2: セッション問題への対応（試行錯誤）

#### 試行1: plone.sessionプラグインの利用
**問題**: `/temp_folder/session_data` が存在しない
```
WARNING [SessionDataManager:330] External session data container '/temp_folder/session_data' not found.
```

**試みた解決策**:
- sessionプラグインの`updateCredentials()`を呼び出し
- → Cookieは設定されるが認証されない

#### 試行2: __ac Cookieの直接設定（base64）
**実装**: `views.py`で直接Cookieを設定
```python
cookie_value = base64.b64encode(f"{user_id}:".encode('utf-8')).decode('ascii')
response.setCookie('__ac', quote(cookie_value), path='/')
```

**結果**: Cookieは設定されるが、Ploneが認証できない
- 理由: Ploneは暗号化されたチケット形式を期待しているが、単純なbase64では不十分

#### 試行3: plone.session.tktauth.createTicket()の使用
**実装**: `plugin.py`の`updateCredentials()`でチケット作成
```python
ticket = createTicket(secret, login, tokens=(), user_data='', ip=remote_addr)
response.setCookie('__ac', ticket, path='/')
```

**問題点**:
1. `createTicket()`の引数エラー → 修正
2. IPアドレスが空文字列でエラー → デフォルト値設定
3. **sessionプラグインのsecretが未設定** (`secret length: 0`)
   - 自動生成機能を追加
   - Cookieは設定されるが認証されない

#### 試行4: sessionプラグインへの委譲
**実装**: AAL2Pluginから`session.updateCredentials()`を呼び出し
```python
session_plugin.updateCredentials(request, response, login, new_password)
```

**結果**: `Delegated credential update to session plugin` と表示されるが、Cookieが設定されない
- 理由: sessionプラグインが`/temp_folder/session_data`を必要とする

---

## 技術的な問題の詳細

### 根本原因
Plone 6の`plone.session`プラグインは、セッションデータコンテナ（`/temp_folder/session_data`）に依存している。このコンテナが存在しないため、セッション管理が機能していない。

### 現在のログ出力
```
2025-11-10 18:34:01,202 INFO [c2.pas.aal2.plugin:551] Successfully authenticated user terada with passkey
2025-11-10 18:34:01,203 INFO [c2.pas.aal2.plugin:756] Delegated credential update to session plugin for user terada
2025-11-10 18:34:01,203 INFO [c2.pas.aal2.browser.views:328] Called AAL2Plugin.updateCredentials() for user terada
2025-11-10 18:34:01,203 INFO [c2.pas.aal2.browser.views:337] Set security context for user terada
2025-11-10 18:34:04,820 WARNING [SessionDataManager:330] External session data container '/temp_folder/session_data' not found.
```

### 確認された事実
✅ パスキー登録: 動作する
✅ パスキー認証（WebAuthn検証）: 成功する
✅ AAL2タイムスタンプ設定: 成功する
✅ 監査ログ記録: 成功する
✅ `newSecurityManager()`: 現在のリクエストでは認証される
❌ Cookie永続化: 次のリクエストで認証されない

### Cookieの状態
- **設定されるCookie**: `__ac`
- **値の例**: `%1B%CB%5E%28%7C%B8%A1%18%82%BD~%E7X%83%FCs%08%14%1A%98%94%01%83%8B%DE%E9%B8%CD%87%B3%17N6911aeedterada%21`
- **問題**: Ploneが次のリクエストでこのCookieを認証に使用できていない

---

## 考えられる原因

### 1. セッションデータコンテナの欠如
**最も可能性が高い**

`/temp_folder/session_data`が存在しないため、`plone.session`プラグインが正常に動作していない。

**解決策の候補**:
- A) ZMIでセッションデータコンテナを作成
- B) AAL2独自の認証Cookieメカニズムを実装

### 2. プラグインの優先順位
sessionプラグインよりAAL2Pluginが先に処理され、Cookieの読み取りを妨げている可能性。

**確認済み**: AAL2Pluginの`extractCredentials()`は`__passkey_auth_attempt`がある場合のみ動作するため、通常のCookie認証には干渉しない。

### 3. Cookieのドメイン/パス設定
Cookieが正しいドメイン・パスで設定されていない可能性。

**要確認**: ブラウザ開発者ツールでCookieの詳細を確認する必要がある。

### 4. CSRF保護の影響
`alsoProvides(self.request, IDisableCSRFProtection)`の影響で、セッション処理に問題がある可能性。

**確認済み**: ログインAPIは正常に動作しているため、CSRF保護の無効化自体は問題ない。

---

## 未確認・未試行の項目

### 1. ZMIでの手動設定
`/temp_folder/session_data`を手動で作成する方法を試していない。

**手順**:
1. `http://localhost:8080/temp_folder/manage_main`
2. "Session Data Container"を追加
3. ID: `session_data`

### 2. session_data_managerの設定
`http://localhost:8080/manage/session_data_manager`でパス設定が正しいか確認していない。

### 3. Cookieの詳細確認
ブラウザ開発者ツールで以下を確認していない:
- Cookie Domain
- Cookie Path
- Cookie Secure flag
- Cookie HttpOnly flag
- Cookie SameSite attribute

### 4. プラグイン優先順位の確認
PASプラグインの実行順序を確認していない。

**確認方法**:
```
http://localhost:8080/Plone/acl_users/plugins/manage_plugins
```

### 5. AAL2Plugin独自のCookie実装
AAL2Pluginで独自の認証Cookieを設定・検証する実装を試していない。

**メリット**:
- temp_folderに依存しない
- 完全にコントロール可能
- シンプル

**デメリット**:
- Plone標準から外れる
- 自前でセキュリティを確保する必要

---

## 推奨される次のステップ

### 優先度1: 手動でセッションデータコンテナを作成
最もシンプルで、Plone標準の動作を維持できる方法。

**手順**:
1. ZMIで`/temp_folder/session_data`を作成
2. `session_data_manager`のパス設定を確認
3. Plone再起動
4. パスキーログインをテスト

### 優先度2: Cookieの詳細確認
ブラウザ開発者ツールで`__ac` Cookieの設定を確認。

### 優先度3: AAL2独自のCookie実装
もし優先度1・2で解決しない場合、独自実装を検討。

---

## 設計上の課題（リファクタリング必要）

### Cookie設定ロジックの配置
現在、`browser/views.py`でCookie設定を行っているが、これはPASプラグインの責務であるべき。

**リファクタリング計画**: `/workspace/REFACTORING_TODO.md`に記載済み

---

## 関連ファイル

### 主要実装ファイル
- `/workspace/src/c2/pas/aal2/plugin.py` - AAL2Plugin本体
- `/workspace/src/c2/pas/aal2/browser/views.py` - ログインビュー
- `/workspace/src/c2/pas/aal2/setuphandlers.py` - プラグインインストール

### ドキュメント
- `/workspace/REFACTORING_TODO.md` - 将来のリファクタリング計画

### ログの確認
```bash
# Ploneログを確認
tail -f var/log/instance.log | grep -E "(session|cookie|authentication|terada)"
```

---

## まとめ

**現状**: パスキー認証は技術的に成功しているが、Ploneの標準セッション管理に統合できていない。

**根本原因**: `/temp_folder/session_data`の欠如により、`plone.session`プラグインが機能していない。

**次のアクション**: まずはZMIでセッションデータコンテナを手動作成し、Plone標準の方法で動作させることを試みる。

---

## ✅ 解決済み（2025-11-10 更新）

**解決策**: AAL2独自のCookie認証機構を実装

`plone.session` の `/temp_folder/session_data` 依存問題を回避するため、AAL2Plugin独自の認証Cookie管理を実装しました。

**実装内容**:
1. `plone.session.tktauth` を使用した署名付きチケットの生成・検証
2. AAL2Pluginに `ICredentialsUpdatePlugin` と `IExtractionPlugin` を完全実装
3. ZODBに永続化されるランダムシークレットによるチケット署名

**詳細**: `/workspace/COOKIE_SESSION_SOLUTION.md` を参照

**変更ファイル**:
- `/workspace/src/c2/pas/aal2/plugin.py` - Cookie認証機構を実装

---

**最終更新**: 2025-11-10
**記録者**: Claude Code
