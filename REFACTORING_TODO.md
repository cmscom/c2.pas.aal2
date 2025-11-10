# Refactoring TODO

このファイルは、将来実施すべきリファクタリングタスクを記録しています。

## 優先度: 高

### 1. Cookie設定ロジックをAAL2Pluginへ移動

**現状の問題**:
- `browser/views.py`の`PasskeyLoginVerifyView`で`__ac` Cookieを直接設定している
- これは関心の分離に反し、PASアーキテクチャの設計思想に合わない
- ビューは HTTP リクエスト/レスポンスの処理に専念すべき
- 認証状態管理（Cookie設定）はPASプラグインの責務

**リファクタリング手順**:

1. **AAL2Pluginに`ICredentialsUpdatePlugin`を追加**
   ```python
   # plugin.py
   from Products.PluggableAuthService.interfaces.plugins import ICredentialsUpdatePlugin
   
   @implementer(IAAL2Plugin, IAuthenticationPlugin, IExtractionPlugin, 
                IValidationPlugin, ICredentialsUpdatePlugin)  # ← 追加
   class AAL2Plugin(BasePlugin):
       ...
   ```

2. **`updateCredentials()`メソッドを実装**
   ```python
   def updateCredentials(self, request, response, login, new_password):
       """Set authentication cookie for passkey login."""
       import base64
       from urllib.parse import quote
       
       # Create __ac cookie: base64(username:password)
       cookie_value = base64.b64encode(f"{login}:".encode('utf-8')).decode('ascii')
       
       # Set cookie
       response.setCookie(
           '__ac',
           quote(cookie_value),
           path='/',
       )
       logger.info(f"Set __ac cookie for user {login}")
   ```

3. **プラグインを`ICredentialsUpdatePlugin`として有効化**
   - `setuphandlers.py`の`install_pas_plugin()`で`ICredentialsUpdatePlugin`を追加

4. **ビューからCookie設定コードを削除**
   - `browser/views.py:311-349`のCookie設定コードを削除
   - 代わりにプラグインの`updateCredentials()`を呼び出す:
   ```python
   # Get AAL2 plugin
   plugin = acl_users.get('aal2_plugin')
   if plugin and hasattr(plugin, 'updateCredentials'):
       plugin.updateCredentials(self.request, self.request.response, user_id, '')
   ```

**メリット**:
- ✅ 関心の分離（ビューはHTTP、プラグインは認証）
- ✅ 再利用性向上（他の認証フローでも使える）
- ✅ PASアーキテクチャに準拠
- ✅ テストが容易
- ✅ 保守性向上

**影響範囲**:
- `src/c2/pas/aal2/plugin.py` - `ICredentialsUpdatePlugin`実装追加
- `src/c2/pas/aal2/browser/views.py` - Cookie設定コード削除
- `src/c2/pas/aal2/setuphandlers.py` - プラグイン有効化設定追加
- `src/c2/pas/aal2/tests/` - 新しいテストケース追加

**関連ファイル**:
- `/workspace/src/c2/pas/aal2/browser/views.py:311-349`
- `/workspace/src/c2/pas/aal2/plugin.py`
- `/workspace/src/c2/pas/aal2/setuphandlers.py`

---

## その他の改善提案

### 2. セッションストレージの改善
現在、`plone.session`が`/temp_folder/session_data`を必要とするため、直接`__ac` Cookieを設定している。
将来的には、適切なセッションストレージ（Redis、memcached等）の利用を検討。

### 3. テストカバレッジの向上
- エンドツーエンドテスト（ブラウザテスト）の追加
- PASプラグイン統合テストの追加
- 監査ログのテスト充実

---

**最終更新**: 2025-11-10
**記録者**: Claude Code
