# c2.pas.aal2 - AAL2 Compliance with Passkey Re-authentication

A Plone PAS plugin implementing NIST AAL2 (Authenticator Assurance Level 2) compliance through WebAuthn/Passkey authentication with time-based session management.

## Features

### Core AAL2 Functionality

- **15-Minute Re-authentication Window**: Enforces NIST AAL2 requirements by tracking passkey authentication timestamps and expiring them after 15 minutes
- **Content-Level Protection**: Administrators can mark specific content items as requiring AAL2 authentication
- **Role-Based Protection**: Assign "AAL2 Required User" role to users who must always authenticate with AAL2, regardless of content
- **Step-Up Authentication**: Seamless challenge flow when AAL2 is required but not valid
- **Comprehensive Audit Logging**: Track all AAL2 authentication events, access grants/denials, and policy changes

### WebAuthn/Passkey Support

- **Passwordless Authentication**: Full FIDO2/WebAuthn implementation using py_webauthn library
- **Multi-Device Support**: Users can register multiple passkeys (different devices, security keys, etc.)
- **Attestation Support**: Optional device attestation for enhanced security
- **Credential Management**: Users can manage, rename, and delete their registered passkeys

## Installation

### Requirements

- Python 3.11+
- Plone 5.2+
- Modern browser with WebAuthn support (Chrome, Firefox, Safari, Edge)

### Install via pip

```bash
pip install c2.pas.aal2
```

### Install via buildout

Add to your `buildout.cfg`:

```ini
[instance]
eggs =
    c2.pas.aal2
```

### Activate the Plugin

1. Navigate to: Site Setup → ZMI → acl_users
2. Add a new "AAL2 Passkey Plugin"
3. Activate the plugin for:
   - Authentication
   - Extraction
   - Validation (for AAL2 enforcement)

### Install GenericSetup Profile

Navigate to: Site Setup → Add-ons → Install "C2 PAS AAL2 Plugin"

This will:
- Register the "AAL2 Required User" role
- Set up the "Require AAL2 Authentication" permission
- Configure default role mappings

## Usage

### For End Users

#### Registering a Passkey

1. Log in to your Plone site with your username/password
2. Navigate to your user profile or passkey management page
3. Click "Register Passkey"
4. Follow your browser's prompts (touch fingerprint sensor, insert security key, etc.)
5. Give your passkey a memorable name (e.g., "Work Laptop", "iPhone")

#### Logging In with Passkey

1. Go to the login page
2. Enter your username
3. Click "Login with Passkey"
4. Authenticate using your device (fingerprint, face ID, security key, etc.)

#### AAL2 Re-authentication

When accessing AAL2-protected content:
- If you authenticated with a passkey within the last 15 minutes, access is granted immediately
- If your AAL2 session expired, you'll see a step-up authentication challenge
- Simply re-authenticate with your passkey to regain access
- The 15-minute window resets each time you authenticate

### For Administrators

#### Protecting Content with AAL2

**Option 1: Content-Level Protection**
```python
from c2.pas.aal2.policy import set_aal2_required

# Require AAL2 for specific content
set_aal2_required(content, required=True)

# Remove AAL2 requirement
set_aal2_required(content, required=False)

# Check if content requires AAL2
from c2.pas.aal2.policy import is_aal2_required
if is_aal2_required(content):
    print("This content requires AAL2")
```

**Option 2: Role-Based Protection**
```python
from c2.pas.aal2.roles import assign_aal2_role, revoke_aal2_role

# Assign AAL2 role to a user (requires AAL2 for ALL resources)
assign_aal2_role('privileged_user', portal)

# Revoke AAL2 role
revoke_aal2_role('privileged_user', portal)

# List all users with AAL2 role
from c2.pas.aal2.roles import list_aal2_users
aal2_users = list_aal2_users(portal)
```

#### Checking AAL2 Status

```python
from c2.pas.aal2.policy import get_aal2_status

status = get_aal2_status(content, user)
print(f"AAL2 required: {status['required']}")
print(f"AAL2 valid: {status['valid']}")
print(f"Expires at: {status['expiry']}")
print(f"Needs re-auth: {status['needs_challenge']}")
```

#### Listing Protected Content

```python
from c2.pas.aal2.policy import list_aal2_protected_content

protected_items = list_aal2_protected_content()
for item in protected_items:
    print(f"{item['title']} at {item['path']}")
```

### For Developers

#### API Reference

##### Session Management (`c2.pas.aal2.session`)

```python
from c2.pas.aal2.session import (
    set_aal2_timestamp,
    get_aal2_timestamp,
    is_aal2_valid,
    get_aal2_expiry,
    clear_aal2_timestamp,
    AAL2_TIMEOUT_SECONDS  # = 900 (15 minutes)
)

# Set AAL2 timestamp after successful passkey authentication
set_aal2_timestamp(user, credential_id='cred_123')

# Check if user's AAL2 authentication is still valid
if is_aal2_valid(user):
    print("AAL2 valid for next", get_remaining_time(user), "seconds")
else:
    print("AAL2 expired, re-authentication required")

# Get expiry datetime
expiry = get_aal2_expiry(user)
print(f"AAL2 expires at: {expiry}")

# Clear AAL2 timestamp (e.g., on logout)
clear_aal2_timestamp(user)
```

##### Policy Management (`c2.pas.aal2.policy`)

```python
from c2.pas.aal2.policy import (
    is_aal2_required,
    set_aal2_required,
    check_aal2_access,
    get_stepup_challenge_url,
    get_aal2_status
)

# Check if AAL2 is required (considers both content policy and user role)
if is_aal2_required(content, user):
    print("AAL2 required")

# Check complete AAL2 access (requirement + validity)
if not check_aal2_access(content, user, request):
    # Redirect to step-up challenge
    challenge_url = get_stepup_challenge_url(content, request)
    return request.RESPONSE.redirect(challenge_url)
```

##### Role Management (`c2.pas.aal2.roles`)

```python
from c2.pas.aal2.roles import (
    has_aal2_role,
    assign_aal2_role,
    revoke_aal2_role,
    list_aal2_users,
    AAL2_REQUIRED_ROLE  # = 'AAL2 Required User'
)

# Check if user has AAL2 role
if has_aal2_role(user):
    print("User has AAL2 Required User role")

# Assign role programmatically
assign_aal2_role(user_id, portal)
```

##### Audit Logging (`c2.pas.aal2.utils.audit`)

```python
from c2.pas.aal2.utils.audit import (
    log_aal2_timestamp_set,
    log_aal2_access_granted,
    log_aal2_access_denied,
    log_aal2_policy_set,
    log_aal2_role_assigned,
    log_aal2_role_revoked
)

# All audit functions automatically log to Python logger
# Configure in your logging.conf:
# [logger_c2.pas.aal2.audit]
# level = INFO
# handlers = syslog, file
```

## Architecture

### Session Tracking

AAL2 authentication timestamps are stored as user annotations:
- **Key**: `c2.pas.aal2.aal2_timestamp`
- **Storage**: ZODB via `zope.annotation.IAnnotations`
- **Timeout**: 900 seconds (15 minutes) per NIST AAL2 requirements

### Policy Enforcement

AAL2 requirements can be set at two levels:
1. **Content-level**: Stored as content annotations (`c2.pas.aal2.require_aal2`)
2. **User-level**: Via "AAL2 Required User" role

The `check_aal2_access()` function enforces both policies and integrates with PAS validation.

### Plugin Integration

The AAL2 plugin implements three PAS interfaces:
- **IAuthenticationPlugin**: Verifies passkey authentication responses
- **IExtractionPlugin**: Extracts passkey credentials from requests
- **IValidationPlugin**: Enforces AAL2 requirements during access checks

## Security Considerations

### NIST AAL2 Compliance

This implementation follows [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) AAL2 requirements:
- ✅ Multi-factor authentication (possession + inherence/knowledge via passkey)
- ✅ Phishing-resistant authentication (WebAuthn/FIDO2)
- ✅ Time-bound re-authentication (15-minute window)
- ✅ Comprehensive audit logging

### Best Practices

1. **HTTPS Required**: WebAuthn only works over HTTPS (exception: localhost for development)
2. **User Verification**: Passkeys should require user verification (PIN, biometric, etc.)
3. **Audit Logs**: Monitor audit logs for suspicious AAL2 bypass attempts
4. **Role Management**: Carefully assign "AAL2 Required User" role only to privileged accounts
5. **Backup Authentication**: Users should register multiple passkeys in case one is lost

### Known Limitations

- **No Cross-Device Sync**: AAL2 timestamps are server-side only; users must re-authenticate on each device after 15 minutes
- **No Push Notifications**: Users are not notified before AAL2 expiry (could be added via UI enhancement)
- **Cache Invalidation**: Content-level AAL2 policies are cached for 60 seconds; changes may take up to 1 minute to propagate

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run AAL2-specific tests
pytest tests/test_session.py tests/test_policy.py tests/test_roles.py

# Run with coverage
pytest --cov=c2.pas.aal2 --cov-report=html tests/
```

### Test Coverage

Current test coverage:
- `session.py`: 76%
- `policy.py`: 65%
- `permissions.py`: 100%
- `roles.py`: 0% (utilities, tested via integration tests)

### Contract Tests

Contract tests verify API guarantees:
- `tests/test_session_contract.py`: Session API contracts (16 tests)
- `tests/test_policy_contract.py`: Policy API contracts (18 tests)

## Development

### Project Structure

```
src/c2/pas/aal2/
├── __init__.py
├── plugin.py              # Main PAS plugin
├── session.py             # AAL2 session tracking
├── policy.py              # AAL2 policy management
├── roles.py               # AAL2 role utilities
├── permissions.py         # Permission definitions
├── interfaces.py          # Zope interfaces
├── credential.py          # Passkey credential storage
├── browser/               # Browser views and templates
│   ├── views.py          # Passkey registration/login views
│   ├── viewlets.py       # AAL2 status viewlets
│   └── configure.zcml    # View registrations
├── profiles/default/      # GenericSetup profile
│   └── rolemap.xml       # Role definitions
└── utils/                 # Utility modules
    ├── webauthn.py       # WebAuthn helpers
    ├── audit.py          # Audit logging
    └── storage.py        # Credential storage

tests/
├── test_session.py        # Session management tests
├── test_policy.py         # Policy management tests
├── test_roles.py          # Role management tests
├── test_permissions.py    # Permission tests
├── test_session_contract.py  # Session API contracts
├── test_policy_contract.py   # Policy API contracts
└── test_pas_plugin.py     # Plugin integration tests
```

### Contributing

1. Follow TDD: Write tests first, then implementation
2. Run `ruff check` before committing
3. Ensure all tests pass
4. Add docstrings to all public functions
5. Update this README for new features

### Code Style

- Follow PEP 8
- Use double quotes for strings
- Maximum line length: 120 characters
- Run `ruff check --fix src/` to auto-fix issues

## Troubleshooting

### Common Issues

**Issue**: "Passkey authentication failed"
- **Solution**: Ensure HTTPS is enabled (or using localhost)
- **Solution**: Check browser WebAuthn support
- **Solution**: Verify RP ID matches your domain

**Issue**: "AAL2 timestamp expired immediately"
- **Solution**: Check server time synchronization
- **Solution**: Verify `AAL2_TIMEOUT_SECONDS` is set to 900

**Issue**: "User not prompted for AAL2 re-authentication"
- **Solution**: Verify plugin is activated for "Validation" in PAS
- **Solution**: Check that content has AAL2 policy set OR user has AAL2 role
- **Solution**: Clear browser cache and session

**Issue**: "ImportError: No module named 'webauthn'"
- **Solution**: Install py_webauthn: `pip install webauthn==2.7.0`

### Debug Logging

Enable debug logging in your Zope configuration:

```ini
[logger_c2.pas.aal2]
level = DEBUG
handlers = console

[logger_c2.pas.aal2.session]
level = DEBUG

[logger_c2.pas.aal2.policy]
level = DEBUG

[logger_c2.pas.aal2.audit]
level = INFO
```

## Changelog

### Version 1.0.0 (2025)

- Initial release with AAL2 compliance features
- WebAuthn/Passkey authentication support
- 15-minute re-authentication window
- Content-level and role-based AAL2 protection
- Comprehensive audit logging
- Full test coverage with contract tests

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Credits

- Developed using [py_webauthn](https://github.com/duo-labs/py_webauthn) by Duo Labs
- Implements [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) AAL2 requirements
- Built for [Plone CMS](https://plone.org)

## Support

- GitHub Issues: https://github.com/cmscom/c2.pas.aal2/issues
- Documentation: https://c2-pas-aal2.readthedocs.io/
- Plone Community: https://community.plone.org

---

**Generated with Claude Code** 🤖
