Changelog
=========

0.1.0 (unreleased)
------------------

- パーミッション登録タイミングを修正（__init__.pyでpermissionsモジュールをインポート）
- GenericSetup rolemapのパースエラーを修正（acquired属性をacquireに変更）
- Initial package structure for c2.pas.aal2 Plone PAS AAL2 authentication plugin
- Created namespace package structure (c2/pas/aal2/)
- Implemented stub AAL2Plugin class with IAuthenticationPlugin and IExtractionPlugin interfaces
- Added basic pytest test structure
- Included ZCML configuration for plugin registration
- Package template ready for future AAL2 authentication logic implementation
