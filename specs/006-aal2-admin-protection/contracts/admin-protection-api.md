# API Contracts: AAL2 Admin Protection

**Feature**: 006-aal2-admin-protection
**Date**: 2025-11-10
**Phase**: 1 - Design

## Overview

This document defines the internal APIs and interfaces for AAL2 admin protection. Since this is a Plone add-on extending PAS, most interactions are through Zope interfaces, event subscribers, and registry records rather than REST/GraphQL APIs.

---

## Python Module Interfaces

### 1. Admin Protection Core (`admin/protection.py`)

#### `is_protected_url(url: str) -> bool`

**Purpose**: Determine if a URL matches any protected admin pattern

**Parameters**:
- `url` (str): Full URL or path to check

**Returns**:
- `bool`: True if URL matches a protected pattern, False otherwise

**Behavior**:
```python
# Example patterns: ['*/@@overview-controlpanel', '*/manage_*']
is_protected_url('/Plone/@@overview-controlpanel')  # True
is_protected_url('/Plone/@@manage-portlets')        # True
is_protected_url('/Plone/front-page')               # False
```

**Performance**: <5ms (cached compiled patterns)

**Errors**:
- No exceptions raised (defensive - returns False on errors)

---

#### `check_admin_access(request, user) -> dict`

**Purpose**: Check if user should be allowed to access admin URL in request

**Parameters**:
- `request` (HTTPRequest): Zope request object
- `user` (PloneUser): Current authenticated user

**Returns**:
```python
{
    'allowed': bool,           # True if access granted
    'reason': str,             # Reason for denial ('aal2_expired', 'not_protected', etc.)
    'redirect_url': str|None,  # URL to redirect to if denied (challenge page)
}
```

**Example Responses**:
```python
# Access allowed - URL not protected
{'allowed': True, 'reason': 'not_protected', 'redirect_url': None}

# Access allowed - AAL2 still valid
{'allowed': True, 'reason': 'aal2_valid', 'redirect_url': None}

# Access denied - AAL2 expired
{'allowed': False, 'reason': 'aal2_expired', 'redirect_url': '/Plone/@@admin-aal2-challenge'}
```

**Errors**:
- Returns `{'allowed': True, 'reason': 'error', 'redirect_url': None}` on exception (fail-open for availability)

---

#### `get_protected_patterns() -> List[str]`

**Purpose**: Retrieve current list of protected URL patterns from registry

**Parameters**: None

**Returns**:
- `List[str]`: List of glob-style URL patterns

**Caching**: Results cached via `plone.memoize.ram`, invalidated on registry change

**Example**:
```python
patterns = get_protected_patterns()
# ['*/@@overview-controlpanel', '*/@@usergroup-userprefs', ...]
```

**Errors**:
- Returns default patterns if registry not accessible
- Logs warning on exception

---

### 2. Admin Redirect Management (`admin/protection.py`)

#### `store_redirect_context(request, original_url: str) -> None`

**Purpose**: Store original URL in session for post-challenge redirect

**Parameters**:
- `request` (HTTPRequest): Zope request object
- `original_url` (str): URL user was trying to access

**Side Effects**:
- Writes to `request.SESSION['c2.pas.aal2.admin_redirect_url']`
- Increments challenge attempt counter

**Validation**:
- `original_url` must be same-origin (prevent open redirect)
- Raises `ValueError` if validation fails

**Example**:
```python
store_redirect_context(request, 'http://localhost/Plone/@@overview-controlpanel')
# Session now contains:
# {
#   'original_url': 'http://localhost/Plone/@@overview-controlpanel',
#   'timestamp': 1699123456.789,
#   'challenge_count': 1
# }
```

---

#### `get_redirect_context(request) -> dict | None`

**Purpose**: Retrieve stored redirect context from session

**Parameters**:
- `request` (HTTPRequest): Zope request object

**Returns**:
```python
{
    'original_url': str,
    'timestamp': float,
    'challenge_count': int
} | None  # None if not found or expired
```

**Validation**:
- Returns None if timestamp > 5 minutes old
- Returns None if challenge_count > 3 (loop prevention)

**Example**:
```python
context = get_redirect_context(request)
if context:
    original_url = context['original_url']
    # Redirect user back
```

---

#### `clear_redirect_context(request) -> None`

**Purpose**: Remove redirect context from session after use

**Parameters**:
- `request` (HTTPRequest): Zope request object

**Side Effects**:
- Deletes session key `c2.pas.aal2.admin_redirect_url`

**Example**:
```python
clear_redirect_context(request)
# Session key removed
```

---

### 3. Event Subscriber (`admin/subscriber.py`)

#### `check_admin_aal2_subscriber(event: IPubBeforeCommit) -> None`

**Purpose**: Zope event subscriber that intercepts admin requests

**Event**: `zope.publisher.interfaces.IPubBeforeCommit`

**Behavior**:
1. Extract request and user from event
2. Check if URL is protected
3. If protected, check AAL2 validity
4. If invalid, store redirect context and raise `Redirect` exception

**Registration** (configure.zcml):
```xml
<subscriber
    for="zope.publisher.interfaces.IPubBeforeCommit"
    handler=".subscriber.check_admin_aal2_subscriber"
/>
```

**No Return Value**: Side effects only (may raise `Redirect`)

---

### 4. Challenge View (`browser/views.py`)

#### `class AdminAAL2ChallengeView(BrowserView)`

**Purpose**: Browser view for admin AAL2 re-authentication challenge

**URL**: `@@admin-aal2-challenge`

**Template**: `browser/templates/admin_aal2_challenge.pt`

**Methods**:

##### `__call__() -> str`

Renders challenge page with context:
```python
{
    'original_url': str,           # Where user was going
    'challenge_count': int,         # Attempt number
    'passkey_challenge_options': dict,  # WebAuthn challenge
}
```

##### `handle_authentication() -> HTTPRedirect`

POST handler for passkey authentication:
- Validates passkey assertion
- Updates AAL2 timestamp (via `session.set_aal2_timestamp()`)
- Redirects to original URL on success
- Shows error message on failure

**Request Parameters**:
```python
# POST /Plone/@@admin-aal2-challenge
{
    'passkey_response': str,  # Base64-encoded WebAuthn assertion
}
```

**Response**:
- Success: HTTP 302 redirect to original URL
- Failure: HTTP 200 with error message in template

---

### 5. Status Viewlet (`browser/viewlets.py`)

#### `class AdminAAL2StatusViewlet(ViewletBase)`

**Purpose**: Display current AAL2 status in admin interface

**Manager**: `plone.portalheader`

**Template**: `browser/templates/admin_aal2_status.pt`

**Methods**:

##### `aal2_info() -> dict`

Returns AAL2 status for current user:
```python
{
    'valid': bool,              # Is AAL2 currently valid?
    'expires_at': datetime,     # When does it expire?
    'remaining_seconds': int,   # Seconds until expiry
    'warning': bool,            # Should show warning? (<2 minutes)
}
```

**Example**:
```python
# In template:
${viewlet/aal2_info/remaining_seconds}  # "523"
${viewlet/aal2_info/warning}             # False
```

---

## Registry Records (Configuration API)

### `c2.pas.aal2.admin.protected_patterns`

**Type**: `List[TextLine]`

**Description**: URL patterns requiring AAL2 authentication

**Access**:
```python
from plone import api

# Read
patterns = api.portal.get_registry_record(
    'c2.pas.aal2.admin.protected_patterns'
)

# Write (control panel only)
api.portal.set_registry_record(
    'c2.pas.aal2.admin.protected_patterns',
    ['*/@@overview-controlpanel', '*/manage_*']
)
```

**Validation**:
- Must be list of strings
- Each string must contain at least one `/`
- Maximum 100 entries

---

### `c2.pas.aal2.admin.enabled`

**Type**: `Bool`

**Description**: Global enable/disable for admin AAL2 protection

**Access**:
```python
from plone import api

# Read
enabled = api.portal.get_registry_record('c2.pas.aal2.admin.enabled')

# Write
api.portal.set_registry_record('c2.pas.aal2.admin.enabled', False)
```

---

## Session Data Format

### `request.SESSION['c2.pas.aal2.admin_redirect_url']`

**Type**: `dict`

**Structure**:
```python
{
    'original_url': str,        # Full URL including query string
    'timestamp': float,         # Unix timestamp (time.time())
    'challenge_count': int,     # Number of challenge attempts
}
```

**Lifecycle**:
1. Created when protected URL accessed with expired AAL2
2. Read by challenge view to display context
3. Updated (challenge_count++) on failed authentication
4. Deleted after successful authentication or 5-minute expiry

**Access**:
- **Write**: `store_redirect_context()`
- **Read**: `get_redirect_context()`
- **Delete**: `clear_redirect_context()`

---

## Integration with Feature 003 (AAL2 Compliance)

### `session.is_aal2_valid(user) -> bool`

**Existing API from 003** - consumed by this feature

**Purpose**: Check if user's AAL2 authentication is still valid (< 15 minutes old)

**Usage**:
```python
from c2.pas.aal2.session import is_aal2_valid

if not is_aal2_valid(user):
    # Trigger challenge
```

---

### `session.set_aal2_timestamp(user) -> None`

**Existing API from 003** - called by this feature after successful challenge

**Purpose**: Update user's AAL2 timestamp to current time

**Usage**:
```python
from c2.pas.aal2.session import set_aal2_timestamp

# After successful passkey authentication
set_aal2_timestamp(user)
```

---

## Integration with Feature 002 (Passkey Login)

### WebAuthn Challenge Generation

**Existing API from 002** - reused for admin challenge

**Usage**:
```python
from c2.pas.aal2.utils.webauthn import create_authentication_options

# Generate challenge for admin re-auth
options = create_authentication_options(user)
```

---

### WebAuthn Assertion Verification

**Existing API from 002** - reused for admin challenge

**Usage**:
```python
from c2.pas.aal2.utils.webauthn import verify_authentication

# Verify passkey response
result = verify_authentication(user, passkey_response)
if result['verified']:
    # Update AAL2 timestamp
```

---

## Error Handling Contracts

### Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `aal2_expired` | AAL2 timestamp > 15 minutes old | Redirect to challenge |
| `not_protected` | URL doesn't match protected patterns | Allow access |
| `aal2_valid` | AAL2 timestamp < 15 minutes old | Allow access |
| `challenge_loop` | >3 challenge attempts | Clear session, redirect to home |
| `redirect_expired` | Redirect context > 5 minutes old | Clear session, redirect to home |
| `invalid_redirect` | Redirect URL not same-origin | Clear session, log warning |

---

## Audit Log Events

### Event Types

#### `admin_access_allowed`

**When**: Protected admin URL accessed with valid AAL2

**Fields**:
```python
{
    'event_type': 'admin_access_allowed',
    'timestamp': datetime,
    'user_id': str,
    'admin_url': str,
    'aal2_valid': True,
    'ip_address': str,
}
```

---

#### `admin_access_challenged`

**When**: Protected admin URL accessed with expired AAL2

**Fields**:
```python
{
    'event_type': 'admin_access_challenged',
    'timestamp': datetime,
    'user_id': str,
    'admin_url': str,
    'aal2_valid': False,
    'ip_address': str,
}
```

---

#### `admin_challenge_success`

**When**: User successfully completes admin AAL2 challenge

**Fields**:
```python
{
    'event_type': 'admin_challenge_success',
    'timestamp': datetime,
    'user_id': str,
    'original_url': str,
    'challenge_count': int,
    'ip_address': str,
}
```

---

#### `admin_challenge_failure`

**When**: User fails or cancels admin AAL2 challenge

**Fields**:
```python
{
    'event_type': 'admin_challenge_failure',
    'timestamp': datetime,
    'user_id': str,
    'reason': str,  # 'cancelled', 'verification_failed', etc.
    'challenge_count': int,
    'ip_address': str,
}
```

---

## Testing Contracts

### Mock Interfaces

```python
class MockRequest:
    """Mock Zope request for testing."""
    URL = 'http://localhost/Plone/@@overview-controlpanel'
    SESSION = {}

class MockUser:
    """Mock Plone user for testing."""
    id = 'test-user'
    def getId(self):
        return self.id

class MockRegistry:
    """Mock plone.app.registry for testing."""
    records = {
        'c2.pas.aal2.admin.protected_patterns': ['*/@@test-page'],
        'c2.pas.aal2.admin.enabled': True,
    }
```

---

## Summary

This feature provides:

1. **Internal Python APIs**: URL matching, access checking, session management
2. **Registry Configuration**: Persistent settings for protected patterns
3. **Browser Views**: Challenge page and status display
4. **Event Subscribers**: Automatic request interception
5. **Audit Events**: Comprehensive logging of admin access

All APIs integrate cleanly with existing features 002 (passkey auth) and 003 (AAL2 session management), reusing infrastructure rather than duplicating it.
