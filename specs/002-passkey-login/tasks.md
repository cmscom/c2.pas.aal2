# タスク: Ploneログインへのパスキー認証

**入力**: `/specs/002-passkey-login/` からの設計ドキュメント
**前提条件**: plan.md（必須）、spec.md（ユーザーストーリー用に必須）、research.md、data-model.md、contracts/

**テスト**: このタスクリストにはテストタスクは含まれていません。機能仕様で明示的に要求された場合にのみテストを追加してください。

**組織**: タスクはユーザーストーリーごとにグループ化され、各ストーリーの独立した実装とテストを可能にします。

## フォーマット: `[ID] [P?] [Story] 説明`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが属するユーザーストーリー（例: US1、US2、US3）
- 説明に正確なファイルパスを含める

## パス規則

このプロジェクトはPloneアドオンパッケージ構造を使用します：
- **ソースコード**: `src/c2/pas/aal2/`
- **テスト**: `tests/`
- **ドキュメント**: `docs/`

---

## フェーズ1: セットアップ（共有インフラストラクチャ）

**目的**: プロジェクトの初期化と基本構造の作成

### セットアップタスク

- [X] T001 setup.pyでPloneパッケージ構造を作成（パッケージ名: c2.pas.aal2、依存関係: Plone>=5.2、webauthn==2.7.0）
- [X] T002 [P] src/c2/pas/aal2/__init__.py を作成（ネームスペースパッケージ宣言）
- [X] T003 [P] src/c2/pas/aal2/browser/__init__.py を作成
- [X] T004 [P] src/c2/pas/aal2/utils/__init__.py を作成
- [X] T005 [P] src/c2/pas/aal2/profiles/default/ ディレクトリを作成
- [X] T006 tests/ディレクトリを作成し、テスト用の__init__.pyを追加
- [X] T007 [P] docs/ディレクトリを作成し、README.mdを追加
- [X] T008 [P] .gitignoreを作成（Python、Plone、IDEの標準的な無視パターン）
- [X] T009 必要な依存関係をインストール（pip install -e .）して、パッケージ構造を検証

---

## フェーズ2: 基盤（ブロッキング前提条件）

**目的**: すべてのユーザーストーリーに必要な共有コンポーネント

**このフェーズを完了する必要がある理由**: これらのコンポーネントは、すべてのユーザーストーリーの実装に必要です。

### 基盤タスク

- [X] T010 src/c2/pas/aal2/credential.py にパスキー認証情報ストレージヘルパーを実装（get_user_passkeys、add_passkey、get_passkey、update_passkey_last_used、delete_passkey、count_passkeys関数）
- [X] T011 src/c2/pas/aal2/utils/storage.py にZODBアノテーションユーティリティを実装（IAnnotationsヘルパー、PersistentDict操作）
- [X] T012 [P] src/c2/pas/aal2/utils/webauthn.py にWebAuthnラッパー関数を実装（create_registration_options、verify_registration_response、create_authentication_options、verify_authentication_response）
- [X] T013 src/c2/pas/aal2/plugin.py にPASプラグインベースクラスを作成（BasePluginを継承、メタタイプ設定、プラグイン登録）
- [X] T014 src/c2/pas/aal2/browser/configure.zcml を作成（ブラウザビューの基本ZCML設定）
- [X] T015 src/c2/pas/aal2/profiles/default/metadata.xml を作成（GenericSetupプロファイルメタデータ）
- [X] T016 src/c2/pas/aal2/profiles/default/pas_plugins.xml を作成（PASプラグイン登録設定）

---

## フェーズ3: ユーザーストーリー1 - 既存アカウントへのパスキー登録（優先度: P1）

**目標**: ログイン中のユーザーが、プロフィールのセキュリティ設定からパスキーを登録できるようにする

**独立テスト基準**:
- 従来の認証情報でログイン
- セキュリティ設定に移動
- パスキー登録フローを完了
- パスキーが保存され、ユーザーアカウントに関連付けられていることを確認

**受け入れシナリオ**:
1. ログイン中のユーザーが「パスキーを追加」をクリックしてデバイス認証を完了すると、パスキーが登録され認証方法のリストに表示される
2. 既存のパスキーを持つユーザーが別のデバイスから別のパスキーを登録すると、両方のパスキーが保存され個別にリストされる
3. パスキー登録中にユーザーがブラウザの認証プロンプトをキャンセルすると、登録がキャンセルされ適切なメッセージが表示される

### US1: モデルとサービス

- [X] T017 [US1] src/c2/pas/aal2/plugin.py にgenerateRegistrationOptionsメソッドを実装（現在のユーザー用の登録オプションを生成、チャレンジをセッションに保存、既存の認証情報を除外）
- [X] T018 [US1] src/c2/pas/aal2/plugin.py にverifyRegistrationResponseメソッドを実装（WebAuthn登録レスポンスを検証、認証情報をZODBアノテーションに保存、監査ログイベントを作成）

### US1: APIエンドポイント

- [X] T019 [US1] src/c2/pas/aal2/browser/views.py にPasskeyRegisterOptionsViewクラスを作成（認証が必要、generateRegistrationOptionsを呼び出し、JSON形式でオプションを返す）
- [X] T020 [US1] src/c2/pas/aal2/browser/views.py にPasskeyRegisterVerifyViewクラスを作成（認証が必要、WebAuthn登録レスポンスを検証、成功/エラーレスポンスを返す）
- [X] T021 [US1] src/c2/pas/aal2/browser/configure.zcml に@@passkey-register-optionsビューを登録（PasskeyRegisterOptionsViewをマップ、zope2.View権限）
- [X] T022 [US1] src/c2/pas/aal2/browser/configure.zcml に@@passkey-register-verifyビューを登録（PasskeyRegisterVerifyViewをマップ、zope2.View権限）

### US1: UIテンプレート

- [X] T023 [US1] src/c2/pas/aal2/browser/templates/register_passkey.pt を作成（パスキー登録フォーム、デバイス名入力、WebAuthn JSインテグレーション、エラーハンドリング）
- [X] T024 [US1] src/c2/pas/aal2/browser/views.py にPasskeyRegisterFormViewクラスを作成（register_passkey.ptテンプレートを表示、ユーザープロフィール/セキュリティ設定からアクセス可能）
- [X] T025 [US1] src/c2/pas/aal2/browser/configure.zcml に@@passkey-register-formビューを登録（PasskeyRegisterFormViewをマップ、zope2.View権限）
- [X] T026 [US1] src/c2/pas/aal2/browser/templates/register_passkey.pt にJavaScriptを追加（WebAuthn APIを呼び出し、base64urlエンコーディング、オプションとレスポンスのエンドポイントと通信）

### US1: 統合

- [X] T027 [US1] Ploneユーザープロフィールにパスキー登録リンクを追加（セキュリティ設定タブまたは個人設定パネルに統合）
- [X] T028 [US1] エラーハンドリングを実装（チャレンジ期限切れ、重複認証情報、ユーザーキャンセル、ブラウザ非サポートのケース）
- [X] T029 [US1] 監査ログを実装（registration_start、registration_success、registration_failureイベントをPlone監査ログに記録）

---

## フェーズ4: ユーザーストーリー2 - パスキーでログイン（優先度: P2）

**目標**: 登録されたパスキーを持つユーザーが、パスワードの代わりにパスキーを使用してログインできるようにする

**依存関係**: ユーザーストーリー1（パスキー登録）が完了している必要があります

**独立テスト基準**:
- 登録されたパスキーでログインページにアクセス
- パスキーログインオプションを選択
- デバイス認証を完了
- 認証エリアへのログイン成功を確認

**受け入れシナリオ**:
1. 登録されたパスキーを持つユーザーが「パスキーでサインイン」を選択してデバイス認証を完了すると、パスワードを入力せずにログインされる
2. 複数の登録されたパスキーを持つユーザーが「パスキーでサインイン」を選択すると、現在のデバイスで複数のパスキーが利用可能な場合に使用するパスキーを選択できる
3. パスキーログインを試みるユーザーの認証が失敗またはキャンセルされると、ログインページに留まり再試行または従来のログインを使用するオプションが表示される

### US2: PAS認証プラグイン

- [X] T030 [US2] src/c2/pas/aal2/plugin.py にIExtractionPluginインターフェースを実装（extractCredentialsメソッド：リクエストからWebAuthnアサーションを抽出、認証情報dictを返す）
- [X] T031 [US2] src/c2/pas/aal2/plugin.py にIAuthenticationPluginインターフェースを実装（authenticateCredentialsメソッド：py_webauthnを使用してアサーションを検証、(user_id, login)を返すまたはNone）
- [X] T032 [US2] src/c2/pas/aal2/plugin.py にgenerateAuthenticationOptionsメソッドを実装（ユーザー名用の認証オプションを生成、チャレンジをセッションに保存、allowCredentialsリストを返す）
- [X] T033 [US2] src/c2/pas/aal2/plugin.py にverifyAuthenticationResponseメソッドを実装（WebAuthnアサーションを検証、sign_countを更新、last_usedタイムスタンプを更新、リプレイ攻撃をチェック）

### US2: APIエンドポイント

- [X] T034 [US2] src/c2/pas/aal2/browser/views.py にPasskeyLoginOptionsViewクラスを作成（パブリック、generateAuthenticationOptionsを呼び出し、JSON形式でオプションを返す）
- [X] T035 [US2] src/c2/pas/aal2/browser/views.py にPasskeyLoginVerifyViewクラスを作成（パブリック、WebAuthnアサーションを検証、認証済みセッションを作成、リダイレクトURLを返す）
- [X] T036 [US2] src/c2/pas/aal2/browser/configure.zcml に@@passkey-login-optionsビューを登録（PasskeyLoginOptionsViewをマップ、パブリックアクセス）
- [X] T037 [US2] src/c2/pas/aal2/browser/configure.zcml に@@passkey-login-verifyビューを登録（PasskeyLoginVerifyViewをマップ、パブリックアクセス）

### US2: UIテンプレート

- [X] T038 [US2] src/c2/pas/aal2/browser/templates/login_with_passkey.pt を作成（パスキーログインフォーム、ユーザー名入力（オプション）、WebAuthn JSインテグレーション、エラーハンドリング）
- [X] T039 [US2] src/c2/pas/aal2/browser/templates/login_with_passkey.pt にJavaScriptを追加（WebAuthn認証APIを呼び出し、オプションとレスポンスのエンドポイントと通信、ログイン成功時にリダイレクト）
- [X] T040 [US2] Ploneログインページを拡張（「パスキーでサインイン」ボタンを追加、従来のログインフォームとパスキーログインフォームを切り替え）

### US2: 統合

- [X] T041 [US2] PASプラグインをPlone acl_usersに登録（IExtractionPluginとIAuthenticationPluginを有効化、プラグインの優先順位を設定）
- [X] T042 [US2] セッション管理を実装（チャレンジの保存と検証、5分のTTL、チャレンジの期限切れハンドリング）
- [X] T043 [US2] エラーハンドリングを実装（無効な署名、認証情報が見つからない、リプレイ攻撃検出、ユーザーキャンセルのケース）
- [X] T044 [US2] 監査ログを実装（authentication_start、authentication_success、authentication_failureイベントをPlone監査ログに記録）

---

## フェーズ5: ユーザーストーリー4 - 従来のログインへのフォールバック（優先度: P2）

**目標**: パスキーを持つユーザーが、従来のユーザー名とパスワードを使用してログインできることを保証する

**依存関係**: ユーザーストーリー2（パスキーログイン）が完了している必要があります

**独立テスト基準**:
- 登録されたパスキーのないデバイスからアカウントにアクセス
- 従来のログインオプションを選択
- ユーザー名とパスワードを入力
- 認証の成功を確認

**受け入れシナリオ**:
1. パスキーを持たないデバイスにいるユーザーが「代わりにパスワードを使用」をクリックして有効な認証情報を入力すると、正常にログインされる
2. ログインページにいるユーザーがパスキーとパスワードの両方のログインオプションが利用可能な場合、両方の認証方法を明確に表示し切り替えることができる
3. パスワードを忘れたがパスキーを持つユーザーがパスキーで正常にログインすると、プロフィールからパスワードリセット機能にアクセスできる

### US4: UIとユーザーエクスペリエンス

- [ ] T045 [US4] Ploneログインページを更新（「代わりにパスワードを使用」リンクを追加、「パスキーでサインイン」リンクを追加、フォームを切り替えるJavaScript）
- [ ] T046 [US4] パスキーとパスワードの両方のログイン方法が明確に表示され、混乱しないUIデザインを実装
- [ ] T047 [US4] ブラウザのWebAuthnサポート検出を実装（パスキーオプションの条件付き表示、非サポートブラウザのフォールバック）
- [ ] T048 [US4] パスワードリセットワークフローをテスト（パスキーログイン後にパスワードリセット機能にアクセス可能であることを確認）

### US4: セキュリティとバリデーション

- [ ] T049 [US4] 従来の認証が常に利用可能であることを確認（PASプラグイン設定を検証、パスワード認証プラグインが有効のままであることを確認）
- [ ] T050 [US4] エッジケースを処理（パスキーデバイスの紛失、パスキーデバイスが利用できない、ブラウザがWebAuthnをサポートしていない）

---

## フェーズ6: ユーザーストーリー3 - 登録されたパスキーの管理（優先度: P3）

**目標**: ログイン中のユーザーが、登録されたパスキーを表示、管理、削除できるようにする

**依存関係**: ユーザーストーリー1（パスキー登録）が完了している必要があります

**独立テスト基準**:
- セキュリティ設定に移動
- デバイス情報とともに登録されたパスキーのリストを表示
- 削除するパスキーを選択
- 削除を確認
- リストから削除され認証に使用できなくなったことを確認

**受け入れシナリオ**:
1. セキュリティ設定ページにいるログイン中のユーザーがパスキーリストを表示すると、登録日と最終使用タイムスタンプとともにすべての登録されたパスキーが表示される
2. パスキーを表示しているログイン中のユーザーが特定のパスキーで「削除」をクリックして確認すると、そのパスキーが削除され認証に使用できなくなる
3. 唯一のパスキーを削除しようとするログイン中のユーザーがパスワードが設定されていない場合、システムは削除を防ぎ、少なくとも1つの認証方法をアクティブに保つ必要があるというメッセージを表示する

### US3: APIエンドポイント

- [ ] T051 [US3] src/c2/pas/aal2/browser/views.py にPasskeyListViewクラスを作成（認証が必要、get_user_passkeysを呼び出し、メタデータを含むパスキーのリストを返す）
- [ ] T052 [US3] src/c2/pas/aal2/browser/views.py にPasskeyDeleteViewクラスを作成（認証が必要、credential_idを受け取り、delete_passkeyを呼び出し、最後の認証方法チェックを実施、FR-016を実装）
- [ ] T053 [US3] src/c2/pas/aal2/browser/views.py にPasskeyUpdateViewクラスを作成（認証が必要、credential_idとdevice_nameを受け取り、パスキーメタデータを更新）
- [ ] T054 [US3] src/c2/pas/aal2/browser/configure.zcml に@@passkey-listビューを登録（PasskeyListViewをマップ、zope2.View権限）
- [ ] T055 [US3] src/c2/pas/aal2/browser/configure.zcml に@@passkey-deleteビューを登録（PasskeyDeleteViewをマップ、zope2.View権限）
- [ ] T056 [US3] src/c2/pas/aal2/browser/configure.zcml に@@passkey-updateビューを登録（PasskeyUpdateViewをマップ、zope2.View権限）

### US3: UIテンプレート

- [ ] T057 [US3] src/c2/pas/aal2/browser/templates/manage_passkeys.pt を作成（パスキーのテーブル/リスト、デバイス名、登録日、最終使用日を表示、削除ボタン、デバイス名編集機能）
- [ ] T058 [US3] src/c2/pas/aal2/browser/templates/manage_passkeys.pt にJavaScriptを追加（削除確認ダイアログ、@@passkey-deleteエンドポイントを呼び出し、デバイス名のインライン編集、@@passkey-updateエンドポイントを呼び出し）
- [ ] T059 [US3] src/c2/pas/aal2/browser/views.py にPasskeyManageViewクラスを作成（manage_passkeys.ptテンプレートを表示、ユーザープロフィール/セキュリティ設定からアクセス可能）
- [ ] T060 [US3] src/c2/pas/aal2/browser/configure.zcml に@@passkey-manageビューを登録（PasskeyManageViewをマップ、zope2.View権限）

### US3: ビジネスロジック

- [ ] T061 [US3] src/c2/pas/aal2/plugin.py に最後の認証方法チェックを実装（count_passkeysとhas_passwordを確認、最後の方法の削除を防止、FR-016を実装）
- [ ] T062 [US3] エラーハンドリングを実装（認証情報が見つからない、最後の認証方法エラー、権限の問題）
- [ ] T063 [US3] 監査ログを実装（credential_deletedイベントをPlone監査ログに記録）

### US3: 統合

- [ ] T064 [US3] Ploneユーザープロフィールにパスキー管理リンクを追加（セキュリティ設定タブまたは個人設定パネルに統合、登録されたパスキーのカウントを表示）

---

## フェーズ7: 最終調整とクロスカッティング機能

**目的**: 最終的な統合、ドキュメント、デプロイメント準備

### 最終調整タスク

- [ ] T065 [P] パフォーマンス最適化を実装（認証情報ルックアップキャッシング、チャレンジ生成の最適化、セッションストレージの効率化）
- [ ] T066 [P] セキュリティ監査を実施（HTTPSチェック、CSRFトークン検証、入力バリデーション、エラーメッセージのサニタイゼーション）
- [ ] T067 [P] docs/README.mdにユーザードキュメントを作成（インストール手順、パスキー登録ガイド、トラブルシューティング、FAQ）
- [ ] T068 [P] docs/ADMIN.mdに管理者ドキュメントを作成（PASプラグイン設定、セキュリティ考慮事項、監査ログアクセス）
- [ ] T069 [P] docs/DEVELOPER.mdに開発者ドキュメントを作成（APIリファレンス、拡張ポイント、カスタマイズガイド）
- [ ] T070 [P] インストール/アンインストール用のGenericSetupアップグレードステップを作成（既存のPloneサイトへの追加、クリーンアンインストール）
- [ ] T071 国際化(i18n)サポートを追加（UIテキストを翻訳可能にする、日本語翻訳を追加、英語翻訳を追加）
- [ ] T072 アクセシビリティチェックを実施（キーボードナビゲーション、スクリーンリーダーサポート、ARIAラベル）
- [ ] T073 [P] ブラウザ互換性テストを実施（Chrome、Firefox、Safari、Edge、各ブラウザでパスキー登録と認証をテスト）
- [ ] T074 setup.pyのメタデータを更新（バージョン、説明、分類子、依存関係の最終確認）
- [ ] T075 デプロイメント前チェックリストを完了（セキュリティレビュー、パフォーマンステスト、ドキュメントレビュー、全機能のE2Eテスト）

---

## 依存関係グラフ

### ユーザーストーリーの完了順序

```
Phase 1: Setup (T001-T009)
    ↓
Phase 2: Foundational (T010-T016)
    ↓
Phase 3: US1 - パスキー登録 (T017-T029) [優先度: P1]
    ↓
    ├─→ Phase 4: US2 - パスキーログイン (T030-T044) [優先度: P2]
    │       ↓
    │   Phase 5: US4 - フォールバック (T045-T050) [優先度: P2]
    │
    └─→ Phase 6: US3 - パスキー管理 (T051-T064) [優先度: P3]

Phase 7: 最終調整 (T065-T075) [すべてのユーザーストーリー完了後]
```

### 主要な依存関係

- **US2とUS4はUS1に依存**: パスキーログインとフォールバックは、パスキー登録機能が完了するまで実装できません
- **US3はUS1に依存**: パスキー管理は、パスキー登録機能が完了するまで実装できません
- **US4はUS2に依存**: フォールバックUIは、パスキーログインUIが完了するまで統合できません
- **基盤はすべてのユーザーストーリーのブロッキング前提条件**: Phase 2はすべてのユーザーストーリーの前に完了する必要があります

### 独立したユーザーストーリー

- **US1とUS2+US4は並行開発可能**: US1（登録）とUS2+US4（ログイン+フォールバック）は、基盤が完了した後、別々のチームによって並行開発できます
- **US3は独立**: US3（管理）は、US1が完了した後、他のストーリーと並行して開発できます

---

## ユーザーストーリーごとの並列実行の例

### Phase 3: US1 - パスキー登録（並列化可能なタスク）

**並列グループ1** (T017-T018完了後):
- T019: PasskeyRegisterOptionsView
- T020: PasskeyRegisterVerifyView
- T023: register_passkey.ptテンプレート

**並列グループ2** (T019-T023完了後):
- T021: @@passkey-register-options登録
- T022: @@passkey-register-verify登録
- T024: PasskeyRegisterFormView
- T026: WebAuthn JavaScript

**並列グループ3** (すべてのビューとテンプレート完了後):
- T027: プロフィール統合
- T028: エラーハンドリング
- T029: 監査ログ

### Phase 4: US2 - パスキーログイン（並列化可能なタスク）

**並列グループ1** (T030-T033完了後):
- T034: PasskeyLoginOptionsView
- T035: PasskeyLoginVerifyView
- T038: login_with_passkey.ptテンプレート

**並列グループ2** (T034-T038完了後):
- T036: @@passkey-login-options登録
- T037: @@passkey-login-verify登録
- T039: WebAuthn認証JavaScript
- T040: ログインページ拡張

**並列グループ3** (すべてのビューとテンプレート完了後):
- T041: PASプラグイン登録
- T042: セッション管理
- T043: エラーハンドリング
- T044: 監査ログ

### Phase 6: US3 - パスキー管理（並列化可能なタスク）

**並列グループ1** (基盤完了後):
- T051: PasskeyListView
- T052: PasskeyDeleteView
- T053: PasskeyUpdateView

**並列グループ2** (T051-T053完了後):
- T054: @@passkey-list登録
- T055: @@passkey-delete登録
- T056: @@passkey-update登録
- T057: manage_passkeys.ptテンプレート

**並列グループ3** (すべてのビューとテンプレート完了後):
- T058: 管理JavaScript
- T059: PasskeyManageView
- T061: 最後の認証方法チェック
- T062: エラーハンドリング
- T063: 監査ログ

### Phase 7: 最終調整（ほとんどが並列化可能）

**並列グループ** (すべてのユーザーストーリー完了後):
- T065: パフォーマンス最適化
- T066: セキュリティ監査
- T067: ユーザードキュメント
- T068: 管理者ドキュメント
- T069: 開発者ドキュメント
- T070: GenericSetupステップ
- T072: アクセシビリティチェック
- T073: ブラウザ互換性テスト
- T074: setup.py更新

**順次実行** (並列タスク完了後):
- T071: 国際化（UIテキストが確定した後）
- T075: デプロイメント前チェックリスト（すべて完了後）

---

## 実装戦略

### MVP（最小実行可能製品）

**推奨されるMVPスコープ**: ユーザーストーリー1のみ（パスキー登録）

**理由**:
- US1は独立してテスト可能です
- US1は即座にユーザー価値を提供します（セキュリティ意識の高いユーザーがパスキーを登録可能）
- US1はパスキーサポートの基盤を実証します
- US1は追加のログイン機能なしで既存の認証と共存できます

**MVPタスク**: T001-T029（セットアップ + 基盤 + US1）

### 段階的なデリバリー

**増分1** (MVP): ユーザーストーリー1 - パスキー登録
- タスク: T001-T029
- 成果物: ユーザーがセキュリティ設定からパスキーを登録できる
- テスト基準: 従来の認証情報でログインし、パスキー登録フローを完了し、パスキーが保存されていることを確認

**増分2**: ユーザーストーリー2 + ユーザーストーリー4 - パスキーログインとフォールバック
- タスク: T030-T050
- 成果物: ユーザーがパスキーでログインできる、従来のログインが利用可能
- テスト基準: 登録されたパスキーでログイン、従来の認証情報でログイン

**増分3**: ユーザーストーリー3 - パスキー管理
- タスク: T051-T064
- 成果物: ユーザーがパスキーを表示、更新、削除できる
- テスト基準: パスキーリストを表示、デバイス名を編集、パスキーを削除

**増分4**: 最終調整と本番環境対応
- タスク: T065-T075
- 成果物: 本番環境対応、完全なドキュメント、国際化、アクセシビリティ

### 並列開発の機会

**チーム1**: US1（パスキー登録） - T017-T029
**チーム2**: US2+US4（パスキーログイン+フォールバック） - T030-T050（US1完了後）
**チーム3**: US3（パスキー管理） - T051-T064（US1完了後）
**チーム4**: 最終調整とドキュメント - T065-T075（すべてのユーザーストーリー完了後）

すべてのチームは、Phase 2（基盤）が完了した後に作業を開始できます。

---

## タスクサマリー

**合計タスク数**: 75

**フェーズ別のタスク数**:
- Phase 1: Setup - 9タスク
- Phase 2: Foundational - 7タスク
- Phase 3: US1（パスキー登録） - 13タスク
- Phase 4: US2（パスキーログイン） - 15タスク
- Phase 5: US4（フォールバック） - 6タスク
- Phase 6: US3（パスキー管理） - 14タスク
- Phase 7: 最終調整 - 11タスク

**ユーザーストーリー別のタスク数**:
- US1（P1）: 13タスク（T017-T029）
- US2（P2）: 15タスク（T030-T044）
- US4（P2）: 6タスク（T045-T050）
- US3（P3）: 14タスク（T051-T064）

**並列化の機会**:
- Setup phase: 5タスクが並列化可能
- Foundational phase: 3タスクが並列化可能
- US1: 約8タスクがグループ内で並列化可能
- US2: 約10タスクがグループ内で並列化可能
- US3: 約9タスクがグループ内で並列化可能
- 最終調整: 約9タスクが並列化可能

**独立テスト基準**:
- US1: 従来の認証情報でログイン、セキュリティ設定に移動、パスキー登録フローを完了、パスキーが保存されていることを確認
- US2: 登録されたパスキーでログインページにアクセス、パスキーログインオプションを選択、デバイス認証を完了、ログイン成功を確認
- US4: 登録されたパスキーのないデバイスからアカウントにアクセス、従来のログインオプションを選択、ユーザー名とパスワードを入力、認証の成功を確認
- US3: セキュリティ設定に移動、パスキーリストを表示、パスキーを削除、リストから削除されたことを確認

**推奨されるMVPスコープ**: US1（パスキー登録）のみ - 29タスク（セットアップ + 基盤 + US1）

---

## 注意事項

1. **ファイルパス**: すべてのタスクには、実装する正確なファイルパスが含まれています
2. **並列実行**: [P]マーカーは、異なるファイルで作業し依存関係がないタスクを示します
3. **ユーザーストーリーラベル**: [US1]、[US2]、[US3]、[US4]ラベルは、各タスクがどのユーザーストーリーに貢献するかを示します
4. **依存関係**: 依存関係グラフは、ユーザーストーリーの完了順序を示します
5. **独立したテスト**: 各ユーザーストーリーは、他のストーリーが完了する前に独立してテストできます
6. **段階的なデリバリー**: 実装戦略セクションは、MVPから完全な機能への段階的なパスを概説します

---

**次のステップ**: 実装を開始するには、`/speckit.implement`コマンドを使用するか、T001から順番にタスクを手動で実装します。
