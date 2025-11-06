# Implementation Plan: Passkey Authentication for Plone Login

**Branch**: `002-passkey-login` | **Date**: 2025-11-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-passkey-login/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add passkey (WebAuthn) authentication to Plone login as an alternative to traditional username/password authentication. Users can register multiple passkeys via their profile settings and use them for passwordless login. The system maintains password authentication as a fallback to prevent account lockout. Passkey credentials are stored in Zope's user data storage (ZODB) alongside existing user information.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+
**Primary Dependencies**: Plone 5.2+, Plone.PAS (Pluggable Authentication Service), webauthn==2.7.0 (py_webauthn by Duo Labs), setuptools/pip
**Storage**: ZODB (Zope Object Database) for passkey credentials stored in user objects
**Testing**: pytest, plone.app.testing (Plone testing framework)
**Target Platform**: Web server (Linux/Unix), web browsers with WebAuthn support
**Project Type**: web (Plone add-on package)
**Performance Goals**: <500ms for passkey authentication validation, <2s for registration ceremony
**Constraints**: Must work with existing Plone PAS infrastructure, HTTPS required for WebAuthn, backward compatible with existing authentication
**Scale/Scope**: Support 10,000+ users with multiple passkeys each, typical Plone site scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: No project constitution defined - using general best practices

Since no project-specific constitution exists (`.specify/memory/constitution.md` is a template), this project will follow:
- Standard Plone add-on development practices
- PAS plugin architecture patterns
- Python packaging standards (setuptools)
- Test-driven development with pytest
- Security best practices for authentication (WebAuthn spec compliance)

**Gate Status**: ✅ PASS - No constitutional violations (no constitution defined)

**Post-Design Re-evaluation** (2025-11-06):
- ✅ Design complete: Phase 0 (research) and Phase 1 (data model, contracts, quickstart) artifacts generated
- ✅ No constitutional violations introduced
- ✅ Follows standard Plone add-on patterns (PAS plugin, ZODB annotations, GenericSetup profiles)
- ✅ Adheres to security best practices (WebAuthn spec compliance, HTTPS requirement, challenge validation)
- ✅ Ready for Phase 2 (task generation with `/speckit.tasks`)

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
src/
└── c2/
    └── pas/
        └── aal2/
            ├── __init__.py
            ├── plugin.py              # PAS plugin implementation
            ├── credential.py          # Passkey credential storage models
            ├── browser/
            │   ├── __init__.py
            │   ├── views.py          # Registration/login views
            │   ├── configure.zcml
            │   └── templates/        # Page templates for UI
            │       ├── register_passkey.pt
            │       ├── manage_passkeys.pt
            │       └── login_with_passkey.pt
            ├── utils/
            │   ├── __init__.py
            │   ├── webauthn.py       # WebAuthn ceremony helpers
            │   └── storage.py        # ZODB storage utilities
            └── profiles/
                └── default/
                    ├── metadata.xml
                    └── pas_plugins.xml

tests/
├── test_plugin.py                    # PAS plugin tests
├── test_credential.py                # Credential model tests
├── test_webauthn.py                  # WebAuthn ceremony tests
├── test_views.py                     # Browser view tests
└── test_integration.py               # End-to-end flow tests

docs/                                 # User documentation
setup.py                              # Package configuration
```

**Structure Decision**: Plone 2-dot namespace package structure (c2.pas.aal2) following Plone conventions. The package is a PAS plugin that integrates with Plone's existing authentication infrastructure. Browser views handle UI, utilities manage WebAuthn ceremonies and ZODB storage, and the plugin coordinates authentication flows.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitutional violations to justify.
