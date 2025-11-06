# Quickstart: c2.pas.aal2パッケージ雛形

**Date**: 2025-11-05
**Feature**: c2.pas.aal2 - Plone PAS AAL2認証プラグイン雛形

## はじめに

このクイックスタートガイドは、c2.pas.aal2パッケージ雛形をセットアップし、開発を開始するための手順を提供します。

## 前提条件

開始する前に、以下の環境が整っていることを確認してください：

- **Python**: 3.11以上
- **Plone**: 5.2以上のインストール済み環境（またはPlone開発環境）
- **Git**: バージョン管理用
- **pip**: Pythonパッケージマネージャー
- **virtualenv** または **venv**: Python仮想環境（推奨）

## セットアップ手順

### 1. パッケージ雛形の取得

```bash
# リポジトリをクローン（または雛形ファイルを配置）
git clone <repository-url> c2.pas.aal2
cd c2.pas.aal2
```

### 2. 仮想環境の作成と有効化

```bash
# Python仮想環境を作成
python3.11 -m venv venv

# 仮想環境を有効化
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. 開発モードでパッケージをインストール

```bash
# パッケージと開発依存関係をインストール
pip install -e ".[test]"

# または、setup.pyから直接インストール
python setup.py develop
```

**期待される出力**:
```
Successfully installed c2.pas.aal2 pytest pytest-cov ...
```

### 4. パッケージ構造の確認

```bash
# パッケージがインポート可能であることを確認
python -c "import c2.pas.aal2; print('Import successful!')"
```

**期待される出力**:
```
Import successful!
```

### 5. テストの実行

```bash
# Pytestを実行
pytest tests/ -v

# カバレッジレポート付きで実行
pytest tests/ --cov=c2.pas.aal2 --cov-report=term-missing
```

**期待される出力**:
```
tests/test_import.py::test_import_package PASSED
tests/test_plugin_registration.py::test_plugin_class_exists PASSED
tests/test_stub_methods.py::test_stub_methods_exist PASSED
======================== 3 passed in 0.5s ========================
```

## パッケージ構造の理解

雛形は以下の構造で構成されています：

```
c2.pas.aal2/
├── c2/                          # トップレベル名前空間
│   └── pas/                     # 第2レベル名前空間
│       └── aal2/                # 実際のパッケージコード
│           ├── __init__.py      # パッケージ初期化
│           ├── plugin.py        # AAL2Pluginスタブクラス
│           ├── interfaces.py    # Zopeインターフェース定義
│           └── configure.zcml   # ZCML設定ファイル
├── tests/                       # テストディレクトリ
│   ├── test_import.py           # インポートテスト
│   ├── test_plugin_registration.py  # プラグイン登録テスト
│   └── test_stub_methods.py     # スタブメソッド確認テスト
├── setup.py                     # パッケージメタデータ
├── README.md                    # パッケージドキュメント
└── LICENSE                      # ライセンスファイル
```

## 主要なファイルの説明

### `c2/pas/aal2/plugin.py`

AAL2Pluginのスタブクラスが定義されています。このクラスは以下のインターフェースを実装しています：

- `IAuthenticationPlugin`: 認証資格情報の検証
- `IExtractionPlugin`: リクエストからの資格情報抽出

**スタブメソッド**:
- `authenticateCredentials(credentials)`: 現在は`None`を返す
- `extractCredentials(request)`: 現在は空の辞書を返す

### `c2/pas/aal2/interfaces.py`

将来の実装のためのインターフェース定義が含まれています：

- `IAAL2Plugin`: AAL2プラグインが実装すべきメソッドの仕様

### `c2/pas/aal2/configure.zcml`

PASプラグインとしての登録設定が記述されています。Ploneがこのファイルを読み込むことで、プラグインがPASに登録されます。

### `setup.py`

パッケージメタデータ、依存関係、インストール設定が定義されています。

## Plone環境での動作確認

### 1. Ploneインスタンスへのパッケージ追加

Plone buildout設定（`buildout.cfg`）にパッケージを追加：

```ini
[buildout]
eggs =
    ...
    c2.pas.aal2

develop =
    path/to/c2.pas.aal2
```

### 2. Buildoutの実行

```bash
bin/buildout
```

### 3. Ploneインスタンスの起動

```bash
bin/instance fg
```

### 4. Plone管理画面でプラグインを確認

1. Plone管理画面にログイン
2. **Site Setup** → **Zope Management Interface** → **acl_users**
3. PASプラグイン一覧に「C2 PAS AAL2 Authentication Plugin」が表示されることを確認

### 5. プラグインの有効化

1. プラグインをクリックして詳細画面を開く
2. **Enable** をクリックして有効化
3. 既存の認証フローに影響がないことを確認（スタブメソッドは何もしない）

## 次のステップ

雛形が正しく動作したら、以下のステップで実装を進めます：

### 1. AAL2認証ロジックの実装

`plugin.py`のスタブメソッドを実装：

```python
def authenticateCredentials(self, credentials):
    """
    TODO: AAL2認証ロジックを実装
    - 資格情報を検証
    - AALレベルをチェック
    - 必要に応じて追加認証を要求
    """
    # 現在はスタブ
    return None
```

### 2. テストケースの追加

`tests/`ディレクトリに新しいテストを追加：

```bash
# 例: AAL2認証ロジックのテスト
touch tests/test_aal2_authentication.py
```

### 3. ドキュメントの更新

`README.md`や`docs/implementation_guide.md`に実装の詳細を記録

### 4. GenericSetupプロファイルの追加（オプション）

Plone管理画面からのインストール・アンインストールを容易にするため：

```bash
mkdir -p c2/pas/aal2/profiles/default
touch c2/pas/aal2/profiles/default/metadata.xml
```

## トラブルシューティング

### インポートエラー

**問題**: `ModuleNotFoundError: No module named 'c2'`

**解決策**:
1. パッケージが開発モードでインストールされているか確認：
   ```bash
   pip list | grep c2.pas.aal2
   ```
2. 仮想環境が有効化されているか確認
3. `setup.py`の`namespace_packages`設定を確認

### テスト失敗

**問題**: `pytest`実行時にテストが失敗する

**解決策**:
1. 依存関係が正しくインストールされているか確認：
   ```bash
   pip install -e ".[test]"
   ```
2. Python 3.11以上を使用しているか確認：
   ```bash
   python --version
   ```

### Ploneでプラグインが表示されない

**問題**: PAS管理画面にプラグインが表示されない

**解決策**:
1. `configure.zcml`が正しく配置されているか確認
2. Buildoutで`develop`ディレクティブが正しく設定されているか確認
3. Ploneインスタンスを再起動

## リファレンス

- **Plone.PAS Documentation**: https://docs.plone.org/develop/plone/security/pas.html
- **Products.PluggableAuthService**: https://pypi.org/project/Products.PluggableAuthService/
- **Pytest Documentation**: https://docs.pytest.org/
- **Python Namespace Packages**: https://packaging.python.org/guides/packaging-namespace-packages/

## サポート

問題が発生した場合は、以下を参照してください：

- プロジェクトの`README.md`
- `docs/implementation_guide.md`（将来の実装ガイドライン）
- Ploneコミュニティフォーラム: https://community.plone.org/

## まとめ

このクイックスタートガイドに従うことで、c2.pas.aal2パッケージ雛形のセットアップとテスト実行が完了しました。次は、スタブメソッドを実装して実際のAAL2認証機能を追加していきましょう。

**推定所要時間**: 10分（Plone環境が既に整っている場合）
