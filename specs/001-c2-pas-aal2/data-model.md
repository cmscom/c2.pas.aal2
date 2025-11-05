# Data Model: c2.pas.aal2パッケージ雛形

**Date**: 2025-11-05
**Feature**: c2.pas.aal2 - Plone PAS AAL2認証プラグイン雛形

## 概要

このパッケージは雛形であり、実際のデータ永続化を行いません。ここで定義するのは、PASプラグインとしての構造的なエンティティ（クラス、インターフェース）のみです。

## エンティティ

### 1. AAL2Plugin (プラグインクラス)

**目的**: Plone.PASプラグインとして登録されるスタブクラス

**属性**:
| 属性名 | 型 | 説明 | 必須 |
|--------|-----|------|------|
| `id` | str | プラグインID（例: "c2_pas_aal2_plugin"） | ✓ |
| `title` | str | プラグイン表示名（例: "C2 PAS AAL2 Authentication Plugin"） | ✓ |
| `meta_type` | str | Zopeメタタイプ（例: "C2 PAS AAL2 Plugin"） | ✓ |

**実装インターフェース**:
- `Products.PluggableAuthService.interfaces.IAuthenticationPlugin`
- `Products.PluggableAuthService.interfaces.IExtractionPlugin`

**スタブメソッド**:
| メソッド名 | 引数 | 戻り値 | 説明 |
|-----------|------|--------|------|
| `authenticateCredentials(credentials)` | dict | dict or None | 認証資格情報を検証（スタブでは`None`を返す） |
| `extractCredentials(request)` | HTTPRequest | dict | リクエストから資格情報を抽出（スタブでは空dictを返す） |

**ライフサイクル**:
1. **生成**: ZCMLまたはGenericSetupプロファイルによってPASに登録
2. **有効化**: Plone管理画面でプラグインを有効化
3. **無効化/削除**: 管理画面で無効化・削除可能

**バリデーション**:
- `id`は空文字列不可
- `title`は空文字列不可
- インターフェースメソッドは呼び出し可能でなければならない

### 2. IAAL2Plugin (インターフェース)

**目的**: AAL2プラグインが実装すべきインターフェースの定義（将来の拡張用）

**メソッド仕様**:
| メソッド名 | 引数 | 戻り値 | 説明 |
|-----------|------|--------|------|
| `get_aal_level(user_id)` | str | int | ユーザーの現在のAALレベルを取得（将来実装、スタブでは1を返す） |
| `require_aal2(user_id, context)` | str, object | bool | AAL2が必要かどうかを判定（将来実装、スタブでは`False`を返す） |

**説明**:
このインターフェースは将来の実装のためのプレースホルダーです。雛形段階では、このインターフェースを定義するのみで、実際の実装は含みません。

### 3. PackageStructure (概念的エンティティ)

**目的**: 2ドット形式のパッケージ構造の定義

**構造**:
```
c2/                      # 名前空間パッケージ（__init__.py含む）
└── pas/                 # 名前空間パッケージ（__init__.py含む）
    └── aal2/            # 実際のパッケージコード
        ├── __init__.py  # パッケージエクスポート
        ├── plugin.py    # AAL2Pluginクラス
        ├── interfaces.py  # IAAL2Pluginインターフェース
        └── configure.zcml  # ZCML設定
```

**関係性**:
- `c2`は`pas`を含む
- `pas`は`aal2`を含む
- `aal2`は`AAL2Plugin`クラスと`IAAL2Plugin`インターフェースを含む

## エンティティ関係図

```
┌─────────────────────────────────────┐
│ Products.PluggableAuthService.      │
│ interfaces.IAuthenticationPlugin    │
│ (Plone PAS提供)                     │
└──────────────┬──────────────────────┘
               │ implements
               │
┌──────────────▼──────────────────────┐
│ AAL2Plugin                          │
│ ----------------------------------- │
│ + id: str                           │
│ + title: str                        │
│ + meta_type: str                    │
│ ----------------------------------- │
│ + authenticateCredentials()         │
│ + extractCredentials()              │
│ + get_aal_level() (future)          │
│ + require_aal2() (future)           │
└─────────────────────────────────────┘
               │
               │ defined by
               │
┌──────────────▼──────────────────────┐
│ IAAL2Plugin                         │
│ (Zope Interface)                    │
│ ----------------------------------- │
│ + get_aal_level()                   │
│ + require_aal2()                    │
└─────────────────────────────────────┘
```

## データフロー

雛形段階ではデータフローは最小限です：

1. **プラグイン登録フロー**:
   ```
   ZCML読み込み → PASにプラグイン登録 → 管理画面に表示
   ```

2. **認証フロー（スタブ）**:
   ```
   HTTPリクエスト → extractCredentials() [スタブ、空dict返却]
   → authenticateCredentials() [スタブ、None返却]
   → 既存の認証フローに影響なし
   ```

3. **テストフロー**:
   ```
   pytest実行 → パッケージインポート → クラス存在確認
   → メソッド呼び出し可能性確認 → 成功
   ```

## 状態遷移

### AAL2Plugin状態

```
[未登録] --ZCML読み込み--> [登録済み]

[登録済み] --管理画面で有効化--> [有効]

[有効] --管理画面で無効化--> [無効]

[無効] --管理画面で削除--> [削除済み]
```

**状態説明**:
- **未登録**: パッケージインストール前、またはZCML未読み込み
- **登録済み**: PASにプラグインとして登録されているが、まだ有効化されていない
- **有効**: プラグインが有効化され、認証フローに組み込まれている（スタブなので実際には何もしない）
- **無効**: 登録されているが無効化されている
- **削除済み**: PASから削除された

## バリデーションルール

### AAL2Pluginクラス

| ルール | 検証内容 | エラー時の動作 |
|--------|---------|---------------|
| ID必須 | `id`が非空文字列 | インスタンス生成失敗 |
| タイトル必須 | `title`が非空文字列 | インスタンス生成失敗 |
| インターフェース実装 | `IAuthenticationPlugin`と`IExtractionPlugin`を実装 | ZCML登録時エラー |
| メソッド存在 | `authenticateCredentials`と`extractCredentials`が呼び出し可能 | テスト失敗 |

### パッケージ構造

| ルール | 検証内容 | エラー時の動作 |
|--------|---------|---------------|
| 名前空間パッケージ | 各レベルに`__init__.py`が存在 | インポートエラー |
| ZCML有効性 | `configure.zcml`が構文的に正しい | Plone起動エラー |
| テスト成功 | 3つの基本テストがすべてパス | CI/CDビルド失敗 |

## 将来の拡張

雛形を基に将来実装する際の拡張ポイント：

1. **AAL2Policy** (新エンティティ): コンテンツ単位のAAL2要求設定
   - 属性: `content_path`, `required_aal_level`, `enabled`
   - ストレージ: Ploneアノテーション or 独立したBTreeストレージ

2. **AuthenticationEvent** (新エンティティ): 認証イベントのログ記録
   - 属性: `user_id`, `timestamp`, `auth_method`, `result`, `aal_level`
   - ストレージ: ファイル（CSV/JSON）or データベース

3. **AAL2Session** (新エンティティ): AAL2認証済みセッション管理
   - 属性: `session_id`, `user_id`, `authenticated_at`, `expires_at`, `auth_method`
   - ストレージ: Ploneセッションストレージ拡張

これらの拡張は、本雛形のスタブメソッドを実装する際に追加されます。
