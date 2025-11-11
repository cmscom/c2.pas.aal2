# Implementation Plan: AAL2 Protection for Plone Admin Interfaces

**Branch**: `006-aal2-admin-protection` | **Date**: 2025-11-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-aal2-admin-protection/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature extends the existing AAL2 compliance framework (003) to specifically protect Plone administrative interfaces. The primary requirement is to enforce 15-minute passkey re-authentication for access to critical admin screens (control panel, user management, site settings, add-on management).

Key technical approach:
1. **URL Pattern Matching**: Implement a configurable registry of protected admin interface URL patterns
2. **Request Interception**: Use Plone traversal/publishing hooks to intercept admin interface access
3. **AAL2 Challenge Flow**: Leverage existing `session.is_aal2_valid()` and create new challenge view for admin contexts
4. **Configuration UI**: Provide control panel interface for managing protected admin screens
5. **Status Display**: Add viewlet to admin UI showing current AAL2 authentication status

This builds directly on the existing AAL2 session management (003) and passkey infrastructure (002), focusing the protection specifically on high-privilege administrative operations rather than general content access.

## Technical Context

**Language/Version**: Python 3.11+ (Plone 5.2+ requirement)
**Primary Dependencies**: Plone 5.2+, Products.PluggableAuthService (PAS), plone.app.registry, zope.publisher (for request interception), Products.CMFPlone (admin interface patterns)
**Storage**: ZODB (for protected URL patterns in plone.app.registry), existing AAL2 session storage (003)
**Testing**: pytest, plone.app.testing, mock
**Target Platform**: Linux/Unix servers running Plone 5.2+
**Project Type**: Plone add-on package extension (c2.pas.aal2)
**Performance Goals**: AAL2 check on admin access <10ms, URL pattern matching <5ms, no measurable impact on non-admin page loads
**Constraints**: Plone 5.2 compatibility, zero regressions in existing functionality, must handle concurrent admin access (multiple tabs), redirect preservation for UX
**Scale/Scope**: 4 user stories (P1: 1, P2: 2, P3: 1), ~10-12 new files, 5-7 URL patterns by default, registry-based configuration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: No formal constitution file exists (template only). Applying standard Plone development best practices:

✅ **Plone Best Practices Check**:
- **Add-on Structure**: Extends existing c2.pas.aal2 package (2-dot namespace) ✅
- **GenericSetup Integration**: Uses registry.xml for configuration ✅
- **Testing**: Comprehensive test coverage with plone.app.testing ✅
- **Request Interception**: Uses standard Zope publisher events ✅
- **Backward Compatibility**: No breaking changes to existing 001-005 features ✅
- **Security**: Reuses existing AAL2 session framework (003), no new attack surface ✅
- **Performance**: Minimal overhead with memoization and efficient URL matching ✅

**No violations or justifications required** - This feature follows established patterns from features 001-005 and extends the existing AAL2 framework to a new use case (admin interface protection) without architectural changes.

**Post-Phase 1 Re-evaluation** (2025-11-10):
- ✅ Design artifacts generated (research.md, data-model.md, contracts, quickstart.md)
- ✅ No new architectural complexity introduced
- ✅ All APIs integrate cleanly with existing features 002 & 003
- ✅ Performance targets achievable with proposed caching strategy
- ✅ Testing strategy follows existing plone.app.testing patterns
- **Confirmation**: No constitution violations in final design

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

This feature extends the existing c2.pas.aal2 Plone add-on package:

```text
src/c2/pas/aal2/
├── __init__.py                      # Package initialization (existing)
├── plugin.py                        # PAS plugin (existing)
├── credential.py                    # Passkey management (existing)
├── session.py                       # AAL2 session management (existing, from 003)
├── policy.py                        # AAL2 policy enforcement (existing, from 003)
├── permissions.py                   # Permission definitions (existing, from 003)
├── roles.py                         # Role management (existing, from 003)
│
├── admin/                           # [NEW] Admin interface protection
│   ├── __init__.py                  # [NEW]
│   ├── interfaces.py                # [NEW P1] Registry schema for protected URLs
│   ├── protection.py                # [NEW P1] Admin URL pattern matching & enforcement
│   ├── subscriber.py                # [NEW P1] Request event subscriber for interception
│   └── configure.zcml               # [NEW P1] Event subscriber registration
│
├── browser/                         # Browser views and UI (existing)
│   ├── __init__.py
│   ├── views.py                     # View classes (existing)
│   ├── viewlets.py                  # [MODIFY P3] Add AAL2 status viewlet
│   ├── configure.zcml               # [MODIFY] Register new views & viewlets
│   ├── templates/
│   │   ├── admin_aal2_challenge.pt  # [NEW P2] Admin-specific re-auth challenge
│   │   ├── admin_aal2_status.pt     # [NEW P3] AAL2 status viewlet template
│   │   └── ...                      # Other templates (existing)
│   └── static/
│       └── js/
│           ├── admin-aal2-status.js # [NEW P3] Status countdown timer
│           └── ...                  # Other JS files (existing, from 005)
│
├── controlpanel/                    # Control panel integration (existing, from 005)
│   ├── __init__.py
│   ├── interfaces.py                # [MODIFY P2] Add admin protection settings schema
│   ├── views.py                     # [MODIFY P2] Add admin protection config view
│   └── configure.zcml
│
├── utils/                           # Utilities (existing)
│   ├── __init__.py
│   ├── webauthn.py                  # WebAuthn helpers (existing)
│   └── audit.py                     # [MODIFY P1] Log admin access attempts
│
├── profiles/default/                # GenericSetup profile (existing)
│   ├── metadata.xml                 # Profile metadata (existing)
│   ├── registry.xml                 # [MODIFY P1+P2] Add protected URL patterns & settings
│   ├── controlpanel.xml             # [MODIFY P2] Add admin protection config panel
│   ├── viewlets.xml                 # [NEW P3] Register AAL2 status viewlet
│   └── ...                          # Other profile files (existing)
│
└── profiles/default/upgrades/       # Upgrade steps (existing)
    ├── configure.zcml               # [MODIFY] Add 006 upgrade step
    └── upgrade_to_006.py            # [NEW] Migration for feature 006

tests/                               # Test suite (existing)
├── test_admin_protection.py         # [NEW P1] Admin URL protection tests
├── test_admin_challenge.py          # [NEW P2] Admin challenge flow tests
├── test_admin_config.py             # [NEW P2] Configuration UI tests
├── test_admin_status.py             # [NEW P3] Status viewlet tests
├── test_integration_admin.py        # [NEW P1] End-to-end admin protection tests
└── ...                              # Other existing tests
```

**Structure Decision**:

This feature adds a new `admin/` module to the existing c2.pas.aal2 package, following the pattern established by features 003 and 005. The `admin/` module encapsulates all admin-interface-specific protection logic:

1. **admin/protection.py**: Core logic for URL pattern matching and AAL2 enforcement
2. **admin/subscriber.py**: Zope publisher event subscriber that intercepts admin requests
3. **admin/interfaces.py**: Registry schema for configurable protected URL patterns
4. **browser/templates/admin_*.pt**: Admin-specific UI templates
5. **controlpanel/**: Extended to include admin protection configuration

This separation keeps admin-specific code isolated while reusing the existing AAL2 session management infrastructure from feature 003.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - This feature follows standard Plone patterns without introducing architectural complexity. All changes extend existing code with focused, single-purpose modules.
