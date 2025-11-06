# Research: c2.pas.aal2パッケージ雛形

**Date**: 2025-11-05
**Feature**: c2.pas.aal2 - Plone PAS AAL2認証プラグイン雛形

## 目的

このリサーチは、2ドット形式のPloneパッケージ構造とPlone.PASプラグインの雛形を作成するための技術的な決定事項と根拠を文書化します。

## 研究項目

### 1. 2ドット形式のPloneパッケージ構造

**Decision**: `c2/pas/aal2/`の名前空間パッケージ構造を採用

**Rationale**:
- Ploneコミュニティでは、複数のドットを含むパッケージ名（例：`plone.app.contenttypes`）が標準的
- Pythonの名前空間パッケージを使用することで、各レベルで独立した`__init__.py`を配置可能
- `c2.pas.aal2`という命名により、c2プロジェクトのPAS関連、AAL2機能であることが明確
- Plone 5.2以降は名前空間パッケージを適切にサポート

**Alternatives Considered**:
- **単一ドット構造** (`c2_pas_aal2`): Plone標準から逸脱し、名前空間の階層化が不可能
- **3ドット以上** (`c2.pas.plugins.aal2`): 過度に深い階層は管理が複雑化し、インポートパスが冗長

**Best Practices**:
- 各名前空間レベルに`__init__.py`を配置し、適切な名前空間パッケージとして機能させる
- `setup.py`または`pyproject.toml`で`namespace_packages`または`packages=find_namespace_packages()`を指定
- MANIFEST.inでZCMLファイルを含めることを明示

### 2. Plone.PASプラグインインターフェース

**Decision**: `Products.PluggableAuthService.interfaces`の関連インターフェースを実装したスタブクラスを提供

**Rationale**:
- Plone.PASは複数のプラグインインターフェースを提供（IAuthenticationPlugin、IExtractionPlugin、ICredentialsResetPluginなど）
- AAL2認証プラグインとしては、最低限`IAuthenticationPlugin`と`IExtractionPlugin`の実装が必要
- スタブメソッドは`pass`または`return None`で実装し、将来の実装者がオーバーライド可能にする

**Alternatives Considered**:
- **全インターフェース実装**: 雛形段階では過剰。必要なインターフェースのみに絞る
- **インターフェースなし**: PASプラグインとして認識されない

**Best Practices**:
- Zopeインターフェースを`interfaces.py`で定義
- プラグインクラスに`@implementer`デコレータを使用
- ZCMLでプラグイン登録を行う（`<utility>`または`<adapter>`タグ）
- プラグインIDと説明文字列を提供

### 3. ZCMLによるプラグイン登録

**Decision**: `configure.zcml`を使用してPASプラグインを登録

**Rationale**:
- PloneはZope Configuration Markup Language (ZCML)を使用してコンポーネントを登録
- PASプラグインは`<utility>`タグでIPluggableAuthServiceの拡張として登録
- GenericSetupプロファイルと組み合わせることで、Plone管理画面からのインストール・アンインストールが可能

**Alternatives Considered**:
- **Pythonコードのみでの登録**: Plone標準から逸脱し、GenericSetupとの統合が困難
- **アノテーションベースの登録**: Plone 5.xではZCMLが依然として標準

**Best Practices**:
- `configure.zcml`はパッケージルート（`c2/pas/aal2/`）に配置
- `<configure xmlns="http://namespaces.zope.org/zope">`で開始
- `i18n:domain`を指定してi18n対応を準備
- GenericSetupプロファイルを`profiles/default/`に配置（雛形では空でも可）

### 4. Pytestテスト構造

**Decision**: `tests/`ディレクトリに3つの基本テストを配置

**Rationale**:
- Pytestは現代的なPythonテストフレームワークで、Ploneコミュニティでも採用増加中
- 雛形段階では構造検証に焦点を当てるため、単体テストのみで十分
- `conftest.py`で共通のフィクスチャやテスト設定を管理

**Test Cases**:
1. **test_import.py**: パッケージのインポート可能性を検証
   - `import c2.pas.aal2`が成功することを確認
   - 主要クラス・モジュールがインポート可能であることを確認

2. **test_plugin_registration.py**: プラグイン登録の検証
   - プラグインクラスが適切なインターフェースを実装していることを確認
   - ZCMLが構文的に正しいことを検証（可能であれば）

3. **test_stub_methods.py**: スタブメソッドの存在確認
   - 必要なPASプラグインメソッドが存在することを確認
   - スタブメソッドが呼び出し可能で、例外を発生させないことを確認

**Alternatives Considered**:
- **unittest**: Pytestの方が記述が簡潔で、フィクスチャ管理が優れている
- **統合テスト**: 雛形段階では不要。実装時に追加

**Best Practices**:
- `pytest.ini`でPytestの設定を管理（テストディスカバリ、カバレッジ設定等）
- `conftest.py`でPlone環境のモック（必要に応じて）を提供
- テストは独立して実行可能に保つ

### 5. パッケージメタデータとドキュメント

**Decision**: `setup.py`を使用し、標準的なPloneパッケージファイルを含める

**Rationale**:
- `setup.py`はPloneコミュニティで依然として広く使用されている（`pyproject.toml`への移行は進行中）
- MANIFEST.inでZCMLや静的ファイルをパッケージに含めることが必要
- README.mdで将来の実装者向けのガイドラインを提供

**Standard Files**:
- **setup.py**: パッケージメタデータ、依存関係、エントリーポイント
- **MANIFEST.in**: ZCMLファイル、READMEなど非Pythonファイルを含める
- **README.md**: パッケージの目的、インストール方法、構造説明
- **LICENSE**: GPLv2（Plone標準）またはMIT
- **.gitignore**: Python標準（`__pycache__/`, `*.pyc`, `dist/`, `*.egg-info/`等）
- **tox.ini**: 複数Python環境でのテスト自動化
- **CHANGES.rst**: バージョン履歴（Plone標準形式）

**Alternatives Considered**:
- **pyproject.toml**: 将来的には移行推奨だが、現時点ではPloneツールチェーンとの互換性を優先
- **最小限のファイルのみ**: 標準ファイルを含めることで、将来の開発者が拡張しやすくなる

**Best Practices**:
- `classifiers`でPython 3.11+とPlone 5.2+を明示
- `install_requires`でPlone依存関係を指定
- `extras_require`でテスト依存関係（pytest等）を分離
- README.mdに将来の実装に向けたTODOセクションを含める

### 6. ライセンス選択

**Decision**: GPLv2を推奨（Plone標準）、またはMITも許容

**Rationale**:
- Ploneコア自体がGPLv2を採用
- GPLv2を選択することでPloneエコシステムとの一貫性を保つ
- MITはより寛容で、商用利用の障壁が低い

**Alternatives Considered**:
- **Apache 2.0**: 特許条項が含まれるが、Ploneコミュニティでは一般的ではない
- **BSD**: MITと類似だが、Plone標準ではない

**Best Practices**:
- LICENSEファイルに選択したライセンスの全文を含める
- setup.pyの`license`フィールドで明示
- README.mdにライセンス情報を記載

## まとめ

このリサーチに基づき、以下の技術的決定を行いました：

1. **パッケージ構造**: 2ドット形式（`c2/pas/aal2/`）の名前空間パッケージ
2. **PASプラグイン**: IAuthenticationPluginとIExtractionPluginのスタブ実装
3. **ZCML登録**: configure.zcmlによる標準的なプラグイン登録
4. **テスト**: Pytest with 3つの基本テスト（インポート、登録、スタブメソッド）
5. **パッケージング**: setup.py with 標準的なPloneパッケージファイル一式
6. **ライセンス**: GPLv2（Plone標準）またはMIT

これらの決定により、Ploneコミュニティの標準に準拠した、拡張可能な雛形パッケージを提供できます。
