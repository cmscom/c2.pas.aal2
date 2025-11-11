# Data Model: AAL2 Protection for Plone Admin Interfaces

**Feature**: 006-aal2-admin-protection
**Date**: 2025-11-10
**Phase**: 1 - Design

## Overview

This document defines the data structures, schemas, and state management for AAL2 admin interface protection. Since this feature extends existing infrastructure (003-aal2-compliance), it primarily adds configuration data and transient session data rather than persistent entities.

---

## Entities

### 1. Protected Admin Pattern (Configuration)

**Description**: URL pattern configuration stored in plone.app.registry

**Storage**: ZODB via plone.app.registry (singleton configuration)

**Schema**: `c2.pas.aal2.admin.interfaces.IAAL2AdminSettings`

**Attributes**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `protected_patterns` | List[str] | No | See below | Glob-style URL patterns requiring AAL2 |
| `enabled` | bool | No | True | Global enable/disable for admin protection |

**Default Patterns**:
```python
[
    '*/@@overview-controlpanel',      # Main control panel
    '*/@@usergroup-userprefs',        # User management
    '*/@@usergroup-groupprefs',       # Group management
    '*/@@member-registration',        # User registration settings
    '*/prefs_install_products_form',  # Add-on management (Plone 5.2)
    '*/@@installer',                  # Add-on installer (Plone 6)
    '*/@@security-controlpanel',      # Security settings
]
```

**Validation Rules**:
- Each pattern must start with `*/` or contain at least one `/`
- Patterns cannot be empty strings
- Maximum 100 patterns (reasonable limit for performance)

**State Transitions**: N/A (configuration data, no state machine)

**Relationships**:
- None (singleton configuration object)

**Access Patterns**:
- Read on every admin request (cached via RAM cache)
- Write only through control panel UI (infrequent)

---

### 2. Admin Redirect Context (Session Data)

**Description**: Temporary storage of original URL during AAL2 challenge flow

**Storage**: Plone session (transient, in-memory or session DB)

**Key**: `c2.pas.aal2.admin_redirect_url`

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `original_url` | str | Yes | Full URL user was trying to access |
| `timestamp` | float | Yes | Unix timestamp when redirect was initiated |
| `challenge_count` | int | Yes | Number of challenge attempts (prevent loops) |

**Validation Rules**:
- `original_url` must be same-origin (security check)
- `timestamp` must be within 5 minutes of current time (expire old redirects)
- `challenge_count` must be ≤ 3 (prevent infinite loops)

**State Transitions**:
```
[Empty] → [Stored]       : User accesses protected URL with expired AAL2
[Stored] → [Validated]   : User completes AAL2 challenge successfully
[Validated] → [Empty]    : User redirected back to original URL
[Stored] → [Empty]       : Timeout (5 minutes) or max challenges exceeded
```

**Relationships**:
- Associated with user session
- References AAL2 timestamp (from feature 003)

**Access Patterns**:
- Write on challenge initiation (subscriber)
- Read on challenge view load (to display context)
- Read on challenge success (to redirect back)
- Delete after redirect or timeout

---

### 3. AAL2 Timestamp (Existing, from 003)

**Description**: User's last passkey authentication time

**Storage**: User session/annotations (existing from feature 003)

**Key**: `c2.pas.aal2.aal2_timestamp`

**Type**: `datetime` (Python datetime object)

**Validation**:
- Must be in the past
- Used to calculate if 15 minutes have elapsed

**Usage in 006**:
- **Read-only** - this feature does not modify AAL2 timestamps
- Timestamps are updated by passkey authentication flow (002/003)
- `session.is_aal2_valid(user)` checks this timestamp

---

### 4. Admin Access Audit Log Entry (Extension)

**Description**: Log entry for admin access attempts (extends existing audit log from 005)

**Storage**: ZODB audit log (existing from feature 005)

**Schema Extension**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | str | Yes | "admin_access_allowed" or "admin_access_challenged" |
| `admin_url` | str | Yes | Protected admin URL that was accessed |
| `aal2_valid` | bool | Yes | Whether AAL2 was valid at access time |
| `challenge_required` | bool | Yes | Whether challenge redirect was triggered |

**Existing Fields** (from 005):
- `timestamp`, `user_id`, `ip_address`, `user_agent`, etc.

**Validation**: Same as existing audit log

**State Transitions**: Append-only log (no state changes)

---

## Data Flow Diagrams

### Admin Access Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Request: GET /Plone/@@overview-controlpanel            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │ IPubBeforeCommit Subscriber │
        │  (admin/subscriber.py)      │
        └─────────────┬───────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │ Load Protected        │◄─── plone.app.registry
          │ Patterns from Registry│     (IAAL2AdminSettings)
          └───────────┬───────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │ Match URL against     │
          │ Patterns (fnmatch)    │
          └───────────┬───────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    No Match                   Match
         │                         │
         ▼                         ▼
    ┌────────┐         ┌──────────────────┐
    │ Allow  │         │ Check AAL2       │◄─── session.is_aal2_valid(user)
    │ Access │         │ Timestamp        │     (from 003)
    └────────┘         └────────┬─────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
              AAL2 Valid              AAL2 Expired
                   │                         │
                   ▼                         ▼
            ┌────────────┐         ┌─────────────────────┐
            │ Allow      │         │ Store Redirect URL  │──► Session
            │ Access     │         │ in Session          │    [admin_redirect_url]
            └────────────┘         └──────────┬──────────┘
                                              │
                                              ▼
                                   ┌────────────────────────┐
                                   │ Redirect to            │
                                   │ @@admin-aal2-challenge │
                                   └────────────────────────┘
```

### Challenge & Redirect Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User lands on: /Plone/@@admin-aal2-challenge                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │ Challenge View              │
        │  (browser/views.py)         │
        └─────────────┬───────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │ Load Redirect URL     │◄─── Session
          │ from Session          │     [admin_redirect_url]
          └───────────┬───────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │ Display Challenge UI  │
          │ (admin_aal2_          │
          │  challenge.pt)        │
          └───────────┬───────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │ User Authenticates    │──► WebAuthn API
          │ with Passkey          │    (from 002)
          └───────────┬───────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    Failure/Cancel             Success
         │                         │
         ▼                         ▼
    ┌────────────┐      ┌──────────────────┐
    │ Show Error │      │ Update AAL2      │──► session.set_aal2_timestamp()
    │ Message    │      │ Timestamp        │    (from 003)
    └────────────┘      └────────┬─────────┘
                                 │
                                 ▼
                      ┌────────────────────────┐
                      │ Retrieve Redirect URL  │◄─── Session
                      │ from Session           │     [admin_redirect_url]
                      └──────────┬─────────────┘
                                 │
                                 ▼
                      ┌────────────────────────┐
                      │ Clear Session Data     │──► Delete session key
                      └──────────┬─────────────┘
                                 │
                                 ▼
                      ┌────────────────────────┐
                      │ Redirect to Original   │
                      │ Admin URL              │
                      └────────────────────────┘
```

---

## Registry Schema (GenericSetup)

**File**: `profiles/default/registry.xml`

```xml
<registry>
  <records interface="c2.pas.aal2.admin.interfaces.IAAL2AdminSettings"
           prefix="c2.pas.aal2.admin">

    <value key="protected_patterns" purge="false">
      <element>*/@@overview-controlpanel</element>
      <element>*/@@usergroup-userprefs</element>
      <element>*/@@usergroup-grouppreps</element>
      <element>*/@@member-registration</element>
      <element>*/prefs_install_products_form</element>
      <element>*/@@installer</element>
      <element>*/@@security-controlpanel</element>
    </value>

    <value key="enabled">true</value>
  </records>
</registry>
```

---

## Database Queries / Access Patterns

### High-Frequency Operations (Every Admin Request)

1. **Check if URL is protected**:
   ```python
   from plone import api
   settings = api.portal.get_registry_record(
       'c2.pas.aal2.admin.protected_patterns'
   )
   # Cached via RAM cache - <1ms
   ```

2. **Check AAL2 validity**:
   ```python
   from c2.pas.aal2.session import is_aal2_valid
   valid = is_aal2_valid(user)
   # Uses existing session infrastructure - <5ms
   ```

### Medium-Frequency Operations (Challenge Flow)

3. **Store redirect URL**:
   ```python
   session = request.SESSION
   session['c2.pas.aal2.admin_redirect_url'] = {
       'original_url': request.URL,
       'timestamp': time.time(),
       'challenge_count': 1,
   }
   # Session write - <10ms
   ```

4. **Retrieve redirect URL**:
   ```python
   redirect_data = session.get('c2.pas.aal2.admin_redirect_url')
   if redirect_data and (time.time() - redirect_data['timestamp']) < 300:
       # Valid redirect within 5 minutes
       url = redirect_data['original_url']
   # Session read - <5ms
   ```

### Low-Frequency Operations (Configuration Changes)

5. **Update protected patterns**:
   ```python
   from plone import api
   api.portal.set_registry_record(
       'c2.pas.aal2.admin.protected_patterns',
       new_patterns
   )
   # Triggers cache invalidation
   # <50ms (infrequent operation)
   ```

---

## Performance Considerations

### Caching Strategy

1. **Pattern Matching Cache**:
   - Cache compiled fnmatch patterns by hash of pattern list
   - Invalidate on registry change (IRecordModifiedEvent)
   - Expected hit rate: >99% (patterns rarely change)

2. **Session Access**:
   - Plone session is already optimized (in-memory or fast DB)
   - No additional caching needed

3. **AAL2 Timestamp**:
   - Existing caching from feature 003
   - No changes needed

### Optimization Targets

- URL pattern matching: <5ms (via compiled pattern cache)
- AAL2 validity check: <5ms (existing 003 infrastructure)
- Total overhead per protected admin request: <10ms
- Non-admin requests: <1ms (early exit if URL doesn't match patterns)

---

## Data Retention & Cleanup

### Session Data

- **Redirect URLs**: Auto-expire after 5 minutes (handled by timeout check)
- **Challenge attempts**: Reset on successful authentication or timeout
- No manual cleanup needed (session lifecycle handles it)

### Configuration Data

- **Protected patterns**: Persisted indefinitely in registry
- **Historical values**: Not tracked (no audit trail for config changes in scope)

### Audit Logs

- Follows existing retention policy from feature 005
- No special handling needed for admin access events

---

## Migration from Feature 003/005

### Data Migration

**None required** - this feature:
- Reuses existing AAL2 timestamp storage (003)
- Adds new registry settings (no data to migrate)
- Extends audit log schema (backward compatible)

### Upgrade Step (upgrade_to_006.py)

```python
def upgrade_to_006(context):
    """Install AAL2 admin protection configuration."""

    # Import registry.xml to create settings
    setup = api.portal.get_tool('portal_setup')
    setup.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'plone.app.registry',
        run_dependencies=False,
    )

    # No data migration needed - new feature, new config
    logger.info("AAL2 admin protection settings installed")
```

---

## Security Considerations

### Session Security

- **Redirect URL validation**: Must be same-origin to prevent open redirect
- **Timestamp expiry**: 5-minute window prevents stale redirects
- **Challenge attempt limit**: Max 3 attempts prevents brute force

### Registry Security

- **Pattern validation**: Prevent malicious patterns (e.g., `*` would protect everything)
- **Configuration access**: Only Managers can modify (existing Plone permission)

### Audit Trail

- All admin access attempts logged (allowed and challenged)
- Timestamps and AAL2 validity recorded for forensic analysis

---

## Testing Data Fixtures

### Test Patterns

```python
TEST_PATTERNS = [
    '*/@@test-admin-page',
    '*/manage_*',
    '*/@@control-*',
]
```

### Test Session Data

```python
VALID_REDIRECT_DATA = {
    'original_url': 'http://localhost/Plone/@@overview-controlpanel',
    'timestamp': time.time(),
    'challenge_count': 1,
}

EXPIRED_REDIRECT_DATA = {
    'original_url': 'http://localhost/Plone/@@overview-controlpanel',
    'timestamp': time.time() - 600,  # 10 minutes ago
    'challenge_count': 1,
}

LOOP_REDIRECT_DATA = {
    'original_url': 'http://localhost/Plone/@@overview-controlpanel',
    'timestamp': time.time(),
    'challenge_count': 4,  # Exceeded limit
}
```

---

## Summary

This feature introduces minimal new data structures:

1. **Configuration Registry**: Persistent, rarely changed
2. **Session Redirect Data**: Transient, short-lived (5 minutes)
3. **Audit Log Extension**: Append-only, follows existing patterns

All persistent storage (AAL2 timestamps) is reused from feature 003, ensuring consistency and minimizing complexity.
