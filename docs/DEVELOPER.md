# Developer Guide - Passkey Authentication

This guide covers the API, architecture, extension points, and customization options for developers.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Storage Layer](#storage-layer)
- [PAS Plugin](#pas-plugin)
- [Browser Views](#browser-views)
- [WebAuthn Utilities](#webauthn-utilities)
- [Extension Points](#extension-points)
- [Testing](#testing)
- [API Reference](#api-reference)

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser / Client                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  register_     │  │  login_with_   │  │  manage_       │ │
│  │  passkey.pt    │  │  passkey.pt    │  │  passkeys.pt   │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘ │
│           │                   │                   │          │
│           │  WebAuthn API     │                   │          │
│           │  (navigator.      │                   │          │
│           │   credentials)    │                   │          │
└───────────┼───────────────────┼───────────────────┼──────────┘
            │                   │                   │
            ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      Browser Views (Zope)                     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  Passkey       │  │  Passkey       │  │  Passkey       │ │
│  │  Register      │  │  Login         │  │  Management    │ │
│  │  Views         │  │  Views         │  │  Views         │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘ │
└───────────┼───────────────────┼───────────────────┼──────────┘
            │                   │                   │
            ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     PAS Plugin (AAL2Plugin)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • IExtractionPlugin (extract credentials)           │   │
│  │  • IAuthenticationPlugin (validate credentials)      │   │
│  │  • generateRegistrationOptions()                     │   │
│  │  • verifyRegistrationResponse()                      │   │
│  │  • generateAuthenticationOptions()                   │   │
│  │  • verifyAuthenticationResponse()                    │   │
│  └──────────────────────────┬───────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebAuthn Utilities                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • create_registration_options()                     │   │
│  │  • verify_registration()                             │   │
│  │  • create_authentication_options()                   │   │
│  │  • verify_authentication()                           │   │
│  │  • validate_sign_count()                             │   │
│  └──────────────────────────┬───────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer (ZODB)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  User Annotations (IAnnotations)                     │   │
│  │  'c2.pas.aal2.passkeys' → PersistentDict            │   │
│  │  {                                                    │   │
│  │    'credential_id_b64': {                            │   │
│  │      'credential_id': bytes,                         │   │
│  │      'public_key': bytes,                            │   │
│  │      'sign_count': int,                              │   │
│  │      'device_name': str,                             │   │
│  │      'created': datetime,                            │   │
│  │      'last_used': datetime                           │   │
│  │    }                                                  │   │
│  │  }                                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

#### Registration Flow

```
1. User clicks "Register Passkey" → PasskeyRegisterFormView
2. JavaScript calls @@passkey-register-options
3. PasskeyRegisterOptionsView:
   - Calls plugin.generateRegistrationOptions()
   - Generates challenge (stored in session)
   - Returns PublicKeyCredentialCreationOptions
4. Browser calls navigator.credentials.create()
5. User interacts with authenticator (Touch ID, etc.)
6. JavaScript posts credential to @@passkey-register-verify
7. PasskeyRegisterVerifyView:
   - Calls plugin.verifyRegistrationResponse()
   - Validates attestation
   - Stores credential in user annotations
   - Returns success
```

#### Authentication Flow

```
1. User clicks "Sign in with Passkey" → PasskeyLoginFormView
2. JavaScript calls @@passkey-login-options
3. PasskeyLoginOptionsView:
   - Calls plugin.generateAuthenticationOptions()
   - Generates challenge (stored in session)
   - Returns PublicKeyCredentialRequestOptions
4. Browser calls navigator.credentials.get()
5. User interacts with authenticator
6. JavaScript posts assertion to @@passkey-login-verify
7. PasskeyLoginVerifyView:
   - Calls plugin.verifyAuthenticationResponse()
   - Validates signature
   - Updates sign count
   - Creates authenticated session
   - Returns success + redirect
```

## Storage Layer

### Location

`src/c2/pas/aal2/credential.py`

### Data Model

Passkeys are stored as ZODB annotations on user objects:

```python
from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict

# Annotation key
PASSKEY_ANNOTATION_KEY = "c2.pas.aal2.passkeys"

# Structure
{
    'credential_id_b64': PersistentDict({
        'credential_id': bytes,      # Raw credential ID
        'public_key': bytes,          # COSE public key
        'sign_count': int,            # Replay attack counter
        'aaguid': bytes,              # Authenticator GUID
        'device_name': str,           # User-assigned name
        'device_type': str,           # 'platform' or 'cross-platform'
        'created': datetime,          # Registration timestamp
        'last_used': datetime,        # Last authentication timestamp
        'transports': list,           # ['usb', 'nfc', 'ble', 'internal']
    })
}
```

### Storage API

```python
from c2.pas.aal2.credential import (
    get_user_passkeys,     # Get all passkeys for user
    add_passkey,           # Add new passkey
    get_passkey,           # Get specific passkey
    update_passkey_last_used,  # Update last used + sign count
    delete_passkey,        # Remove passkey
    count_passkeys,        # Count user's passkeys
)

# Example: Add a passkey
from plone import api

user = api.user.get(username='john')
credential_data = {
    'credential_id': b'...',
    'public_key': b'...',
    'sign_count': 0,
    'device_name': 'iPhone 14',
    'device_type': 'platform',
    'transports': ['internal'],
}
credential_id_b64 = add_passkey(user, credential_data)

# Example: Retrieve passkey
passkey = get_passkey(user, credential_id_b64)
print(passkey['device_name'])  # 'iPhone 14'

# Example: Update after authentication
update_passkey_last_used(user, credential_id_b64, new_sign_count=1)

# Example: Delete passkey
success = delete_passkey(user, credential_id_b64)
```

### Why ZODB Annotations?

- **Persistent**: Survives server restarts
- **Per-User**: Isolated storage per user object
- **Transactional**: ACID guarantees
- **Flexible**: Schema can evolve
- **Standard**: Plone convention for user metadata

## PAS Plugin

### Location

`src/c2/pas/aal2/plugin.py`

### Class: AAL2Plugin

```python
class AAL2Plugin(BasePlugin):
    """PAS plugin for WebAuthn passkey authentication."""

    meta_type = 'AAL2 Passkey Authentication Plugin'

    # Implements:
    # - Products.PluggableAuthService.interfaces.plugins.IExtractionPlugin
    # - Products.PluggableAuthService.interfaces.plugins.IAuthenticationPlugin
```

### Key Methods

#### generateRegistrationOptions

```python
def generateRegistrationOptions(
    self, request, user,
    device_name=None,
    authenticator_attachment=None
):
    """
    Generate WebAuthn registration options.

    Args:
        request: Zope request object
        user: Plone user object
        device_name: Optional device name
        authenticator_attachment: 'platform' or 'cross-platform'

    Returns:
        PublicKeyCredentialCreationOptions

    Side Effects:
        - Stores challenge in session
        - Logs registration start event
    """
```

#### verifyRegistrationResponse

```python
def verifyRegistrationResponse(self, request, user, credential_response):
    """
    Verify and store registration response.

    Args:
        request: Zope request object
        user: Plone user object
        credential_response: Credential from browser

    Returns:
        dict: {'success': True, 'credential_id': '...'}

    Raises:
        ValueError: If verification fails

    Side Effects:
        - Stores credential in user annotations
        - Updates session
        - Logs registration success/failure
    """
```

#### generateAuthenticationOptions

```python
def generateAuthenticationOptions(self, request, username=None):
    """
    Generate WebAuthn authentication options.

    Args:
        request: Zope request object
        username: Optional username to filter credentials

    Returns:
        PublicKeyCredentialRequestOptions

    Side Effects:
        - Stores challenge in session
        - Logs authentication start event
    """
```

#### verifyAuthenticationResponse

```python
def verifyAuthenticationResponse(
    self, request, credential_response, username=None
):
    """
    Verify authentication response and authenticate user.

    Args:
        request: Zope request object
        credential_response: Assertion from browser
        username: Optional username hint

    Returns:
        dict: {'success': True, 'user_id': '...'}

    Raises:
        ValueError: If verification fails

    Side Effects:
        - Updates sign count
        - Updates last_used timestamp
        - Logs authentication success/failure
    """
```

### PAS Interface Implementation

#### IExtractionPlugin.extractCredentials

```python
def extractCredentials(self, request):
    """
    Extract passkey credentials from request.

    Called by PAS during authentication chain.

    Returns:
        dict or None: Credentials if passkey auth attempt detected
    """
    # Check for passkey auth markers in request
    if request.get('__passkey_auth_attempt'):
        return {
            'login': request.get('__passkey_username'),
            'password': '',  # Not used for passkeys
            'passkey_credential': request.get('__passkey_credential'),
        }
    return None
```

#### IAuthenticationPlugin.authenticateCredentials

```python
def authenticateCredentials(self, credentials):
    """
    Authenticate credentials extracted by extractCredentials.

    Called by PAS after credential extraction.

    Returns:
        tuple or None: (user_id, login) if valid, None otherwise
    """
    if 'passkey_credential' in credentials:
        # Passkey authentication already verified in verify view
        # Just return user_id
        return (credentials['login'], credentials['login'])
    return None
```

## Browser Views

### Locations

- Views: `src/c2/pas/aal2/browser/views.py`
- Templates: `src/c2/pas/aal2/browser/templates/*.pt`
- Configuration: `src/c2/pas/aal2/browser/configure.zcml`

### Registration Views

```python
class PasskeyRegisterOptionsView(BrowserView):
    """Generate registration options (@@passkey-register-options)."""

class PasskeyRegisterVerifyView(BrowserView):
    """Verify registration response (@@passkey-register-verify)."""

class PasskeyRegisterFormView(BrowserView):
    """Render registration form (@@passkey-register-form)."""
```

### Login Views

```python
class PasskeyLoginOptionsView(BrowserView):
    """Generate authentication options (@@passkey-login-options)."""

class PasskeyLoginVerifyView(BrowserView):
    """Verify authentication response (@@passkey-login-verify)."""

class PasskeyLoginFormView(BrowserView):
    """Render login form (@@passkey-login-form)."""
```

### Management Views

```python
class PasskeyListView(BrowserView):
    """List user's passkeys (@@passkey-list)."""

class PasskeyDeleteView(BrowserView):
    """Delete passkey (@@passkey-delete)."""

class PasskeyUpdateView(BrowserView):
    """Update passkey metadata (@@passkey-update)."""

class PasskeyManageView(BrowserView):
    """Render management interface (@@passkey-manage)."""
```

### Adding Custom Views

```xml
<!-- In your package's browser/configure.zcml -->
<browser:page
    name="my-custom-passkey-view"
    for="*"
    class=".views.MyCustomPasskeyView"
    permission="zope2.View"
    />
```

```python
# In your views.py
from c2.pas.aal2.credential import get_user_passkeys
from Products.Five.browser import BrowserView
from plone import api

class MyCustomPasskeyView(BrowserView):
    def __call__(self):
        user = api.user.get_current()
        passkeys = get_user_passkeys(user)

        # Custom logic here
        return self.index()  # Render template
```

## WebAuthn Utilities

### Location

`src/c2/pas/aal2/utils/webauthn.py`

### Functions

```python
from c2.pas.aal2.utils.webauthn import (
    create_registration_options,
    verify_registration,
    create_authentication_options,
    verify_authentication,
    validate_sign_count,
)
```

#### create_registration_options

```python
def create_registration_options(
    user_id: str,
    username: str,
    display_name: str,
    rp_id: str,
    rp_name: str,
    exclude_credentials: list = None,
    authenticator_attachment: str = None
) -> PublicKeyCredentialCreationOptions:
    """
    Wrapper around webauthn.generate_registration_options.

    Args:
        user_id: Unique user identifier (opaque to authenticator)
        username: Username for display
        display_name: Human-readable name
        rp_id: Relying Party ID (domain)
        rp_name: Relying Party name
        exclude_credentials: List of existing credentials to exclude
        authenticator_attachment: 'platform' or 'cross-platform'

    Returns:
        Registration options for navigator.credentials.create()
    """
```

#### verify_registration

```python
def verify_registration(
    credential: dict,
    expected_challenge: bytes,
    expected_origin: str,
    expected_rp_id: str
) -> VerifiedRegistration:
    """
    Wrapper around webauthn.verify_registration_response.

    Args:
        credential: Credential from browser
        expected_challenge: Challenge from session
        expected_origin: Expected origin (portal URL)
        expected_rp_id: Expected RP ID (domain)

    Returns:
        VerifiedRegistration with credential_id, public_key, etc.

    Raises:
        InvalidRegistrationResponse: If verification fails
    """
```

### Customizing WebAuthn Behavior

```python
# Override timeout
def create_registration_options(...):
    options = generate_registration_options(
        # ...
        timeout=120000,  # 2 minutes instead of default 5
    )
    return options

# Require user verification (PIN/biometric)
def create_authentication_options(...):
    options = generate_authentication_options(
        # ...
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return options

# Change attestation preference
def create_registration_options(...):
    options = generate_registration_options(
        # ...
        attestation=AttestationConveyancePreference.DIRECT,  # Request attestation
    )
    return options
```

## Extension Points

### Custom Storage Backend

Replace ZODB annotations with custom storage:

```python
# mypackage/storage.py
class RedisPasskeyStorage:
    """Store passkeys in Redis instead of ZODB."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def add_passkey(self, user_id, credential_data):
        key = f"passkeys:{user_id}:{credential_data['credential_id']}"
        self.redis.setex(key, 86400*365, json.dumps(credential_data))

    def get_passkey(self, user_id, credential_id):
        key = f"passkeys:{user_id}:{credential_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None

# Then monkey-patch or replace imports
import c2.pas.aal2.credential as cred_module
cred_module.add_passkey = RedisPasskeyStorage().add_passkey
# ... etc
```

### Custom Audit Logging

Send audit events to external system:

```python
# mypackage/audit.py
from c2.pas.aal2.utils import audit as audit_module

original_log_event = audit_module.log_event

def custom_log_event(event_type, user_id, success, **kwargs):
    # Call original
    original_log_event(event_type, user_id, success, **kwargs)

    # Send to external SIEM
    import requests
    requests.post('https://siem.example.com/events', json={
        'event_type': event_type,
        'user_id': user_id,
        'success': success,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    })

# Monkey-patch
audit_module.log_event = custom_log_event
```

### Custom Challenge Storage

Use Redis for challenges instead of Plone sessions:

```python
# mypackage/challenges.py
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def store_challenge(session_id, challenge, ttl=300):
    """Store challenge in Redis with TTL."""
    redis_client.setex(f"challenge:{session_id}", ttl, challenge)

def get_challenge(session_id):
    """Retrieve challenge from Redis."""
    return redis_client.get(f"challenge:{session_id}")

# Replace session storage in plugin.py
def generateRegistrationOptions(self, request, user, ...):
    # ...
    challenge = options.challenge
    session_id = generate_session_id()
    store_challenge(session_id, challenge)
    # Return session_id to client
```

### Pre/Post Hooks

Add custom logic before/after passkey operations:

```python
# mypackage/hooks.py
from zope.component import adapter
from zope.interface import Interface, implementer

class IPasskeyRegistered(Interface):
    """Event: Passkey registered."""

class IPasskeyDeleted(Interface):
    """Event: Passkey deleted."""

@adapter(IPasskeyRegistered)
def on_passkey_registered(event):
    """Send welcome email when user registers first passkey."""
    user = event.user
    if count_passkeys(user) == 1:
        send_email(user, subject="Welcome to Passkey Authentication!")

# Register in configure.zcml
<subscriber handler=".hooks.on_passkey_registered" />
```

## Testing

### Unit Tests

```python
# tests/test_credential.py
import unittest
from c2.pas.aal2.credential import add_passkey, get_passkey
from plone.app.testing import TEST_USER_ID

class TestCredentialStorage(unittest.TestCase):

    def test_add_passkey(self):
        user = self.portal.acl_users.getUserById(TEST_USER_ID)
        credential_data = {
            'credential_id': b'test123',
            'public_key': b'pubkey',
            'sign_count': 0,
            'device_name': 'Test Device',
        }

        cred_id = add_passkey(user, credential_data)
        self.assertIsNotNone(cred_id)

        # Retrieve and verify
        passkey = get_passkey(user, cred_id)
        self.assertEqual(passkey['device_name'], 'Test Device')
```

### Integration Tests

```python
# tests/test_views.py
import json
from plone.app.testing import SITE_OWNER_NAME

class TestPasskeyViews(unittest.TestCase):

    def test_register_options_view(self):
        self.portal.acl_users._doAddUser('testuser', 'secret', [], [])

        # Login
        self.request.form['__ac_name'] = 'testuser'
        self.request.form['__ac_password'] = 'secret'

        # Call view
        view = self.portal.restrictedTraverse('@@passkey-register-options')
        result = json.loads(view())

        self.assertIn('publicKey', result)
        self.assertIn('challenge', result['publicKey'])
```

### Mock WebAuthn

For testing without real authenticators:

```python
# tests/mocks.py
class MockAuthenticator:
    """Mock WebAuthn authenticator for testing."""

    def create_credential(self, options):
        """Simulate credential creation."""
        return {
            'id': 'mock_credential_id',
            'rawId': 'mock_credential_id',
            'response': {
                'attestationObject': b'mock_attestation',
                'clientDataJSON': b'{"type":"webauthn.create"}',
            },
            'type': 'public-key',
        }

    def get_assertion(self, options):
        """Simulate authentication."""
        return {
            'id': 'mock_credential_id',
            'response': {
                'authenticatorData': b'mock_auth_data',
                'clientDataJSON': b'{"type":"webauthn.get"}',
                'signature': b'mock_signature',
            },
        }
```

## API Reference

### Storage Functions

| Function | Args | Returns | Description |
|----------|------|---------|-------------|
| `get_user_passkeys(user)` | user: User object | dict | All passkeys for user |
| `add_passkey(user, credential_data)` | user, dict | str (cred_id) | Add new passkey |
| `get_passkey(user, credential_id)` | user, str | dict or None | Get specific passkey |
| `update_passkey_last_used(user, cred_id, sign_count)` | user, str, int | None | Update metadata |
| `delete_passkey(user, credential_id)` | user, str | bool | Remove passkey |
| `count_passkeys(user)` | user | int | Count user's passkeys |

### WebAuthn Functions

| Function | Args | Returns | Description |
|----------|------|---------|-------------|
| `create_registration_options(...)` | user_id, username, rp_id, etc. | PublicKeyCredentialCreationOptions | Generate reg options |
| `verify_registration(...)` | credential, challenge, origin, rp_id | VerifiedRegistration | Verify attestation |
| `create_authentication_options(...)` | rp_id, allow_credentials | PublicKeyCredentialRequestOptions | Generate auth options |
| `verify_authentication(...)` | credential, challenge, public_key, etc. | VerifiedAuthentication | Verify assertion |
| `validate_sign_count(...)` | stored, received | bool | Check replay attack |

### Audit Functions

| Function | Args | Returns | Description |
|----------|------|---------|-------------|
| `log_event(type, user_id, success, ...)` | str, str, bool, kwargs | dict | Log audit event |
| `log_registration_start(user_id, request)` | str, request | dict | Log registration start |
| `log_registration_success(user_id, cred_id, request)` | str, str, request | dict | Log reg success |
| `log_authentication_success(user_id, cred_id, request)` | str, str, request | dict | Log auth success |
| `log_credential_deleted(user_id, cred_id, request)` | str, str, request | dict | Log deletion |

## Contributing

To contribute to this package:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

## License

GPLv2 - See [LICENSE](../LICENSE) for full text.
