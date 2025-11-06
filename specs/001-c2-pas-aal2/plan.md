# Implementation Plan: c2.pas.aal2 - Plone PAS AAL2認証プラグイン雛形

**Branch**: `001-c2-pas-aal2` | **Date**: 2025-11-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-c2-pas-aal2/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

c2.pas.aal2パッケージの雛形を作成します。これは2ドット形式のPlone標準パッケージ構造を持ち、Plone.PASプラグインとして登録可能なスケルトンコードとスタブメソッドを含みます。実際のAAL2認証ロジックは含まず、将来の実装のための基盤を提供します。標準的なPloneパッケージファイル（LICENSE、MANIFEST.in、tox.ini等）とPytestベースのテスト構造を含みます。

## Technical Context

**Language/Version**: Python 3.11以上
**Primary Dependencies**: Plone 5.2以上、Plone.PAS（Ploneコアに含まれる）、setuptools/pip
**Storage**: N/A（雛形のため永続化なし）
**Testing**: pytest、pytest-cov（開発依存関係）
**Target Platform**: Plone環境（通常Linux/Unix系サーバー）
**Project Type**: single（Pythonパッケージライブラリ）
**Performance Goals**: パッケージインストール5分以内、テスト実行時間10秒以内
**Constraints**: Plone 5.2+互換性、既存認証フローへの影響ゼロ、Python 3.11+のみサポート
**Scale/Scope**: 小規模パッケージ雛形（推定500行未満のコード、3つのテストケース、標準的なPloneパッケージファイル一式）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: プロジェクト固有のConstitutionがまだ定義されていないため、一般的なPythonパッケージのベストプラクティスに基づいてチェックします。

### 一般的なベストプラクティス適合性

| チェック項目 | ステータス | 詳細 |
|------------|----------|------|
| パッケージ構造の標準化 | ✅ PASS | 2ドット形式のPlone標準構造を採用 |
| テスト可能性 | ✅ PASS | Pytestを使用した明確なテスト構造 |
| ドキュメント整備 | ✅ PASS | README、setup.py、ZCML等のドキュメントを含む |
| 依存関係の明示 | ✅ PASS | setup.py/pyproject.tomlで依存関係を定義 |
| バージョン互換性 | ✅ PASS | Python 3.11+、Plone 5.2+を明示 |
| ライセンス明示 | ✅ PASS | LICENSEファイルを含む（GPLv2またはMIT） |
| 後方互換性 | ✅ PASS | 既存認証フローに影響なし（スタブメソッド） |

**結果**: すべてのチェック項目に合格。Phase 0に進行可能。

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
├── src/                         # ソースコードディレクトリ（標準的なsrcレイアウト）
│   └── c2/                      # トップレベル名前空間
│       └── pas/                 # 第2レベル名前空間
│           └── aal2/            # 実際のパッケージコード
│               ├── __init__.py  # パッケージ初期化
│               ├── plugin.py    # PASプラグインスタブクラス
│               ├── interfaces.py # Zope インターフェース定義
│               └── configure.zcml # ZCML設定ファイル
│
├── tests/                       # テストディレクトリ
│   ├── __init__.py
│   ├── conftest.py              # pytest設定
│   ├── test_import.py           # インポートテスト
│   ├── test_plugin_registration.py  # プラグイン登録テスト
│   └── test_stub_methods.py     # スタブメソッド存在確認テスト
│
├── docs/                        # ドキュメントディレクトリ（オプション）
│   └── implementation_guide.md  # 将来の実装ガイドライン
│
├── setup.py                     # セットアップスクリプト（package_dir={'': 'src'}指定）
├── MANIFEST.in                  # パッケージマニフェスト
├── README.md                    # パッケージドキュメント
├── LICENSE                      # ライセンスファイル（GPLv2またはMIT）
├── .gitignore                   # Git除外設定
├── tox.ini                      # Tox設定（テスト自動化）
├── pytest.ini                   # Pytest設定
└── CHANGES.rst                  # 変更履歴（Plone標準）
```

**Structure Decision**: 標準的な`src/`レイアウトを採用し、2ドット形式のPlone標準パッケージ構造を`src/c2/pas/aal2/`に配置します。`setup.py`で`package_dir={'': 'src'}`を指定することで、Pythonの名前空間パッケージとして`import c2.pas.aal2`が可能になります。`src/`レイアウトは、パッケージコードとテストコードの分離を明確にし、インストール前の誤ったインポートを防ぎます。各レベルに`__init__.py`を配置し、適切なPython importパスを確保します。テストは独立した`tests/`ディレクトリに配置し、パッケージコードとの分離を維持します。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

該当なし - すべてのConstitution Checkに合格しています。
