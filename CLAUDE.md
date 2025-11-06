# workspace Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-06

## Active Technologies
- Python 3.11+ + Plone 5.2+, Plone.PAS (Pluggable Authentication Service), webauthn==2.7.0 (py_webauthn by Duo Labs), setuptools/pip (002-passkey-login)
- ZODB (Zope Object Database) for passkey credentials stored in user objects (002-passkey-login)
- Python 3.11+ + Plone 5.2+, Plone.PAS (Pluggable Authentication Service), webauthn==2.7.0 (py_webauthn by Duo Labs), datetime (標準ライブラリ) (003-aal2-compliance)
- ZODB (Zope Object Database) - ユーザーオブジェクトにAAL2タイムスタンプ属性を追加、アノテーションでパーミッション設定を保存 (003-aal2-compliance)

- Python 3.11以上 + Plone 5.2以上、Plone.PAS（Ploneコアに含まれる）、setuptools/pip (001-c2-pas-aal2)

## Project Structure

```text
src/               # ソースコードディレクトリ（標準的なsrcレイアウト）
  c2/pas/aal2/     # 2ドット形式のPlone標準パッケージ構造
tests/             # テストディレクトリ
docs/              # ドキュメントディレクトリ
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11以上: Follow standard conventions

## Recent Changes
- 003-aal2-compliance: Added Python 3.11+ + Plone 5.2+, Plone.PAS (Pluggable Authentication Service), webauthn==2.7.0 (py_webauthn by Duo Labs), datetime (標準ライブラリ)
- 002-passkey-login: Added Python 3.11+ + Plone 5.2+, Plone.PAS (Pluggable Authentication Service), webauthn==2.7.0 (py_webauthn by Duo Labs), setuptools/pip

- 001-c2-pas-aal2: Added Python 3.11以上 + Plone 5.2以上、Plone.PAS（Ploneコアに含まれる）、setuptools/pip

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
