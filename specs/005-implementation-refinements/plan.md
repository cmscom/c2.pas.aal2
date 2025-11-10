# Implementation Plan: Implementation Refinements and Production Readiness

**Branch**: `005-implementation-refinements` | **Date**: 2025-11-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-implementation-refinements/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature refines the existing c2.pas.aal2 implementation (features 001-003) by addressing technical debt and production readiness gaps. The primary objectives are: (1) externalize inline JavaScript from templates to static files for maintainability, (2) implement persistent audit logging for compliance, (3) add internationalization support for global users, (4) integrate AAL2 settings into Plone control panel for better admin UX, and (5) optimize performance with catalog indexes. This is a refinement feature building on completed core functionality (passkey auth, AAL2 compliance, management UI).

## Technical Context

**Language/Version**: Python 3.11+ (Plone 5.2+ requirement)
**Primary Dependencies**: Plone 5.2+, Products.PluggableAuthService (PAS), Products.GenericSetup, plone.app.registry, webauthn==2.7.0, zope.annotation, ZODB
**Storage**: ZODB (primary storage for audit logs, user credentials, AAL2 metadata); Optional: PostgreSQL/MySQL via SQLAlchemy for audit logs (P2 enhancement)
**Testing**: pytest, plone.app.testing, mock, unittest
**Target Platform**: Linux/Unix servers running Plone 5.2+ (Python 3.11+)
**Project Type**: Plone add-on package (c2.pas.aal2)
**Performance Goals**: JavaScript load <50ms overhead, AAL2 policy checks <100ms p95, catalog queries <2s for 5000+ items
**Constraints**: Plone 5.2 compatibility (no Plone 6-only features), WebAuthn browser support (Chrome 67+, Firefox 60+, Safari 13+, Edge 18+), zero regressions in existing functionality
**Scale/Scope**: 5 independent user stories (P1: 1, P2: 2, P3: 2), ~15-20 new files, 5 JavaScript modules, 5 language translation catalogs, 2 catalog indexes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: No constitution file found (template placeholders only). Proceeding with standard Plone development best practices:

✅ **Plone Best Practices Check**:
- **Add-on Structure**: Follows 2-dot namespace package convention (c2.pas.aal2) ✅
- **GenericSetup Profiles**: Uses GenericSetup for configuration and upgrades ✅
- **Testing**: Comprehensive test coverage with plone.app.testing ✅
- **Internationalization**: i18n markers present, adding translation catalogs ✅
- **Resource Management**: Will use Plone resource registry for JavaScript ✅
- **Backward Compatibility**: Changes maintain compatibility with existing installations ✅
- **Security**: No new permissions introduced (P3 control panel reuses existing) ✅

**No violations or justifications required** - this is a refinement feature that enhances existing working code without architectural changes.

## Project Structure

### Documentation (this feature)

```text
specs/005-implementation-refinements/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (technology decisions, patterns)
├── data-model.md        # Phase 1 output (audit log schema, i18n catalog structure)
├── quickstart.md        # Phase 1 output (developer setup guide)
├── contracts/           # Phase 1 output (API contracts for audit log queries)
├── checklists/          # Quality validation checklists
│   └── requirements.md  # Spec validation (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

This is a Plone add-on package using the standard 2-dot namespace structure:

```text
src/c2/pas/aal2/                    # Main package
├── __init__.py                     # Package initialization
├── plugin.py                       # PAS plugin (existing)
├── credential.py                   # Passkey credential management (existing)
├── session.py                      # AAL2 session management (existing)
├── policy.py                       # AAL2 policy enforcement (existing)
├── permissions.py                  # Permission definitions (existing)
├── roles.py                        # Role management (existing)
│
├── browser/                        # Browser views and UI
│   ├── __init__.py
│   ├── views.py                    # View classes (existing)
│   ├── configure.zcml              # Browser layer configuration
│   ├── templates/                  # Page templates
│   │   ├── register_passkey.pt     # [MODIFY] Remove inline JS, add resource refs
│   │   ├── login_with_passkey.pt   # [MODIFY] Remove inline JS, add resource refs
│   │   ├── enhanced_login.pt       # [MODIFY] Remove inline JS, add resource refs
│   │   ├── manage_passkeys.pt      # [MODIFY] Remove inline JS, add resource refs
│   │   └── ...                     # Other templates
│   ├── aal2_challenge.pt           # [MODIFY] Remove inline JS, add resource refs
│   └── static/                     # [NEW] Static resources
│       └── js/                     # [NEW] External JavaScript files
│           ├── webauthn-utils.js   # [NEW P1] Common utilities (base64, error handling)
│           ├── webauthn-register.js # [NEW P1] Registration flow
│           ├── webauthn-login.js   # [NEW P1] Login/authentication flow
│           ├── webauthn-aal2.js    # [NEW P1] AAL2 challenge flow
│           └── passkey-management.js # [NEW P1] Management UI
│
├── storage/                        # [NEW P2] Audit log storage
│   ├── __init__.py                 # [NEW P2]
│   ├── audit.py                    # [NEW P2] Persistent audit log implementation
│   └── query.py                    # [NEW P2] Audit log query interface
│
├── locales/                        # [NEW P2] Internationalization
│   ├── en/                         # [NEW P2] English (baseline)
│   │   └── LC_MESSAGES/
│   │       └── c2.pas.aal2.po
│   ├── ja/                         # [NEW P2] Japanese
│   │   └── LC_MESSAGES/
│   │       └── c2.pas.aal2.po
│   ├── es/                         # [NEW P2] Spanish
│   │   └── LC_MESSAGES/
│   │       └── c2.pas.aal2.po
│   ├── fr/                         # [NEW P2] French
│   │   └── LC_MESSAGES/
│   │       └── c2.pas.aal2.po
│   └── de/                         # [NEW P2] German
│       └── LC_MESSAGES/
│           └── c2.pas.aal2.po
│
├── controlpanel/                   # [NEW P3] Control panel integration
│   ├── __init__.py                 # [NEW P3]
│   ├── interfaces.py               # [NEW P3] Schema for control panel settings
│   ├── views.py                    # [NEW P3] Control panel view
│   └── configure.zcml              # [NEW P3] Control panel registration
│
├── catalog/                        # [NEW P3] Catalog indexes
│   ├── __init__.py                 # [NEW P3]
│   └── indexes.py                  # [NEW P3] AAL2 protection and role indexes
│
├── utils/                          # Utilities (existing)
│   ├── __init__.py
│   ├── webauthn.py                 # WebAuthn helpers (existing)
│   └── audit.py                    # [MODIFY P2] Update to use persistent storage
│
├── profiles/default/               # GenericSetup profile
│   ├── metadata.xml                # Profile metadata (existing)
│   ├── pas_plugins.xml             # PAS plugin registration (existing)
│   ├── rolemap.xml                 # Permissions and roles (existing)
│   ├── jsregistry.xml              # [NEW P1] JavaScript resource registration
│   ├── registry.xml                # [NEW P3] Control panel settings schema
│   ├── catalog.xml                 # [NEW P3] Catalog index configuration
│   └── controlpanel.xml            # [NEW P3] Control panel registration
│
└── profiles/default/upgrades/      # [NEW] Upgrade steps for existing installations
    ├── configure.zcml              # [NEW] Upgrade step registration
    └── upgrade_to_005.py           # [NEW] Migration code for feature 005

tests/                              # Test suite (existing)
├── test_pas_plugin.py              # [MODIFY] Add JS externalization tests
├── test_browser_views.py           # [MODIFY] Add JS resource loading tests
├── test_audit_storage.py           # [NEW P2] Persistent audit log tests
├── test_i18n.py                    # [NEW P2] Translation catalog tests
├── test_controlpanel.py            # [NEW P3] Control panel tests
├── test_catalog_indexes.py         # [NEW P3] Catalog index tests
└── ...                             # Other existing tests

docs/                               # Documentation (existing)
├── README.md                       # [MODIFY] Update with new features
└── ...
```

**Structure Decision**:

This feature extends the existing Plone add-on package (c2.pas.aal2) rather than creating new projects. The structure follows Plone conventions:

1. **Browser layer** (`browser/`) handles UI, templates, and static resources
2. **New modules** (`storage/`, `controlpanel/`, `catalog/`) are added as siblings to existing modules
3. **GenericSetup profiles** (`profiles/default/`) configure all new components
4. **Upgrade steps** (`profiles/default/upgrades/`) ensure existing installations can migrate safely
5. **Tests** remain in top-level `tests/` directory following existing pattern

This maintains consistency with features 001-003 while cleanly separating new refinement code.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - This feature follows standard Plone development patterns without introducing architectural complexity. All changes are additive refinements to existing working code.
