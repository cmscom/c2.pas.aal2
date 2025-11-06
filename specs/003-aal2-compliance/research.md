# Research: AAL2 Compliance Implementation

**Feature**: 003-aal2-compliance
**Date**: 2025-11-06
**Status**: Complete

## Overview

このドキュメントは、AAL2コンプライアンス機能の実装に必要な技術調査の結果をまとめたものです。既存のc2.pas.aal2パッケージ（パスキー認証実装）を拡張し、AAL2レベルの認証保証を実現します。

## Research Questions & Decisions

### 1. Plone.PASでのカスタムパーミッション定義方法

**Decision**: CMFCoreのパーミッション登録システムを使用

**Rationale**:
- PloneはCMFCore（Content Management Framework Core）のパーミッションシステムを使用
- `Products.CMFCore.permissions`モジュールで標準パーミッションを定義
- カスタムパーミッションは`configure.zcml`で登録し、文字列定数として定義
- 例: `setDefaultRoles('Require AAL2 Authentication', ('Manager',))`で初期ロールを設定可能

**Alternatives considered**:
- Zopeの低レベルPermission機能を直接使用 → CMFCoreの抽象化を利用する方が保守性が高い
- 動的パーミッション生成 → 静的定義の方がデバッグとパフォーマンスの面で優れる

**Implementation approach**:
```python
# permissions.py
from Products.CMFCore.permissions import setDefaultRoles

RequireAAL2Authentication = 'Require AAL2 Authentication'
setDefaultRoles(RequireAAL2Authentication, ('Manager',))
```

**References**:
- CMFCore Permission Documentation
- Plone 5.2 Security Framework

---

### 2. Plone.PASでのカスタムロール定義方法

**Decision**: GenericSetupのrolemap.xmlを使用してロールを定義

**Rationale**:
- Ploneのロール管理はGenericSetup（設定管理システム）で行う
- `profiles/default/rolemap.xml`でロールとパーミッションのマッピングを定義
- ロールは`portal_role_manager`ツールで管理され、ZODBに永続化される
- インストール時に自動的にロールが登録される

**Alternatives considered**:
- プログラマティックなロール作成（`portal_role_manager.addRole()`） → インストール時の一貫性が低い
- ZCMLでのロール登録 → GenericSetupの方がPloneの標準的なアプローチ

**Implementation approach**:
```xml
<!-- profiles/default/rolemap.xml -->
<rolemap>
  <roles>
    <role name="AAL2 Required User"/>
  </roles>
  <permissions>
    <permission name="Require AAL2 Authentication" acquired="False">
      <role name="Manager"/>
      <role name="AAL2 Required User"/>
    </permission>
  </permissions>
</rolemap>
```

**References**:
- GenericSetup Documentation
- Plone Role Management Best Practices

---

### 3. ZODBへのAAL2タイムスタンプ保存方法

**Decision**: ユーザーオブジェクトのアノテーション（`IAnnotations`）を使用

**Rationale**:
- Ploneのユーザーオブジェクトは通常、カスタム属性の直接追加をサポートしていない
- `zope.annotation.interfaces.IAnnotations`を使用すれば、任意のオブジェクトにメタデータを保存可能
- アノテーションはZODBに自動的に永続化される
- キー形式: `c2.pas.aal2.timestamp`で名前空間衝突を回避

**Alternatives considered**:
- ユーザープロパティ（`user.setProperty()`） → タイムスタンプのような動的データには不適切
- セッションストレージのみ → サーバー再起動やセッションタイムアウトでデータ消失
- 外部データベース（PostgreSQLなど） → オーバーエンジニアリング、Ploneの標準から逸脱

**Implementation approach**:
```python
from zope.annotation.interfaces import IAnnotations
from datetime import datetime

ANNOTATION_KEY = 'c2.pas.aal2.aal2_timestamp'

def set_aal2_timestamp(user):
    """Set AAL2 authentication timestamp for user."""
    annotations = IAnnotations(user)
    annotations[ANNOTATION_KEY] = datetime.utcnow().isoformat()

def get_aal2_timestamp(user):
    """Get AAL2 authentication timestamp for user."""
    annotations = IAnnotations(user)
    timestamp_str = annotations.get(ANNOTATION_KEY)
    if timestamp_str:
        return datetime.fromisoformat(timestamp_str)
    return None
```

**References**:
- Zope Annotations Documentation
- Plone User Object Architecture

---

### 4. コンテンツレベルでのAAL2ポリシー設定方法

**Decision**: コンテンツオブジェクトのアノテーションを使用し、Ploneのワークフロー/セキュリティUIと統合

**Rationale**:
- コンテンツオブジェクトもアノテーションをサポート
- `c2.pas.aal2.require_aal2`というブール値フラグを保存
- Ploneの既存のセキュリティタブに「AAL2保護を要求」チェックボックスを追加可能
- `@@sharing`ビューを拡張するか、カスタムコントロールパネルを提供

**Alternatives considered**:
- ワークフロー状態に基づく制御 → 柔軟性が低く、既存ワークフローとの統合が複雑
- マーカーインターフェース → チェックは高速だが、動的な設定変更が困難
- ポータルカタログのメタデータ → インデックス化は不要、シンプルなアノテーションで十分

**Implementation approach**:
```python
from zope.annotation.interfaces import IAnnotations

AAL2_POLICY_KEY = 'c2.pas.aal2.require_aal2'

def set_aal2_required(context, required=True):
    """Mark content as requiring AAL2 authentication."""
    annotations = IAnnotations(context)
    annotations[AAL2_POLICY_KEY] = required

def is_aal2_required(context):
    """Check if content requires AAL2 authentication."""
    annotations = IAnnotations(context)
    return annotations.get(AAL2_POLICY_KEY, False)
```

**UI Integration**:
- Browser view: `@@aal2-settings` で管理画面を提供
- Viewlet: セキュリティタブに統合

**References**:
- Plone Content Annotations
- Security Tab Extension Patterns

---

### 5. AAL2チェックをPloneのリクエストサイクルに統合する方法

**Decision**: PASプラグインの`IValidationPlugin`と`IAuthenticationPlugin`を拡張し、トラバーサル後に検証

**Rationale**:
- PloneのPublisherは、リクエスト処理時にPASプラグインチェーンを実行
- トラバーサル（URLからオブジェクト解決）後、ビューのレンダリング前にセキュリティチェックが実行される
- `IValidationPlugin`インターフェースを実装し、`validate`メソッドでAAL2要件をチェック
- AAL2要件が満たされていない場合、`Unauthorized`例外を発生させ、カスタム例外ビューでパスキーチャレンジを表示

**Alternatives considered**:
- ビューレベルのデコレータ → すべてのビューに手動適用が必要、保守性が低い
- Middlewareレベルの介入 → Ploneの標準パターンから逸脱、デバッグが困難
- イベントサブスクライバー（`IObjectWillBeAccessedEvent`） → タイミングが不適切、例外処理が複雑

**Implementation approach**:
```python
from Products.PluggableAuthService.interfaces.plugins import IValidationPlugin
from zope.interface import implementer

@implementer(IValidationPlugin)
class AAL2Plugin(BasePlugin):
    def validate(self, user, request):
        """Validate AAL2 requirements for current request."""
        # Get published object from request
        published = request.get('PUBLISHED')
        if published is None:
            return True  # No object to protect

        # Check if object requires AAL2
        context = getattr(published, 'context', None)
        if context and is_aal2_required(context):
            # Check user's AAL2 status
            if not self.check_aal2_valid(user):
                # Raise Unauthorized with custom marker
                raise Unauthorized('AAL2 authentication required')

        return True
```

**Exception Handling**:
- カスタム例外ビュー: `@@aal2-challenge-view`
- HTTPステータス: 401 Unauthorized
- レスポンス: パスキーチャレンジUI

**References**:
- PAS IValidationPlugin Interface
- Plone Exception Views
- Publisher Architecture

---

### 6. 15分タイムウィンドウの精度とタイムゾーン処理

**Decision**: UTC時刻を使用し、サーバー側で一元管理

**Rationale**:
- すべてのタイムスタンプをUTC（`datetime.utcnow()`）で記録
- タイムゾーン変換はクライアント側でのみ実行（表示目的）
- 15分 = 900秒、精度は±5秒（仕様要件）
- Pythonの`datetime`モジュールはマイクロ秒精度をサポート、十分な精度

**Alternatives considered**:
- タイムゾーン対応（`datetime.now(timezone.utc)`） → Python 3.11+では推奨だが、後方互換性のため`utcnow()`を使用
- Unixタイムスタンプ（秒） → 人間が読める形式でない、デバッグが困難
- 相対時間（セッション開始からの経過時間） → サーバー再起動で情報消失

**Implementation approach**:
```python
from datetime import datetime, timedelta

AAL2_TIMEOUT_SECONDS = 900  # 15 minutes

def is_aal2_valid(timestamp):
    """Check if AAL2 authentication is still valid."""
    if timestamp is None:
        return False

    now = datetime.utcnow()
    elapsed = (now - timestamp).total_seconds()
    return elapsed <= AAL2_TIMEOUT_SECONDS

def get_aal2_expiry(timestamp):
    """Get AAL2 expiry time."""
    if timestamp is None:
        return None
    return timestamp + timedelta(seconds=AAL2_TIMEOUT_SECONDS)
```

**Edge Case Handling**:
- システム時刻変更: タイムスタンプが未来の場合、無効とみなす
- クロックスキュー: サーバー間のNTP同期が前提（インフラ要件）

**References**:
- Python datetime Best Practices
- NIST AAL2 Time Requirements

---

### 7. パスキーチャレンジUIの実装方法

**Decision**: Plone ZPTテンプレート + WebAuthn JavaScript APIの組み合わせ

**Rationale**:
- PloneのZPT（Zope Page Templates）でHTMLをレンダリング
- 既存のWebAuthn実装（`utils/webauthn.py`）を再利用
- JavaScript: ブラウザの`navigator.credentials.get()`を呼び出し
- サーバー側: `generateAuthenticationOptions()`でチャレンジ生成、`verifyAuthenticationResponse()`で検証

**Alternatives considered**:
- React/Vueなどのフロントエンドフレームワーク → Ploneの標準アプローチでない、オーバーエンジニアリング
- iframeベースのチャレンジ → セキュリティリスク、UX悪化
- モーダルダイアログ → フルページリダイレクトの方がシンプル

**Implementation approach**:
```xml
<!-- browser/aal2_challenge.pt -->
<html metal:use-macro="context/main_template/macros/master">
  <metal:content fill-slot="content">
    <h1>追加認証が必要です</h1>
    <p>このリソースにアクセスするには、パスキーで再認証してください。</p>
    <button id="aal2-authenticate-btn">パスキーで認証</button>
    <script tal:content="structure view/webauthn_script"></script>
  </metal:content>
</html>
```

```python
# browser/views.py
class AAL2ChallengeView(BrowserView):
    def __call__(self):
        # Generate authentication options
        plugin = self.get_aal2_plugin()
        options = plugin.generateAuthenticationOptions(
            self.request,
            username=self.get_current_user_id()
        )
        # Store original URL for redirect after success
        self.request.SESSION['aal2_redirect_url'] = self.request.get('came_from')
        return self.index()

    def webauthn_script(self):
        # Return JavaScript for WebAuthn API call
        return """
        document.getElementById('aal2-authenticate-btn').addEventListener('click', async () => {
            // Call WebAuthn API
            const options = %s;
            const credential = await navigator.credentials.get(options);
            // POST to verification endpoint
            fetch('@@aal2-verify', {
                method: 'POST',
                body: JSON.stringify(credential)
            });
        });
        """ % self.authentication_options_json
```

**References**:
- WebAuthn API Documentation
- Plone ZPT Templates
- Browser API: navigator.credentials

---

### 8. パフォーマンス最適化戦略

**Decision**: メモリキャッシュとアノテーション遅延ロードの組み合わせ

**Rationale**:
- AAL2チェックは高頻度（すべてのリクエスト）で実行される可能性がある
- ユーザーのAAL2タイムスタンプをリクエストスコープでキャッシュ
- コンテンツのAAL2ポリシーは変更頻度が低いため、RAM Cacheを使用
- 目標: AAL2チェック <50ms、タイムスタンプ検証 <10ms

**Alternatives considered**:
- Memcached/Redis外部キャッシュ → オーバーエンジニアリング、依存関係増加
- ZODBキャッシュのみ → 毎回ディスクI/O、パフォーマンス目標未達
- キャッシュなし → 100,000ユーザーでスケーラビリティ問題

**Implementation approach**:
```python
from plone.memoize import ram
from plone.memoize.volatile import cache

# Request-scoped cache for user AAL2 status
def _aal2_status_cache_key(method, user_id):
    return (user_id, time.time() // 60)  # Cache for 1 minute

@ram.cache(_aal2_status_cache_key)
def get_user_aal2_status(user_id):
    """Get AAL2 status with caching."""
    user = get_user_object(user_id)
    timestamp = get_aal2_timestamp(user)
    return is_aal2_valid(timestamp)

# Content-level AAL2 policy cache
def _content_policy_cache_key(method, context_path):
    return context_path

@ram.cache(_content_policy_cache_key)
def get_content_aal2_policy(context_path):
    """Get content AAL2 policy with caching."""
    context = get_object_by_path(context_path)
    return is_aal2_required(context)
```

**Cache Invalidation**:
- AAL2タイムスタンプ更新時: リクエストスコープのため自動無効化
- コンテンツポリシー変更時: `ram.cache.invalidate()`を呼び出し

**References**:
- plone.memoize Documentation
- Plone Caching Best Practices
- RAM Cache Strategies

---

## Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.11+ | 実装言語 |
| Framework | Plone | 5.2+ | CMS基盤 |
| Auth Framework | Plone.PAS | Core | 認証プラグインシステム |
| WebAuthn Library | webauthn | 2.7.0 | パスキー検証 |
| Database | ZODB | Core | ユーザーデータ永続化 |
| Time Handling | datetime | stdlib | タイムスタンプ管理 |
| Caching | plone.memoize | Core | パフォーマンス最適化 |
| Testing | pytest | Latest | ユニット・統合テスト |
| UI Templates | ZPT | Core | HTMLレンダリング |

---

## Implementation Risks & Mitigation

### Risk 1: ZODB書き込み競合

**Risk**: 複数リクエストが同時にAAL2タイムスタンプを更新

**Mitigation**:
- ZODBのトランザクション分離レベルを活用
- `ConflictError`をキャッチして自動リトライ（ZODBの標準動作）
- タイムスタンプ更新は最終書き込みが優先（最新の認証が有効）

### Risk 2: セッション管理の複雑さ

**Risk**: 複数タブ・ウィンドウでのAAL2状態の同期

**Mitigation**:
- AAL2タイムスタンプをユーザーオブジェクト（ZODB）に保存、セッションではない
- すべてのタブ・ウィンドウで共有される
- リロードで最新状態を取得

### Risk 3: パフォーマンス劣化

**Risk**: すべてのリクエストでAAL2チェックが実行される

**Mitigation**:
- キャッシング戦略（上記参照）
- AAL2保護コンテンツのみチェック（条件分岐）
- 早期リターン: AAL2不要の場合は即座に終了

---

## Next Steps

1. **Phase 1 - Design**:
   - data-model.md: エンティティとリレーションシップの詳細設計
   - contracts/: API契約（内部API）の定義
   - quickstart.md: 開発者向けクイックスタートガイド

2. **Phase 2 - Implementation**:
   - tasks.md生成（`/speckit.tasks`コマンド）
   - TDD: テスト→実装→リファクタリングサイクル
   - 段階的統合: permissions → roles → session → policy → UI

---

**Research Status**: ✅ Complete
**Review Date**: 2025-11-06
**Approved By**: Auto-generated by `/speckit.plan`
