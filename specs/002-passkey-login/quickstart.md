# Quickstart: Passkey Authentication for Plone Login

**Branch**: `002-passkey-login` | **Date**: 2025-11-06
**Purpose**: Developer onboarding guide for implementing passkey authentication

## Overview

This guide helps developers get started with implementing the c2.pas.aal2 passkey authentication package for Plone. It covers setup, basic usage, and common development tasks.

## Prerequisites

Before starting, ensure you have:

- Python 3.11 or later
- Plone 5.2 or later installed
- HTTPS-enabled development environment (or localhost for testing)
- Modern browser with WebAuthn support (Chrome 67+, Firefox 60+, Safari 13+, Edge 18+)
- Git for version control
- Basic understanding of Plone PAS (Pluggable Authentication Service)

## Project Structure

```
workspace/
├── src/
│   └── c2/
│       └── pas/
│           └── aal2/
│               ├── __init__.py
│               ├── plugin.py              # PAS plugin
│               ├── credential.py          # Data models
│               ├── browser/               # UI views
│               ├── utils/                 # WebAuthn helpers
│               └── profiles/              # GenericSetup
├── tests/
│   ├── test_plugin.py
│   ├── test_credential.py
│   ├── test_webauthn.py
│   └── test_views.py
├── docs/
├── setup.py
└── README.md
```

## Quick Setup (5 Minutes)

### 1. Install Dependencies

```bash
# Create and activate virtual environment
cd /workspace
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
pip install -e .

# Install test dependencies
pip install -e ".[test]"
```

### 2. Configure Plone Site

```bash
# Start Plone instance (if not already running)
./bin/instance fg

# Access ZMI: http://localhost:8080/manage
# Navigate to acl_users (PAS)
# Activate the "WebAuthn Passkey Authentication" plugin
```

### 3. Verify Installation

```bash
# Run tests
pytest tests/

# Check plugin is registered
python -c "from c2.pas.aal2.plugin import PasskeyAuthPlugin; print('OK')"
```

## Development Workflow

### Phase 1: Understand the Architecture

```
Browser                     Plone Server
   │                             │
   │  1. POST /@@passkey-        │
   │     register-options        │
   ├────────────────────────────>│
   │                             │ PasskeyAuthPlugin
   │  2. PublicKeyCredential     │   .generateRegistrationOptions()
   │     CreationOptions          │
   │<────────────────────────────┤
   │                             │
   │  3. navigator.credentials   │
   │     .create()               │
   │  (User authenticates)       │
   │                             │
   │  4. POST /@@passkey-        │
   │     register-verify         │
   │     + AttestationResponse   │
   ├────────────────────────────>│
   │                             │ PasskeyAuthPlugin
   │  5. Success response        │   .verifyRegistration()
   │<────────────────────────────┤   → Store in ZODB
   │                             │
```

### Phase 2: Core Components

#### 1. PAS Plugin (`plugin.py`)

The main plugin implements PAS interfaces:

```python
from Products.PluggableAuthService.interfaces.plugins import (
    IAuthenticationPlugin,
    IExtractionPlugin,
)

class PasskeyAuthPlugin(BasePlugin):
    """WebAuthn passkey authentication plugin for Plone PAS."""

    meta_type = 'WebAuthn Passkey Authentication Plugin'

    # IExtractionPlugin
    def extractCredentials(self, request):
        """Extract passkey assertion from request."""
        # Check for WebAuthn assertion in POST data
        # Return credentials dict or empty dict

    # IAuthenticationPlugin
    def authenticateCredentials(self, credentials):
        """Validate passkey assertion against stored credentials."""
        # Verify signature using py_webauthn
        # Return (user_id, login) or None
```

**Key Methods**:
- `generateRegistrationOptions(user)`: Create options for registration ceremony
- `verifyRegistrationResponse(user, response)`: Validate and store new credential
- `generateAuthenticationOptions(username)`: Create options for auth ceremony
- `verifyAuthenticationResponse(response)`: Validate assertion and authenticate

#### 2. Credential Storage (`credential.py`)

Helper functions for ZODB annotations:

```python
def add_passkey(user, credential_data):
    """Add a new passkey to user's annotations."""
    annotations = IAnnotations(user)
    passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

    credential_id_b64 = base64url_encode(credential_data['credential_id'])
    passkeys[credential_id_b64] = PersistentDict(credential_data)

    annotations[PASSKEY_ANNOTATION_KEY] = passkeys
    user._p_changed = True
    return credential_id_b64
```

#### 3. Browser Views (`browser/views.py`)

View classes for UI:

```python
class PasskeyRegisterOptionsView(BrowserView):
    """Generate registration options for authenticated user."""

    def __call__(self):
        plugin = self._get_plugin()
        user = api.user.get_current()

        options = plugin.generateRegistrationOptions(user)

        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(options)
```

#### 4. WebAuthn Utilities (`utils/webauthn.py`)

Wrapper around py_webauthn:

```python
from webauthn import (
    generate_registration_options,
    verify_registration_response,
)

def create_registration_options(user, rp_id, rp_name):
    """Generate WebAuthn registration options."""
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=user.getId().encode('utf-8'),
        user_name=user.getProperty('email'),
        user_display_name=user.getProperty('fullname'),
    )
    return options
```

### Phase 3: Implement User Stories

#### Story P1: Register Passkey

1. **Backend** (`browser/views.py`):
   ```python
   class PasskeyRegisterOptionsView(BrowserView):
       def __call__(self):
           # Generate options
           # Store challenge in session
           # Return JSON response
   ```

2. **Frontend** (TAL template + JS):
   ```javascript
   async function registerPasskey() {
       const options = await fetch('/@@passkey-register-options', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' }
       }).then(r => r.json());

       // Decode base64url fields
       options.publicKey.challenge = base64urlDecode(options.publicKey.challenge);
       options.publicKey.user.id = base64urlDecode(options.publicKey.user.id);

       // Call WebAuthn API
       const credential = await navigator.credentials.create({
           publicKey: options.publicKey
       });

       // Send to server
       await fetch('/@@passkey-register-verify', {
           method: 'POST',
           body: JSON.stringify({ credential: encodeCredential(credential) })
       });
   }
   ```

3. **Tests** (`test_views.py`):
   ```python
   def test_register_options_requires_auth(self):
       response = self.portal.restrictedTraverse('@@passkey-register-options')()
       self.assertEqual(response.status, 401)

   def test_register_options_generates_challenge(self):
       login(self.portal, 'testuser')
       response = self.portal.restrictedTraverse('@@passkey-register-options')()
       data = json.loads(response)
       self.assertIn('publicKey', data)
       self.assertIn('challenge', data['publicKey'])
   ```

#### Story P2: Login with Passkey

Similar structure: options view → frontend JS → verify view → tests

#### Story P3: Manage Passkeys

List view + delete action + update action

### Phase 4: Testing Strategy

#### Unit Tests

```bash
# Test individual functions
pytest tests/test_credential.py -v

# Test WebAuthn helpers
pytest tests/test_webauthn.py -v
```

Example:
```python
def test_add_passkey(self):
    user = self.portal.acl_users.getUser('testuser')
    credential_data = {
        'credential_id': b'test_credential',
        'public_key': b'test_public_key',
        'sign_count': 0,
    }

    credential_id = add_passkey(user, credential_data)

    passkeys = get_user_passkeys(user)
    self.assertEqual(len(passkeys), 1)
    self.assertIn(credential_id, passkeys)
```

#### Integration Tests

```bash
# Test full registration flow
pytest tests/test_integration.py::test_full_registration_flow -v

# Test full authentication flow
pytest tests/test_integration.py::test_full_authentication_flow -v
```

Example:
```python
def test_full_registration_flow(self):
    # 1. Get options
    options_view = self.portal.restrictedTraverse('@@passkey-register-options')
    options = json.loads(options_view())

    # 2. Simulate browser response (use fido2 virtual authenticator)
    from fido2.server import Fido2Server
    server = Fido2Server(...)
    credential = create_mock_credential(options)

    # 3. Verify response
    verify_view = self.portal.restrictedTraverse('@@passkey-register-verify')
    result = json.loads(verify_view(credential=credential))

    self.assertTrue(result['success'])
```

#### Browser Tests (Optional)

Use Playwright for E2E tests:

```python
# tests/e2e/test_passkey_registration.py
def test_register_passkey_ui(page):
    page.goto('http://localhost:8080/plone')
    page.click('text=My Profile')
    page.click('text=Add Passkey')

    # Browser handles WebAuthn ceremony
    page.wait_for_selector('text=Passkey registered successfully')
```

## Common Development Tasks

### Add a New View

1. Create view class in `browser/views.py`:
   ```python
   class MyNewView(BrowserView):
       def __call__(self):
           return "Hello World"
   ```

2. Register in `browser/configure.zcml`:
   ```xml
   <browser:page
       name="my-new-view"
       for="*"
       class=".views.MyNewView"
       permission="zope2.View"
       />
   ```

3. Add tests in `tests/test_views.py`

### Modify Data Model

1. Update `credential.py` with new field
2. Add migration function for existing data
3. Create GenericSetup upgrade step
4. Update tests

### Debug WebAuthn Issues

```python
# Add logging to plugin
import logging
logger = logging.getLogger('c2.pas.aal2')

def verifyAuthenticationResponse(self, response):
    logger.info(f"Verifying assertion for credential {response['id']}")
    try:
        # ... verification code
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        raise
```

View logs:
```bash
tail -f var/log/instance.log | grep c2.pas.aal2
```

### Test with Virtual Authenticator

Chrome DevTools Protocol:

```javascript
// Enable virtual authenticator
const authenticatorId = await fetch('http://localhost:9222/json/new').then(r => r.json());

// Add credential
await fetch(`http://localhost:9222/webauthn/addCredential`, {
    method: 'POST',
    body: JSON.stringify({
        authenticatorId,
        credential: { ... }
    })
});
```

## Configuration

### GenericSetup Profile

File: `profiles/default/pas_plugins.xml`

```xml
<?xml version="1.0"?>
<pluggable-authentication-service>
  <plugins>
    <plugin id="passkey_auth"
            type="WebAuthn Passkey Authentication Plugin"
            interface="IAuthenticationPlugin"
            interface="IExtractionPlugin" />
  </plugins>
</pluggable-authentication-service>
```

### Site Configuration

Control panel settings (future enhancement):

```python
# registry.xml
<record name="c2.pas.aal2.settings.rp_name">
    <field type="plone.registry.field.TextLine">
        <title>Relying Party Name</title>
    </field>
    <value>My Plone Site</value>
</record>
```

## Troubleshooting

### Issue: "PublicKeyCredential is not defined"

**Cause**: Browser doesn't support WebAuthn or page not served over HTTPS

**Solution**:
- Use HTTPS in production
- For local dev, use `localhost` (exempted from HTTPS requirement)
- Check browser compatibility

### Issue: "Challenge validation failed"

**Cause**: Challenge expired or session lost

**Solution**:
- Check session timeout settings
- Ensure challenge TTL is reasonable (5 minutes)
- Verify session cookie is being sent

### Issue: "Credential not found"

**Cause**: User deleted credential or ZODB issue

**Solution**:
- Check ZODB annotations: `user._annotations`
- Verify credential_id encoding (base64url)
- Check for ZODB packing issues

### Issue: "Sign count mismatch"

**Cause**: Potential replay attack or authenticator counter reset

**Solution**:
- Log sign count values for debugging
- Handle counter wrap (rare)
- Reject authentication and alert user

## Performance Optimization

### Challenge Generation

```python
# Use secrets module for cryptographic randomness
import secrets

def generate_challenge():
    return secrets.token_bytes(32)  # 256 bits
```

### Credential Lookup

```python
# Cache credential_id → user_id mapping
from plone.memoize import ram

@ram.cache(lambda method, self, credential_id: credential_id)
def find_user_by_credential(self, credential_id):
    # Expensive ZODB traversal
    for user_id in self.acl_users.getUserIds():
        user = self.acl_users.getUserById(user_id)
        if get_passkey(user, credential_id):
            return user
    return None
```

### Session Storage

Use RAM session for challenges (faster than ZODB):

```python
from zope.session.interfaces import ISession

def store_challenge(request, challenge):
    session = ISession(request)
    session['c2.pas.aal2']['challenge'] = challenge
```

## Security Checklist

Before deploying:

- [ ] HTTPS enabled in production
- [ ] Challenge timeout configured (5 minutes)
- [ ] Rate limiting on verification endpoints
- [ ] Audit logging enabled
- [ ] CSRF protection active
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] Session cookies use HttpOnly, Secure, SameSite
- [ ] Sign count validation enforced
- [ ] Last authentication method check (FR-016)

## Next Steps

1. **Review the spec**: Read [spec.md](./spec.md) for requirements
2. **Study the research**: See [research.md](./research.md) for technical decisions
3. **Understand data model**: Review [data-model.md](./data-model.md)
4. **Check API contracts**: See [contracts/api-endpoints.md](./contracts/api-endpoints.md)
5. **Start implementing**: Begin with P1 user story (registration)
6. **Write tests first**: Follow TDD approach
7. **Run `/speckit.tasks`**: Generate detailed implementation tasks

## Resources

### Documentation

- [Plone PAS Documentation](https://docs.plone.org/develop/plone/security/authentication.html)
- [py_webauthn Docs](https://duo-labs.github.io/py_webauthn/)
- [WebAuthn Spec Level 2](https://www.w3.org/TR/webauthn-2/)
- [MDN WebAuthn Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)

### Tools

- [webauthn.io](https://webauthn.io) - Test WebAuthn flows
- [Chrome DevTools WebAuthn](https://developer.chrome.com/docs/devtools/webauthn/)
- [pytest](https://docs.pytest.org/) - Testing framework
- [plone.app.testing](https://pypi.org/project/plone.app.testing/) - Plone test fixtures

### Community

- [Plone Community Forum](https://community.plone.org/)
- [py_webauthn GitHub](https://github.com/duo-labs/py_webauthn)
- [WebAuthn Working Group](https://www.w3.org/Webauthn/)

## Code Examples Repository

Example implementations:

```bash
# Clone examples
git clone https://github.com/duo-labs/py_webauthn.git
cd py_webauthn/examples

# Study Flask example (similar to Plone)
python flask_example.py
```

## FAQ

**Q: Can users have passkey-only accounts (no password)?**
A: Yes, but system enforces at least one authentication method (FR-016). Users must keep either a password or a passkey.

**Q: How many passkeys can a user register?**
A: Unlimited (FR-004), but practical limit is ~10-20 before UI becomes unwieldy.

**Q: Does this work with Touch ID / Face ID / Windows Hello?**
A: Yes! These are "platform authenticators" and fully supported.

**Q: What about hardware security keys (YubiKey)?**
A: Yes! These are "cross-platform authenticators" (roaming) and supported.

**Q: Can passkeys sync across devices?**
A: That's handled by the user's device ecosystem (Apple Keychain, Google Password Manager), not by Plone.

**Q: What if the user loses their passkey device?**
A: They can use password fallback to log in, then remove the lost passkey and add a new one.

## Getting Help

1. **Check the spec**: Most answers are in [spec.md](./spec.md)
2. **Review research**: Technical decisions explained in [research.md](./research.md)
3. **Search community**: [community.plone.org](https://community.plone.org)
4. **Open an issue**: GitHub issues for bugs/features
5. **Ask in chat**: Plone Discord/Matrix channels

---

**Ready to start coding?** Run `/speckit.tasks` to generate detailed implementation tasks!
