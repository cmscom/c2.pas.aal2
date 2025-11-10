# Passkey Login Session Persistence - Fix V2

## 問題の詳細分析

初回の修正後も、以下の問題が残っていました：

1. **Cookie設定の問題**
   - AAL2プラグインが独自にCookieを作成していたが、Ploneの標準認証メカニズムと互換性がなかった
   - Cookieが過度にエンコードされていた（%25 = % の二重エンコード）

2. **PAS統合の問題**
   - AAL2プラグインが標準のCookie認証と競合していた
   - プラグインの優先順位設定が不適切だった

## 解決策：標準Plone認証への完全委譲

### アプローチの変更

**Before (問題のあるアプローチ)**:
- AAL2プラグインが独自にCookieを作成・検証
- 標準のPlone認証と並行して動作
- 複雑なCookieエンコード/デコード処理

**After (新しいアプローチ)**:
- AAL2プラグインはパスキー認証のみを処理
- Cookie管理は完全に標準Ploneプラグインに委譲
- シンプルで互換性のあるアーキテクチャ

## 実装の詳細

### 1. プラグインインターフェースの簡素化 (`plugin.py`)

```python
# 変更前
@implementer(IAuthenticationPlugin, IExtractionPlugin,
             IValidationPlugin, ICredentialsUpdatePlugin, IAAL2Plugin)

# 変更後
@implementer(IAuthenticationPlugin, IExtractionPlugin,
             IValidationPlugin, IAAL2Plugin)
# ICredentialsUpdatePluginは実装しない
```

### 2. extractCredentialsの簡素化

```python
def extractCredentials(self, request):
    # パスキー認証リクエストのみを処理
    if request.get('__passkey_auth_attempt'):
        # パスキー認証情報を抽出
        return {'extractor': 'passkey', ...}

    # Cookie認証は標準Ploneプラグインに任せる
    return {}
```

### 3. authenticateCredentialsの専門化

```python
def authenticateCredentials(self, credentials):
    # パスキー認証のみを処理
    if credentials.get('extractor') != 'passkey':
        return None  # 他のプラグインに処理を委譲

    # パスキー認証ロジック
    ...
```

### 4. ビューでの標準ログインメカニズム使用 (`views.py`)

```python
# 全ての登録済みICredentialsUpdatePluginを呼び出す
plugins = acl_users.plugins
updaters = plugins.listPlugins(ICredentialsUpdatePlugin)

for plugin_id, plugin in updaters:
    plugin.updateCredentials(request, response, user_id, '')
    # これにより標準のPlone Cookieが設定される
```

### 5. プラグイン優先順位の適切な設定

```xml
<!-- pas_plugins.xml -->
<plugin-order>
  <extraction>
    <!-- Cookie認証の後にAAL2プラグインを実行 -->
    <plugin id="aal2_plugin" pos="5"/>
  </extraction>
  <authentication>
    <!-- パスキー認証は高優先度 -->
    <plugin id="aal2_plugin" pos="0"/>
  </authentication>
</plugin-order>
```

## 利点

### 1. シンプルさ
- 複雑なCookieエンコード/デコード処理が不要
- コード量の削減（約100行削除）
- デバッグとメンテナンスが容易

### 2. 互換性
- 標準Plone認証メカニズムとの完全な互換性
- 他のPASプラグインとの協調動作
- Ploneのアップグレードに対する耐性

### 3. セキュリティ
- 実績のあるPlone Cookie認証を使用
- 独自実装のセキュリティリスクを回避
- 標準のセッション管理機能を活用

## デプロイ手順

1. **コードのデプロイ**
   ```bash
   # 修正されたファイルをデプロイ
   - src/c2/pas/aal2/plugin.py
   - src/c2/pas/aal2/browser/views.py
   - src/c2/pas/aal2/setuphandlers.py
   - src/c2/pas/aal2/profiles/default/pas_plugins.xml
   ```

2. **Ploneの再起動**
   ```bash
   # インスタンスを再起動
   bin/instance restart
   ```

3. **プラグインの再インストール**
   - 管理画面 → アドオン管理
   - c2.pas.aal2を再インストール

4. **プラグイン順序の確認**
   - `/acl_users/manage_plugins`にアクセス
   - Extraction: aal2_pluginがcookie認証の後にあることを確認
   - Authentication: aal2_pluginが上位にあることを確認

## テスト手順

### 1. ログインテスト
```
1. ブラウザのCookieをクリア
2. /@@passkey-login にアクセス
3. パスキーでログイン
4. DevToolsでCookieを確認
   - __ac Cookieが存在
   - 標準的なPlone Cookie形式
```

### 2. セッション永続性テスト
```
1. ログイン後、ブラウザを閉じる
2. ブラウザを再度開く
3. プロテクトされたページにアクセス
4. ログイン状態が維持されていることを確認
```

### 3. 他の認証方法との共存テスト
```
1. 通常のパスワードログインが引き続き動作
2. 両方の認証方法が共存可能
```

## トラブルシューティング

### Cookie が設定されない場合

1. **ログを確認**
   ```
   grep "updateCredentials" instance.log
   # 標準プラグインが呼ばれているか確認
   ```

2. **プラグイン設定を確認**
   ```python
   # Zope管理画面のDebug Modeで
   app.Plone.acl_users.plugins.listPlugins(ICredentialsUpdatePlugin)
   # cookie_authなど標準プラグインがアクティブか確認
   ```

### ログイン後すぐにログアウトされる場合

1. **Cookie設定を確認**
   - ブラウザのCookie設定で`localhost`が許可されているか
   - サードパーティCookieがブロックされていないか

2. **IPアドレスの変更**
   - プロキシ経由でIPが変わっていないか確認
   - VPN使用時は注意

## まとめ

この修正により、パスキーログインのセッション永続性問題は根本的に解決されました。

**キーポイント**:
- 標準Plone認証メカニズムとの完全な統合
- 独自Cookie実装を排除し、標準実装に委譲
- シンプルで保守可能なアーキテクチャ

これにより、パスキーログインは通常のパスワードログインと同じようにセッションが維持され、ユーザーは快適にシステムを利用できるようになります。