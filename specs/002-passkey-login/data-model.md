# Data Model: Passkey Authentication for Plone Login

**Branch**: `002-passkey-login` | **Date**: 2025-11-06
**Purpose**: Phase 1 design artifact defining data entities and relationships

## Overview

This document defines the data model for storing and managing passkey credentials in Plone. The model uses ZODB annotations on user objects to store multiple passkey credentials per user.

## Entity Definitions

### 1. Passkey Credential

**Description**: Represents a single registered WebAuthn credential (passkey) associated with a user account.

**Storage Location**: ZODB user object annotations
**Annotation Key**: `c2.pas.aal2.passkeys`
**Data Structure**: PersistentDict

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `credential_id` | bytes | Yes | Unique identifier for the credential (from WebAuthn) | Length: 16-1023 bytes |
| `public_key` | bytes | Yes | COSE-encoded public key | Valid COSE_Key format |
| `sign_count` | int | Yes | Authentication counter for replay protection | >= 0, wraps at 2^32 |
| `aaguid` | bytes | Yes | Authenticator AAGUID (16 bytes) | Length: 16 bytes |
| `device_name` | str | No | User-provided friendly name | Max 100 characters |
| `device_type` | str | Yes | Authenticator type | Values: "platform", "cross-platform" |
| `created` | datetime | Yes | Registration timestamp | UTC timezone |
| `last_used` | datetime | No | Last successful authentication | UTC timezone |
| `transports` | list[str] | No | Supported transport methods | Values: ["usb", "nfc", "ble", "internal", "hybrid"] |

**Indexes**:
- Primary key: `credential_id` (base64url-encoded as dict key)
- No secondary indexes needed (user-scoped data)

**Relationships**:
- Many-to-One: Multiple credentials → One user
- Storage: Via ZODB IAnnotations on user object

### 2. User Account (Extended)

**Description**: Existing Plone user object extended with passkey credentials via annotations.

**Storage Location**: ZODB (Plone user objects)
**Extension Method**: IAnnotations adapter

**New Annotation**:

```python
IAnnotations(user)["c2.pas.aal2.passkeys"] = PersistentDict({
    "base64url_credential_id_1": PersistentDict(credential_data),
    "base64url_credential_id_2": PersistentDict(credential_data),
    # ... more credentials
})
```

**Relationships**:
- One-to-Many: One user → Multiple passkey credentials
- Zero-to-Many: Users without passkeys have no annotation or empty PersistentDict

### 3. Authentication Event (Audit Log)

**Description**: Log entry for security auditing of passkey operations.

**Storage Location**: Plone audit log or custom logging table
**Purpose**: Security monitoring, debugging, compliance

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | str (UUID) | Yes | Unique event identifier |
| `event_type` | str | Yes | Type of operation |
| `user_id` | str | Yes | Plone user ID |
| `credential_id` | bytes | No | Affected credential (if applicable) |
| `timestamp` | datetime | Yes | Event time (UTC) |
| `success` | bool | Yes | Operation success/failure |
| `ip_address` | str | Yes | Client IP address |
| `user_agent` | str | Yes | Browser user agent |
| `error_message` | str | No | Error details (if failed) |

**Event Types**:
- `registration_start`: User initiated passkey registration
- `registration_success`: Passkey registered successfully
- `registration_failure`: Registration failed
- `authentication_start`: User initiated passkey login
- `authentication_success`: Login succeeded
- `authentication_failure`: Login failed
- `credential_deleted`: User removed a passkey
- `credential_used`: Passkey used for authentication (duplicate of auth_success, for convenience)

### 4. WebAuthn Challenge (Session)

**Description**: Temporary challenge data stored in user session during registration/authentication ceremonies.

**Storage Location**: Plone session (session_data_manager)
**Lifetime**: 5 minutes (300 seconds)

**Session Keys**:
- `webauthn_reg_challenge`: Challenge for registration
- `webauthn_auth_challenge`: Challenge for authentication
- `webauthn_reg_user_id`: User ID for registration (if pre-authenticated)

**Challenge Data Structure**:

```python
{
    "challenge": bytes,          # 32-byte random challenge
    "created": datetime,         # Challenge creation time
    "user_id": str,             # Associated user ID (optional for auth)
    "timeout": int,             # Challenge timeout in milliseconds
}
```

## Data Relationships

```
┌─────────────────┐
│  Plone User     │
│  (ZODB Object)  │
└────────┬────────┘
         │ IAnnotations
         │ One-to-Many
         ↓
┌─────────────────────────────────┐
│  Passkey Credentials            │
│  (PersistentDict annotation)    │
│  Key: c2.pas.aal2.passkeys      │
└────────┬────────────────────────┘
         │ Contains Multiple
         ↓
┌─────────────────────────────────┐
│  Individual Passkey             │
│  (PersistentDict entry)         │
│  - credential_id (key)          │
│  - public_key                   │
│  - sign_count                   │
│  - metadata...                  │
└─────────────────────────────────┘

         ┌──────────────────┐
         │  Session Data    │
         │  (Temporary)     │
         │  - challenge     │
         │  - created       │
         └──────────────────┘

         ┌──────────────────┐
         │  Audit Log       │
         │  (Persistent)    │
         │  - event_type    │
         │  - timestamp     │
         │  - user_id       │
         └──────────────────┘
```

## Storage Implementation Details

### ZODB Annotation Pattern

```python
from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict
from datetime import datetime, timezone
import base64

PASSKEY_ANNOTATION_KEY = "c2.pas.aal2.passkeys"

def get_user_passkeys(user):
    """
    Retrieve all passkey credentials for a user.

    Args:
        user: Plone user object

    Returns:
        PersistentDict: Dictionary of credential_id -> credential_data
    """
    annotations = IAnnotations(user)
    return annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

def add_passkey(user, credential_data):
    """
    Add a new passkey credential to a user.

    Args:
        user: Plone user object
        credential_data: Dict containing credential fields

    Returns:
        str: Base64url-encoded credential_id (the key used)
    """
    annotations = IAnnotations(user)
    passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

    # Use base64url-encoded credential_id as dictionary key
    credential_id_b64 = base64.urlsafe_b64encode(
        credential_data['credential_id']
    ).decode('ascii').rstrip('=')

    # Create persistent dict for this credential
    passkey = PersistentDict({
        'credential_id': credential_data['credential_id'],
        'public_key': credential_data['public_key'],
        'sign_count': credential_data.get('sign_count', 0),
        'aaguid': credential_data.get('aaguid', b''),
        'device_name': credential_data.get('device_name', ''),
        'device_type': credential_data.get('device_type', 'cross-platform'),
        'created': datetime.now(timezone.utc),
        'last_used': None,
        'transports': credential_data.get('transports', []),
    })

    passkeys[credential_id_b64] = passkey
    annotations[PASSKEY_ANNOTATION_KEY] = passkeys

    # Mark object as modified for ZODB persistence
    user._p_changed = True

    return credential_id_b64

def get_passkey(user, credential_id):
    """
    Retrieve a specific passkey credential.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str

    Returns:
        PersistentDict: Credential data, or None if not found
    """
    passkeys = get_user_passkeys(user)

    if isinstance(credential_id, bytes):
        credential_id_b64 = base64.urlsafe_b64encode(
            credential_id
        ).decode('ascii').rstrip('=')
    else:
        credential_id_b64 = credential_id

    return passkeys.get(credential_id_b64)

def update_passkey_last_used(user, credential_id, new_sign_count):
    """
    Update last_used timestamp and sign_count after successful authentication.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str
        new_sign_count: int

    Returns:
        bool: True if updated, False if credential not found
    """
    passkey = get_passkey(user, credential_id)
    if passkey is None:
        return False

    passkey['last_used'] = datetime.now(timezone.utc)
    passkey['sign_count'] = new_sign_count

    # Mark annotation and user as modified
    passkeys = get_user_passkeys(user)
    annotations = IAnnotations(user)
    annotations[PASSKEY_ANNOTATION_KEY] = passkeys
    user._p_changed = True

    return True

def delete_passkey(user, credential_id):
    """
    Delete a passkey credential.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str

    Returns:
        bool: True if deleted, False if not found
    """
    annotations = IAnnotations(user)
    passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

    if isinstance(credential_id, bytes):
        credential_id_b64 = base64.urlsafe_b64encode(
            credential_id
        ).decode('ascii').rstrip('=')
    else:
        credential_id_b64 = credential_id

    if credential_id_b64 not in passkeys:
        return False

    del passkeys[credential_id_b64]
    annotations[PASSKEY_ANNOTATION_KEY] = passkeys
    user._p_changed = True

    return True

def count_passkeys(user):
    """
    Count how many passkeys a user has registered.

    Args:
        user: Plone user object

    Returns:
        int: Number of registered passkeys
    """
    passkeys = get_user_passkeys(user)
    return len(passkeys)
```

## Data Validation Rules

### Credential ID Validation

```python
def validate_credential_id(credential_id):
    """Validate credential_id format and length."""
    if not isinstance(credential_id, bytes):
        raise ValueError("credential_id must be bytes")
    if not (16 <= len(credential_id) <= 1023):
        raise ValueError("credential_id length must be 16-1023 bytes")
    return True
```

### Public Key Validation

```python
def validate_public_key(public_key):
    """Validate public_key is valid COSE format."""
    if not isinstance(public_key, bytes):
        raise ValueError("public_key must be bytes")
    # py_webauthn handles COSE validation during verification
    # Basic length check: COSE keys are typically 50-150 bytes
    if len(public_key) < 32:
        raise ValueError("public_key too short (invalid COSE format)")
    return True
```

### Sign Count Validation

```python
def validate_sign_count(old_count, new_count):
    """
    Validate sign_count increment for replay protection.

    Returns:
        bool: True if valid, False if potential replay attack
    """
    # Handle counter wrap (very rare, after 2^32 authentications)
    if new_count == 0 and old_count > (2**32 - 1000):
        return True  # Likely counter wrap

    # Normal case: new count must be greater
    return new_count > old_count
```

### Device Name Validation

```python
def validate_device_name(name):
    """Validate user-provided device name."""
    if name is None or name == "":
        return True  # Optional field
    if not isinstance(name, str):
        raise ValueError("device_name must be string")
    if len(name) > 100:
        raise ValueError("device_name too long (max 100 characters)")
    # Sanitize for XSS protection
    import html
    return html.escape(name)
```

## State Transitions

### Credential Lifecycle

```
    [Registration Start]
            ↓
    [Challenge Generated] → (5min timeout) → [Challenge Expired]
            ↓
    [User Authenticates Device]
            ↓
    [Credential Verified]
            ↓
    [Credential Stored] ────────────────┐
            ↓                           │
    [Active Credential] ←───────────────┘
            ↓                           ↑
    [Used for Auth] ────────────────────┘
            ↓ (updates last_used, sign_count)
    [User Deletes]
            ↓
    [Credential Removed]
```

### Sign Count State Machine

```
Initial: sign_count = 0

Each authentication:
    1. Verify new_count > stored_count
    2. If valid: stored_count = new_count
    3. If invalid: reject authentication (potential replay attack)

Special case - Counter wrap:
    If new_count == 0 AND stored_count > 2^32-1000:
        Accept as valid wrap
        Reset stored_count = 0
```

## Migration Strategy

### Initial Installation

No existing data to migrate. Users start with zero passkeys.

### Future Schema Changes

If credential schema needs to change:

1. **Add version field** to credential dict:
   ```python
   passkey['schema_version'] = 1
   ```

2. **Migration script** for ZODB traversal:
   ```python
   def migrate_passkey_schema(portal):
       """Migrate all user passkeys to new schema version."""
       acl_users = portal.acl_users
       for user_id in acl_users.getUserIds():
           user = acl_users.getUserById(user_id)
           passkeys = get_user_passkeys(user)

           for key, passkey in passkeys.items():
               if passkey.get('schema_version', 0) < 2:
                   # Apply migration transformations
                   passkey['new_field'] = default_value
                   passkey['schema_version'] = 2

           # Save changes
           annotations = IAnnotations(user)
           annotations[PASSKEY_ANNOTATION_KEY] = passkeys
           user._p_changed = True
   ```

3. **Generic Setup upgrade step** in `upgrades.py`

## Performance Considerations

### Read Performance

- **Lookup by credential_id**: O(1) - dictionary key lookup
- **Count passkeys**: O(1) - len(dict)
- **List all passkeys**: O(n) where n = number of user's passkeys (typically 1-5)

### Write Performance

- **Add passkey**: O(1)
- **Update passkey**: O(1)
- **Delete passkey**: O(1)

### ZODB Considerations

- Annotations stored with user object - loaded together (good locality)
- Typical passkey size: ~500 bytes
- User with 5 passkeys: ~2.5 KB additional data
- ZODB handles this efficiently with object caching
- No indexes needed (user-scoped queries only)

### Scalability Limits

- **10,000 users**: No issues with annotation approach
- **100,000+ users**: Consider separate BTrees for credential_id → user_id mapping if cross-user lookups needed (currently not required)

## Security Considerations

### Data Protection

1. **Public Keys**: Not secret, but protect from tampering via ZODB transaction isolation
2. **Credential IDs**: Effectively public, but validate origin during authentication
3. **AAGUID**: Device identifier, not sensitive
4. **Sign Count**: Critical for replay protection - must be updated atomically

### Integrity

- ZODB transactions ensure atomic updates
- Always use `user._p_changed = True` after modifying annotations
- Sign count updates must be within same transaction as authentication

### Deletion

- Soft delete not needed (credentials can be re-registered)
- Hard delete with audit log entry
- Enforce minimum one authentication method before deletion (FR-016)

## References

- [ZODB Persistent Objects](https://zodb.org/en/latest/guide/writing-persistent-objects.html)
- [Zope Annotations](https://zope.readthedocs.io/en/latest/zope2book/AppendixC.html)
- [WebAuthn Credential Structure](https://www.w3.org/TR/webauthn-2/#sctn-credential-descriptor)
- [COSE Key Format](https://datatracker.ietf.org/doc/html/rfc8152)
