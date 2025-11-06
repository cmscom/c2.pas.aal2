# setup.py Template for c2.pas.aal2

**Date**: 2025-11-06
**Feature**: c2.pas.aal2 - Plone PAS AAL2認証プラグイン雛形
**Purpose**: `src/` レイアウトに対応したsetup.pyの設定例

## 重要なポイント

### 1. `src/` レイアウトの設定

標準的な`src/`レイアウトを使用するため、以下の設定が必須です：

```python
setup(
    # ... その他の設定 ...
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    # ...
)
```

- `package_dir={'': 'src'}`: パッケージのルートディレクトリを`src/`に指定
- `packages=find_packages(where='src')`: `src/`以下のパッケージを自動検出

### 2. 名前空間パッケージの設定

2ドット形式のPlone標準パッケージ構造のため、名前空間パッケージの宣言が必要です：

```python
setup(
    # ...
    namespace_packages=['c2', 'c2.pas'],
    zip_safe=False,
    # ...
)
```

- `namespace_packages=['c2', 'c2.pas']`: `c2`と`c2.pas`を名前空間パッケージとして宣言
- `zip_safe=False`: Ploneパッケージは通常zipインストール不可

### 3. ZCMLファイルの包含

ZCML設定ファイルをパッケージに含めるため：

```python
setup(
    # ...
    include_package_data=True,
    # ...
)
```

そして、`MANIFEST.in`で以下を指定：

```
recursive-include src *.zcml
```

### 4. 依存関係の設定

```python
setup(
    # ...
    install_requires=[
        'setuptools',
        'Plone>=5.2',
        'Products.PluggableAuthService',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
        ],
    },
    python_requires='>=3.11',
    # ...
)
```

## 完全な setup.py 例

```python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

version = '0.1.0'

long_description = (
    open('README.md').read() + '\n' +
    open('CHANGES.rst').read()
)

setup(
    name='c2.pas.aal2',
    version=version,
    description='Plone PAS AAL2 Authentication Plugin Template',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Plone',
        'Framework :: Plone :: 5.2',
        'Framework :: Plone :: 6.0',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    ],
    keywords='Plone PAS authentication AAL2 security',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/c2.pas.aal2',
    license='GPLv2',

    # src/ レイアウトの設定
    package_dir={'': 'src'},
    packages=find_packages(where='src'),

    # 名前空間パッケージの宣言
    namespace_packages=['c2', 'c2.pas'],

    # ZCMLファイルを含める
    include_package_data=True,
    zip_safe=False,

    # 依存関係
    install_requires=[
        'setuptools',
        'Plone>=5.2',
        'Products.PluggableAuthService',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
        ],
    },

    # Python バージョン要件
    python_requires='>=3.11',

    # エントリーポイント（必要に応じて）
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
```

## MANIFEST.in の例

setup.pyと合わせて、`MANIFEST.in`も作成します：

```
include *.rst
include *.md
recursive-include src *.zcml
recursive-include src *.py
```

## インストール確認

設定が正しいことを確認するには：

```bash
# 開発モードでインストール
pip install -e .

# パッケージが正しくインポートできることを確認
python -c "import c2.pas.aal2; print('Success')"

# インストールされたファイルを確認
pip show -f c2.pas.aal2
```

## トラブルシューティング

### 問題: `import c2.pas.aal2` が失敗する

**原因**: `package_dir`の設定が誤っている、または名前空間パッケージの宣言が不足している

**解決策**:
1. `setup.py`で`package_dir={'': 'src'}`が正しく設定されているか確認
2. `namespace_packages=['c2', 'c2.pas']`が設定されているか確認
3. `src/c2/__init__.py`と`src/c2/pas/__init__.py`に名前空間パッケージ宣言があるか確認：
   ```python
   # -*- coding: utf-8 -*-
   __import__('pkg_resources').declare_namespace(__name__)
   ```

### 問題: ZCML ファイルがパッケージに含まれない

**原因**: `include_package_data=True`が設定されていない、または`MANIFEST.in`が不足している

**解決策**:
1. `setup.py`に`include_package_data=True`を追加
2. `MANIFEST.in`に`recursive-include src *.zcml`を追加
3. 再インストール: `pip install -e .`

### 問題: テスト実行時にパッケージが見つからない

**原因**: pytest の設定で`src/`ディレクトリが認識されていない

**解決策**:
`pytest.ini`または`pyproject.toml`で以下を設定：

```ini
[pytest]
pythonpath = src
testpaths = tests
```

## 参考資料

- [Packaging Python Projects - Python Packaging User Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [src layout vs flat layout](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#src-layout-vs-flat-layout)
- [Plone Package Development](https://docs.plone.org/develop/addons/index.html)
