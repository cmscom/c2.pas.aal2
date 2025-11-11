# Research: AAL2 Protection for Plone Admin Interfaces

**Feature**: 006-aal2-admin-protection
**Date**: 2025-11-10
**Phase**: 0 - Research & Technology Selection

## Overview

This document captures research findings and technology decisions for implementing AAL2 protection specifically for Plone administrative interfaces. The goal is to identify the best approach for intercepting admin requests, matching URL patterns, and enforcing re-authentication challenges.

## Research Areas

### 1. Plone Request Interception Mechanisms

**Decision**: Use `zope.publisher.interfaces.IPubBeforeCommit` event subscriber

**Rationale**:
- Standard Zope pattern for request-level interception
- Fires after traversal but before response commit, allowing redirect to challenge page
- Used successfully in Plone security add-ons (e.g., Products.LoginLockout)
- Allows examination of full request context including traversed object
- Better performance than IPublishTraverse (fires only once per request)

**Alternatives Considered**:
1. **IPublishTraverse adapter**: Fires multiple times during traversal (performance concern)
2. **BeforeTraverseEvent**: Too early - cannot access final traversed object
3. **Custom PAS plugin method**: Would require modifying existing plugin interface
4. **Plone transform chain**: Inappropriate - transforms are for content rendering

**Implementation Pattern**:
```python
from zope.publisher.interfaces import IPubBeforeCommit
from zope.component import adapter

@adapter(IPubBeforeCommit)
def check_admin_aal2(event):
    request = event.request
    # Check if URL matches protected pattern
    # Check if AAL2 is valid
    # Redirect to challenge if needed
```

**Reference**: Plone documentation on event subscribers, Products.LoginLockout source code

---

### 2. URL Pattern Matching Strategy

**Decision**: Use Python `fnmatch` with registry-stored patterns

**Rationale**:
- `fnmatch` provides glob-style patterns (e.g., `*/@@overview-controlpanel`) familiar to admins
- Lightweight and fast (<1ms per match)
- No external dependencies (Python stdlib)
- Registry storage via plone.app.registry allows runtime configuration without code deploy
- Supports wildcards for flexible matching (e.g., `*/manage*`, `*/prefs_*`)

**Alternatives Considered**:
1. **Regular expressions**: More powerful but complex for admins to configure, slower
2. **Hardcoded URL list**: Inflexible, requires code changes for new patterns
3. **Adapter lookup by interface**: Over-engineered for URL matching use case
4. **Path prefix matching**: Too simplistic (e.g., `/admin` would miss `@@manage-portlets`)

**Default Protected Patterns**:
```python
DEFAULT_PROTECTED_PATTERNS = [
    '*/@@overview-controlpanel',      # Main control panel
    '*/@@usergroup-userprefs',        # User management
    '*/@@usergroup-groupprefs',       # Group management
    '*/@@member-registration',        # User registration settings
    '*/prefs_install_products_form',  # Add-on management (Plone 5.2)
    '*/@@installer',                  # Add-on installer (Plone 6)
    '*/@@security-controlpanel',      # Security settings
]
```

**Registry Schema** (plone.app.registry):
```python
from zope import schema
from zope.interface import Interface

class IAAL2AdminSettings(Interface):
    """AAL2 admin protection settings."""

    protected_patterns = schema.List(
        title=u"Protected Admin URL Patterns",
        description=u"URL patterns requiring AAL2 (glob syntax: */pattern)",
        value_type=schema.TextLine(),
        default=DEFAULT_PROTECTED_PATTERNS,
        required=False,
    )

    enabled = schema.Bool(
        title=u"Enable Admin AAL2 Protection",
        description=u"Require AAL2 re-authentication for admin interfaces",
        default=True,
    )
```

---

### 3. Challenge Flow & Redirect Handling

**Decision**: Store original URL in session, redirect to dedicated challenge view, redirect back on success

**Rationale**:
- Matches user expectation (similar to login flow)
- Session storage ensures redirect URL survives authentication
- Dedicated view provides admin-specific messaging
- Prevents double-challenge if user refreshes

**Alternatives Considered**:
1. **Query parameter for redirect**: Visible in URL, security concern (open redirect)
2. **Referer header**: Unreliable, can be spoofed or missing
3. **Modal overlay**: Requires JavaScript, poor mobile experience
4. **In-place challenge**: Complex to inject into arbitrary admin pages

**Flow**:
```
1. User accesses /Plone/@@overview-controlpanel
2. Subscriber detects protected URL + expired AAL2
3. Store '/Plone/@@overview-controlpanel' in session['aal2_redirect']
4. Redirect to /Plone/@@admin-aal2-challenge
5. Challenge view shows admin-specific message + passkey prompt
6. On success: update AAL2 timestamp, redirect to session['aal2_redirect']
7. On failure/cancel: clear session, redirect to portal homepage
```

**Session Key**: `c2.pas.aal2.admin_redirect_url`

**Security Considerations**:
- Validate redirect URL is same-origin
- Clear redirect URL after use (prevent replay)
- Set max age on session data (5 minutes timeout)

---

### 4. Multi-Tab Handling

**Decision**: Use server-side AAL2 timestamp in user session (existing 003 infrastructure)

**Rationale**:
- AAL2 timestamp already stored in user session/annotations by feature 003
- Timestamp is shared across all tabs/windows for same user
- Re-authentication in one tab immediately updates timestamp for all tabs
- No additional synchronization mechanism needed

**Behavior**:
- User opens admin page in Tab A → AAL2 challenge → authenticates
- Timestamp updated to current time
- User switches to Tab B (same admin page) → loads immediately (timestamp fresh)
- After 15 minutes, both tabs require re-authentication on next navigation

**Edge Case Handling**:
- **Race condition** (2 tabs access expired AAL2 simultaneously):
  - Both redirect to challenge
  - First to complete updates timestamp
  - Second challenge view checks timestamp on load, auto-redirects if now valid

**No localStorage/JavaScript sync needed** - server-side timestamp is authoritative

---

### 5. Permission vs. Role-Based Access

**Decision**: Admin protection is orthogonal to permissions - applies to anyone accessing protected URLs

**Rationale**:
- Admin interfaces already have permission checks (e.g., `cmf.ManageSite`)
- AAL2 is an additional authentication assurance layer, not an authorization layer
- Simpler model: "If you can access it, we need to verify it's really you recently"
- Aligns with spec FR-013: "権限チェックを先に実行し、ユーザーが管理画面にアクセスする権限を持つ場合のみAAL2チェックを実行"

**Flow**:
```
1. User requests protected admin URL
2. Plone/Zope checks permissions (e.g., Manager role required)
3. If permission denied → 403 Forbidden (normal Plone behavior)
4. If permission granted → AAL2 subscriber checks timestamp
5. If AAL2 expired → redirect to challenge
6. If AAL2 valid → allow access
```

**No new permission needed** - FR-010 requirement is met by checking existing admin permissions

---

### 6. Status Viewlet Implementation

**Decision**: Use `plone.app.layout.viewlets.common.ViewletBase` with JavaScript countdown

**Rationale**:
- Standard Plone viewlet pattern
- Can be registered for specific viewlet manager (e.g., `plone.portalheader`)
- JavaScript countdown provides real-time feedback without polling
- Viewlet only renders for authenticated users with admin access

**Alternatives Considered**:
1. **Server-side refresh**: Poor UX, unnecessary load
2. **WebSocket/SSE**: Over-engineered for simple countdown
3. **Portlet**: Wrong pattern - viewlets are for UI chrome, portlets for content

**Viewlet Registration** (viewlets.xml):
```xml
<object>
  <order manager="plone.portalheader" skinname="*">
    <viewlet name="c2.pas.aal2.admin_status" insert-after="*"/>
  </order>
</object>
```

**JavaScript Pattern**:
```javascript
// Update countdown every second
setInterval(() => {
  const timestamp = getAAL2Timestamp(); // from inline data
  const remaining = calculateRemaining(timestamp);
  updateDisplay(remaining);
  if (remaining < 120) {
    showWarning(); // Yellow/red visual indicator
  }
}, 1000);
```

---

### 7. Testing Strategy

**Decision**: Use `plone.app.testing` with layer-based functional tests

**Rationale**:
- Existing test infrastructure in c2.pas.aal2 uses this pattern
- Functional tests can simulate full request/response cycle including redirects
- Layer setup can configure protected patterns for test isolation
- Mock objects for testing URL matching without full Plone instance

**Test Categories**:

1. **Unit Tests** (test_admin_protection.py):
   - URL pattern matching (fnmatch correctness)
   - Protected patterns registry access
   - AAL2 timestamp validation edge cases

2. **Integration Tests** (test_integration_admin.py):
   - Full request cycle: access → challenge → re-auth → redirect
   - Multi-tab simulation (concurrent requests)
   - Configuration changes take effect immediately
   - Audit logging verification

3. **Browser Tests** (test_admin_challenge.py):
   - Challenge page rendering
   - Passkey authentication flow integration
   - Redirect to original URL after success
   - Error handling (cancel, timeout)

**Mock Fixtures**:
```python
from plone.app.testing import PloneSandboxLayer

class AAL2AdminLayer(PloneSandboxLayer):
    def setUpPloneSite(self, portal):
        # Install c2.pas.aal2
        # Configure test patterns
        # Create test admin user with passkey
```

---

### 8. Performance Optimization

**Decision**: Use `plone.memoize.ram` for pattern compilation and permission checks

**Rationale**:
- Pattern matching happens on every admin request
- Compiled fnmatch patterns can be cached by pattern list hash
- Permission checks (for FR-013) can be cached per user/URL
- RAM cache invalidation on registry changes

**Caching Strategy**:
```python
from plone.memoize import ram
import time

def _pattern_cache_key(method, patterns):
    # Cache key: hash of pattern list
    return hash(tuple(patterns))

@ram.cache(_pattern_cache_key)
def compile_patterns(patterns):
    # Return compiled pattern matchers
    return [fnmatch.translate(p) for p in patterns]

# Invalidate on registry change
from zope.component import adapter
from plone.registry.interfaces import IRecordModifiedEvent

@adapter(IRecordModifiedEvent)
def invalidate_pattern_cache(event):
    if event.record.interfaceName == 'c2.pas.aal2.admin.interfaces.IAAL2AdminSettings':
        # Clear cache
        ram.cache.invalidate(_pattern_cache_key)
```

**Performance Targets** (from Technical Context):
- AAL2 check: <10ms
- URL pattern matching: <5ms
- No measurable impact on non-admin pages (early exit if URL doesn't match patterns)

---

## Summary of Key Decisions

| Area | Decision | Why |
|------|----------|-----|
| Request Interception | IPubBeforeCommit subscriber | Standard, efficient, full context |
| URL Matching | fnmatch with registry patterns | Simple, fast, configurable |
| Challenge Flow | Session redirect + dedicated view | Secure, familiar UX |
| Multi-Tab | Server-side timestamp (existing) | No sync needed, already built |
| Access Control | Orthogonal to permissions | Simpler, aligns with AAL2 concept |
| Status Display | Viewlet + JS countdown | Standard pattern, good UX |
| Testing | plone.app.testing layers | Consistent with existing tests |
| Performance | RAM cache for patterns | <10ms target achievable |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Pattern misconfiguration locks out admins | Medium | High | Provide bypass mechanism (direct portal root access) |
| Challenge redirect loop | Low | High | Track challenge attempts in session, max 3 redirects |
| Performance degradation on busy sites | Low | Medium | Early exit for non-admin URLs, pattern caching |
| Conflict with other security add-ons | Low | Medium | Test with common add-ons (Products.LoginLockout) |

---

## Open Questions

None - all technical decisions resolved during research phase.

---

## References

- Plone 5.2 Developer Documentation: https://5.docs.plone.org/
- zope.publisher Events: https://zopepublisher.readthedocs.io/
- plone.app.registry: https://pypi.org/project/plone.app.registry/
- Python fnmatch: https://docs.python.org/3/library/fnmatch.html
- Feature 003 (AAL2 Compliance): /workspace/specs/003-aal2-compliance/
