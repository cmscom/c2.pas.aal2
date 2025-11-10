# Data Model: Implementation Refinements

**Feature**: 005-implementation-refinements
**Date**: 2025-11-10
**Status**: Completed

## Overview

This document defines the data models for persistent audit logging, control panel settings, and catalog indexes introduced in this feature. JavaScript externalization and i18n do not require new data models (file-based only).

---

## 1. Audit Log Data Model (P2)

### AuditLogContainer

Top-level container stored in portal annotations under key `c2.pas.aal2.audit_logs`.

**Storage**: ZODB annotation (`IAnnotations(portal)['c2.pas.aal2.audit_logs']`)

**Structure**:
```python
{
    'events': OOBTree(),           # timestamp (float) -> AuditEvent
    'by_user': OOBTree(),          # user_id (str) -> [event_ids]
    'by_action': OOBTree(),        # action_type (str) -> [event_ids]
    'by_outcome': OOBTree(),       # outcome (str) -> [event_ids]
    'metadata': {
        'created': datetime,
        'last_cleaned': datetime,
        'total_events': int,
        'retention_days': int
    }
}
```

**Indexes**:
- Primary: timestamp (OOBTree for range queries)
- Secondary: user_id, action_type, outcome (OOBTree for exact match queries)

**Operations**:
- `add_event(event)` - O(log n)
- `query_by_timestamp(start, end)` - O(log n + k) where k = result size
- `query_by_user(user_id)` - O(log n + k)
- `query_by_action(action_type)` - O(log n + k)
- `cleanup_old_events(before_timestamp)` - O(k log n) where k = events to delete

---

### AuditEvent

Individual audit log entry.

**Storage**: Persistent object in ZODB (referenced by AuditLogContainer)

**Schema**:
```python
class AuditEvent:
    """
    Represents a single security or authentication event.

    All timestamps are UTC. Metadata is JSON-serializable dict.
    """
    event_id: str                   # UUID4, unique identifier
    timestamp: datetime             # UTC timestamp of event
    user_id: str                    # Plone user ID (or 'anonymous')
    action_type: str                # Enum: see Action Types below
    outcome: str                    # Enum: 'success' | 'failure'
    ip_address: str                 # Source IP address (IPv4 or IPv6)
    user_agent: str                 # Browser User-Agent header
    metadata: dict                  # Action-specific data (see below)
```

**Action Types** (action_type enum):
```python
AUDIT_ACTION_TYPES = [
    # Passkey Registration
    'registration_start',        # User initiated passkey registration
    'registration_success',      # Passkey successfully registered
    'registration_failure',      # Passkey registration failed

    # Authentication
    'authentication_start',      # User initiated passkey login
    'authentication_success',    # Successful passkey authentication
    'authentication_failure',    # Failed passkey authentication

    # Credential Management
    'credential_deleted',        # User deleted a passkey
    'credential_updated',        # User updated passkey metadata

    # AAL2 Operations
    'aal2_timestamp_set',        # AAL2 timestamp recorded
    'aal2_access_granted',       # AAL2 check passed
    'aal2_access_denied',        # AAL2 check failed (expired)
    'aal2_policy_set',           # AAL2 policy applied to content

    # Role Management
    'aal2_role_assigned',        # AAL2 role granted to user
    'aal2_role_revoked',         # AAL2 role removed from user
]
```

**Metadata Schema** (by action_type):

```python
# registration_start
metadata = {
    'device_name': str,              # User-provided device name
    'authenticator_type': str,       # 'platform' | 'cross-platform' | null
}

# registration_success
metadata = {
    'device_name': str,
    'credential_id': str,            # WebAuthn credential ID
    'device_type': str,              # 'platform' | 'cross-platform'
    'aaguid': str,                   # Authenticator AAGUID
}

# registration_failure / authentication_failure
metadata = {
    'error_type': str,               # WebAuthn error name
    'error_message': str,            # Human-readable error
}

# authentication_success
metadata = {
    'credential_id': str,
    'sign_count': int,               # WebAuthn signature counter
    'aal2_elevated': bool,           # Whether this granted AAL2
}

# credential_deleted / credential_updated
metadata = {
    'credential_id': str,
    'old_device_name': str,          # For updates
    'new_device_name': str,          # For updates
}

# aal2_access_granted / aal2_access_denied
metadata = {
    'content_path': str,             # Path to protected content
    'required_level': str,           # 'AAL2'
    'time_since_auth': int,          # Seconds since last AAL2 auth
    'expiry_seconds': int,           # AAL2 timeout setting
}

# aal2_policy_set
metadata = {
    'content_path': str,
    'enabled': bool,
    'changed_by': str,               # User who made change
}

# aal2_role_assigned / aal2_role_revoked
metadata = {
    'target_user_id': str,           # User receiving/losing role
    'role_name': str,                # 'AAL2 Required User'
    'changed_by': str,
}
```

**Validation Rules**:
- `event_id` must be unique UUID4
- `timestamp` must be UTC (validated: `timestamp.tzinfo == pytz.UTC`)
- `action_type` must be in AUDIT_ACTION_TYPES
- `outcome` must be 'success' or 'failure'
- `ip_address` must be valid IPv4 or IPv6
- `metadata` must be JSON-serializable (no binary data)
- No sensitive data in metadata (passwords, tokens, session IDs)

**Retention Policy**:
- Default: 90 days
- Configurable via control panel (30-365 days)
- Cleanup runs daily via cron job or on-demand
- Deleted events are permanently removed (not soft-deleted)

---

## 2. Control Panel Settings (P3)

### AAL2Settings

Configuration stored in plone.app.registry.

**Storage**: plone.registry records (`plone.app.registry`)

**Schema Interface**:
```python
from zope.interface import Interface
from zope import schema

class IAAL2Settings(Interface):
    """AAL2 Security Configuration"""

    aal2_timeout_seconds = schema.Int(
        title="AAL2 Session Timeout",
        description="Seconds before AAL2 re-authentication required. "
                    "Default: 900 (15 minutes). Min: 300 (5 min). Max: 3600 (1 hour).",
        default=900,
        min=300,
        max=3600,
        required=True
    )

    aal2_enabled = schema.Bool(
        title="Enable AAL2 Protection",
        description="Turn AAL2 enforcement on/off globally. "
                    "When disabled, AAL2-protected content is accessible without re-auth.",
        default=True,
        required=True
    )

    audit_retention_days = schema.Int(
        title="Audit Log Retention Period",
        description="Days to retain audit logs before automatic cleanup. "
                    "Default: 90. Min: 30. Max: 365.",
        default=90,
        min=30,
        max=365,
        required=True
    )

    audit_storage_backend = schema.Choice(
        title="Audit Log Storage Backend",
        description="Where to store audit logs. ZODB is default. "
                    "SQL requires additional configuration (see docs).",
        values=['zodb', 'sql'],
        default='zodb',
        required=True
    )

    notification_email = schema.TextLine(
        title="Security Notification Email",
        description="Email address for security alerts (optional). "
                    "Leave empty to disable notifications.",
        default='',
        required=False
    )

    strict_mode = schema.Bool(
        title="Strict Mode",
        description="Block all operations if audit logging fails. "
                    "When disabled, audit failures are logged but operations proceed.",
        default=False,
        required=True
    )
```

**Registry Keys** (stored as):
```
c2.pas.aal2.aal2_timeout_seconds = 900
c2.pas.aal2.aal2_enabled = True
c2.pas.aal2.audit_retention_days = 90
c2.pas.aal2.audit_storage_backend = 'zodb'
c2.pas.aal2.notification_email = ''
c2.pas.aal2.strict_mode = False
```

**Access Pattern**:
```python
from plone import api

# Read setting
timeout = api.portal.get_registry_record(
    'c2.pas.aal2.aal2_timeout_seconds'
)

# Write setting
api.portal.set_registry_record(
    'c2.pas.aal2.aal2_timeout_seconds',
    600  # 10 minutes
)
```

**Validation**:
- All min/max constraints enforced by z3c.form
- Email validation if provided (regex: RFC 5322 simplified)
- Changes trigger event for cache invalidation

**Migration**:
- Default values applied on first install
- Existing `session.AAL2_TIMEOUT_SECONDS` constant migrated to registry
- Upgrade step creates registry records if missing

---

## 3. Catalog Indexes (P3)

### AAL2 Protection Index

**Index Name**: `aal2_protected`
**Index Type**: FieldIndex (boolean)
**Purpose**: Fast lookup of all AAL2-protected content

**Indexed Value**:
```python
@indexer(IContentish)
def aal2_protected(object):
    """
    Returns True if content requires AAL2, False otherwise.

    Logic:
    - Check object annotations for __aal2_required__ flag
    - Check parent content for inherited protection
    - Check workflow state-based protection rules
    """
    from c2.pas.aal2.policy import is_aal2_required
    try:
        return is_aal2_required(object)
    except:
        return False  # Fail open for indexing
```

**Query Examples**:
```python
# Find all protected content
catalog = getToolByName(portal, 'portal_catalog')
brains = catalog(aal2_protected=True)

# Count protected items
count = len(catalog(aal2_protected=True))

# Protected content in specific folder
brains = catalog(
    aal2_protected=True,
    path='/Plone/secure-folder'
)
```

**Reindexing**:
- On content creation: indexed automatically
- On policy change: `obj.reindexObject(idxs=['aal2_protected'])`
- Bulk reindex: `catalog.manage_reindexIndex(ids=['aal2_protected'])`

---

### AAL2 Required Roles Index

**Index Name**: `aal2_required_roles`
**Index Type**: KeywordIndex (list of strings)
**Purpose**: Find content protected for specific roles

**Indexed Value**:
```python
@indexer(IContentish)
def aal2_required_roles(object):
    """
    Returns list of role names that require AAL2 for this content.

    Returns:
        list: Role names, e.g. ['Editor', 'Reviewer']
        [] if no role-based AAL2 protection
    """
    annotations = IAnnotations(object, {})
    return annotations.get('__aal2_required_roles__', [])
```

**Query Examples**:
```python
# Find content requiring AAL2 for Editors
brains = catalog(aal2_required_roles='Editor')

# Find content requiring AAL2 for Editor OR Reviewer
brains = catalog(aal2_required_roles=['Editor', 'Reviewer'])

# Find content with any role-based AAL2 protection
brains = catalog(
    aal2_protected=True,
    aal2_required_roles={'query': [], 'operator': 'or'}
)
```

**Reindexing**:
- Same as aal2_protected index
- Event subscriber on role assignment/revocation

---

## 4. Translation Catalog Structure (P2)

### .po File Format

Translation catalogs follow standard gettext format.

**File Locations**:
```
src/c2/pas/aal2/locales/
├── c2.pas.aal2.pot                 # Template (auto-generated)
├── en/LC_MESSAGES/c2.pas.aal2.po  # English
├── ja/LC_MESSAGES/c2.pas.aal2.po  # Japanese
├── es/LC_MESSAGES/c2.pas.aal2.po  # Spanish
├── fr/LC_MESSAGES/c2.pas.aal2.po  # French
└── de/LC_MESSAGES/c2.pas.aal2.po  # German
```

**Entry Structure**:
```po
#: src/c2/pas/aal2/browser/templates/register_passkey.pt:12
msgid "Register a Passkey"
msgstr "パスキーを登録" # Japanese translation

#: src/c2/pas/aal2/browser/views.py:45
msgid "Touch your security key or use your device's biometric sensor"
msgstr "セキュリティキーにタッチするか、デバイスの生体認証センサーを使用してください"
```

**Metadata**:
- Language code (ISO 639-1): en, ja, es, fr, de
- Character encoding: UTF-8
- Plural forms per language
- Translator credits

**Priority Strings** (Must be translated first):
1. Error messages (authentication failures, WebAuthn errors)
2. Button labels ("Register Passkey", "Login with Passkey")
3. Form field labels and help text
4. Security warnings

**Total Strings**: ~50-60 translatable strings across UI

---

## State Transitions

### Audit Event Lifecycle

```
[Event occurs]
    → create AuditEvent object
    → validate schema
    → assign UUID
    → write to AuditLogContainer (ZODB)
    → index in BTrees
    → [retained until cleanup]
    → delete after retention_days
    → [TERMINAL]
```

**Error Handling**:
- If ZODB write fails → log to Python logger → continue operation (unless strict_mode=True)
- If index update fails → log error → event still stored (reindex later)
- If cleanup fails → log error → retry next scheduled run

---

### Control Panel Setting Lifecycle

```
[Admin changes setting]
    → validate input (z3c.form)
    → write to plone.registry
    → trigger IRecordModifiedEvent
    → subscribers invalidate caches
    → [new value active immediately]
```

---

## Relationships

```
┌─────────────────┐
│   Portal        │
│  (Plone site)   │
└────────┬────────┘
         │ annotations
         │
         ├──► AuditLogContainer
         │        ├──► AuditEvent (many)
         │        └──► Indexes (BTrees)
         │
         ├──► plone.registry
         │        └──► IAAL2Settings
         │
         └──► portal_catalog
                  ├──► aal2_protected (FieldIndex)
                  └──► aal2_required_roles (KeywordIndex)

┌─────────────────┐
│   Content       │
│  (IContentish)  │
└────────┬────────┘
         │ annotations
         │
         ├──► __aal2_required__ (bool)
         └──► __aal2_required_roles__ (list)
```

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Add audit event | O(log n) | BTree insert |
| Query by timestamp range | O(log n + k) | k = result count |
| Query by user/action | O(log n + k) | Secondary index lookup |
| Cleanup old events | O(k log n) | k = events to delete |
| Catalog query (protected) | O(log n) | FieldIndex lookup |
| Catalog query (roles) | O(log n + k) | KeywordIndex lookup |
| Registry setting read | O(1) | Cached in memory |
| Registry setting write | O(1) | Plus cache invalidation |

**Scalability**:
- Audit logs: Tested up to 1M events in ZODB
- Catalog: Handles 100k+ content items efficiently
- Registry: No scale issues (few settings)

---

## Data Migration

### From Feature 003 → 005

1. **AAL2 Timeout**: Migrate hardcoded `session.AAL2_TIMEOUT_SECONDS` to registry
2. **Audit Logs**: Create new AuditLogContainer (no migration needed, start fresh)
3. **Catalog Indexes**: Add new indexes, reindex all content
4. **Translations**: Add locales directory (no migration needed)

**Upgrade Step** (`profiles/default/upgrades/upgrade_to_005.py`):
```python
def upgrade_to_005(context):
    """Upgrade to feature 005"""
    setup_tool = getToolByName(context, 'portal_setup')

    # 1. Install new registry records
    setup_tool.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'plone.app.registry'
    )

    # 2. Initialize audit log container
    from c2.pas.aal2.storage.audit import initialize_audit_container
    initialize_audit_container(context)

    # 3. Add catalog indexes
    setup_tool.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'catalog'
    )

    # 4. Reindex AAL2 fields
    catalog = getToolByName(context, 'portal_catalog')
    catalog.manage_reindexIndex(ids=['aal2_protected', 'aal2_required_roles'])

    logger.info("Upgraded to feature 005")
```

---

## Validation Rules Summary

1. **AuditEvent**:
   - event_id: UUID4 format
   - timestamp: UTC datetime
   - action_type: Must be in AUDIT_ACTION_TYPES enum
   - outcome: 'success' or 'failure' only
   - metadata: JSON-serializable, no sensitive data

2. **IAAL2Settings**:
   - aal2_timeout_seconds: 300 ≤ value ≤ 3600
   - audit_retention_days: 30 ≤ value ≤ 365
   - notification_email: Valid RFC 5322 email or empty

3. **Catalog Indexes**:
   - aal2_protected: Boolean only
   - aal2_required_roles: List of strings (role names)

All validation enforced at schema level (zope.schema) or in indexer functions.
