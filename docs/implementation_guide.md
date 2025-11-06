# Implementation Guide: c2.pas.aal2 AAL2 Authentication Plugin

This guide provides detailed instructions for implementing AAL2 (Authentication Assurance Level 2) functionality on top of the c2.pas.aal2 template package.

## Table of Contents

1. [Overview](#overview)
2. [AAL2 Concepts](#aal2-concepts)
3. [Architecture](#architecture)
4. [Implementation Steps](#implementation-steps)
5. [Extending Stub Methods](#extending-stub-methods)
6. [Adding New PAS Interfaces](#adding-new-pas-interfaces)
7. [Testing Strategy](#testing-strategy)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

## Overview

The c2.pas.aal2 package provides a skeleton for implementing AAL2 authentication in Plone. The current implementation includes:

- **Stub AAL2Plugin class** with IAuthenticationPlugin and IExtractionPlugin
- **IAAL2Plugin interface** defining AAL2-specific methods
- **ZCML configuration** for plugin registration
- **Test structure** with pytest

Your task is to implement the actual AAL2 authentication logic.

## AAL2 Concepts

### Authentication Assurance Levels

- **AAL1**: Single-factor authentication (password only)
- **AAL2**: Two-factor authentication (password + OTP/2FA)
- **AAL3**: Hardware-based cryptographic authentication

### Key Requirements for AAL2

1. **Multi-factor authentication**: Requires at least two independent authentication factors
2. **Session management**: Track AAL level throughout user session
3. **Step-up authentication**: Force additional authentication for sensitive operations
4. **Policy enforcement**: Define which content requires AAL2 access

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────┐
│ Plone Request                                │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│ PAS (Pluggable Authentication Service)      │
│  ┌───────────────────────────────────────┐  │
│  │ AAL2Plugin (c2.pas.aal2)              │  │
│  │  ├─ extractCredentials()              │  │
│  │  ├─ authenticateCredentials()         │  │
│  │  ├─ get_aal_level()                   │  │
│  │  └─ require_aal2()                    │  │
│  └───────────────────────────────────────┘  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ User Session (with AAL level metadata)      │
└─────────────────────────────────────────────┘
```

### Data Flow

```
1. User Login → extractCredentials() → Extract username/password/2FA token
2. Credential Validation → authenticateCredentials() → Verify credentials + AAL level
3. Session Creation → Store AAL level in session
4. Content Access → require_aal2() → Check if AAL2 needed
5. Step-up Auth (if needed) → Force additional authentication
```

## Implementation Steps

### Step 1: Implement Credential Extraction

Modify `src/c2/pas/aal2/plugin.py` - `extractCredentials()`:

```python
def extractCredentials(self, request):
    """Extract credentials including 2FA token from request."""
    creds = {}

    # Extract basic credentials (username/password)
    login = request.get('__ac_name', '')
    password = request.get('__ac_password', '')

    if login:
        creds['login'] = login
        creds['password'] = password

    # Extract 2FA token (if present)
    otp_token = request.get('otp_token', '')
    if otp_token:
        creds['otp_token'] = otp_token

    # Extract authentication method hint
    auth_method = request.get('auth_method', 'password')
    creds['auth_method'] = auth_method

    return creds
```

### Step 2: Implement Authentication with AAL Level Detection

```python
def authenticateCredentials(self, credentials):
    """Authenticate credentials and determine AAL level."""
    login = credentials.get('login')
    password = credentials.get('password')
    otp_token = credentials.get('otp_token')

    if not login or not password:
        return None

    # Verify base credentials (AAL1)
    user = self._verify_password(login, password)
    if not user:
        return None

    # Check for 2FA (AAL2)
    if otp_token:
        if self._verify_otp(user, otp_token):
            # Store AAL2 in session
            self._set_session_aal(user, 2)
            return (user.getId(), login)
        else:
            return None  # OTP verification failed

    # Only password authentication (AAL1)
    self._set_session_aal(user, 1)
    return (user.getId(), login)


def _verify_password(self, login, password):
    """Verify username and password against user database."""
    # Implementation depends on your user storage
    # Example: Use Plone's standard user authentication
    pas = self._getPAS()
    plugins = pas.plugins.listPlugins(IAuthenticationPlugin)

    for plugin_id, plugin in plugins:
        if plugin_id == self.getId():
            continue  # Skip ourselves
        user_id = plugin.authenticateCredentials({
            'login': login,
            'password': password
        })
        if user_id:
            return pas.getUserById(user_id[0])
    return None


def _verify_otp(self, user, otp_token):
    """Verify OTP/2FA token for user."""
    # TODO: Implement OTP verification
    # Options:
    # - TOTP (Time-based OTP) using libraries like pyotp
    # - SMS OTP via external service
    # - Hardware token verification
    # Example with TOTP:
    # import pyotp
    # user_secret = self._get_user_totp_secret(user)
    # totp = pyotp.TOTP(user_secret)
    # return totp.verify(otp_token)
    pass


def _set_session_aal(self, user, aal_level):
    """Store AAL level in user session."""
    sdm = getToolByName(self, 'session_data_manager')
    session = sdm.getSessionData(create=True)
    session['aal_level'] = aal_level
    session['aal_timestamp'] = datetime.now()
```

### Step 3: Implement AAL Level Detection

```python
def get_aal_level(self, user_id):
    """Get current AAL level for user from session."""
    try:
        sdm = getToolByName(self, 'session_data_manager')
        session = sdm.getSessionData(create=False)
        if session:
            aal_level = session.get('aal_level', 1)
            # Check if AAL timestamp is still valid (e.g., within 30 minutes)
            timestamp = session.get('aal_timestamp')
            if timestamp and (datetime.now() - timestamp).seconds > 1800:
                # AAL expired, downgrade to AAL1
                return 1
            return aal_level
    except:
        pass
    return 1  # Default to AAL1
```

### Step 4: Implement AAL2 Policy Enforcement

```python
def require_aal2(self, user_id, context):
    """Check if AAL2 is required for accessing context."""
    # Check content annotation for AAL2 requirement
    from zope.annotation.interfaces import IAnnotations

    try:
        annotations = IAnnotations(context)
        aal2_required = annotations.get('c2.pas.aal2.required', False)

        if aal2_required:
            current_aal = self.get_aal_level(user_id)
            return current_aal < 2  # Return True if AAL2 needed but not met
    except:
        pass

    return False  # No AAL2 requirement by default
```

### Step 5: Add Content Annotation for AAL2 Policy

Create `src/c2/pas/aal2/browser/aal2_policy.py`:

```python
"""Browser views for managing AAL2 policies on content."""

from zope.annotation.interfaces import IAnnotations
from Products.Five.browser import BrowserView


class AAL2PolicyView(BrowserView):
    """View for setting AAL2 requirements on content."""

    def set_aal2_required(self, required=True):
        """Mark content as requiring AAL2 authentication."""
        annotations = IAnnotations(self.context)
        annotations['c2.pas.aal2.required'] = required
        return "AAL2 requirement set to: {}".format(required)

    def get_aal2_required(self):
        """Check if content requires AAL2."""
        annotations = IAnnotations(self.context)
        return annotations.get('c2.pas.aal2.required', False)
```

Register in `configure.zcml`:

```xml
<browser:page
    name="aal2-policy"
    for="*"
    class=".browser.aal2_policy.AAL2PolicyView"
    permission="cmf.ManagePortal"
    />
```

## Adding New PAS Interfaces

To extend functionality, you can implement additional PAS interfaces:

### IPropertiesPlugin

For storing AAL-related user properties:

```python
from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin

@implementer(IPropertiesPlugin)
class AAL2Plugin(BasePlugin):
    # ... existing code ...

    def getPropertiesForUser(self, user, request=None):
        """Return AAL level as user property."""
        return {
            'aal_level': self.get_aal_level(user.getId()),
        }
```

### IChallengePlugin

For triggering step-up authentication:

```python
from Products.PluggableAuthService.interfaces.plugins import IChallengePlugin

@implementer(IChallengePlugin)
class AAL2Plugin(BasePlugin):
    # ... existing code ...

    def challenge(self, request, response):
        """Challenge user for additional authentication."""
        if self._needs_step_up_auth(request):
            # Redirect to 2FA page
            response.redirect('/require_2fa')
            return True
        return False
```

## Testing Strategy

### Unit Tests

Add tests for each implemented method:

```python
# tests/test_aal2_authentication.py
def test_aal1_authentication(aal2_plugin):
    """Test basic password authentication returns AAL1."""
    creds = {'login': 'user', 'password': 'pass'}
    result = aal2_plugin.authenticateCredentials(creds)
    assert aal2_plugin.get_aal_level('user') == 1


def test_aal2_authentication(aal2_plugin):
    """Test 2FA authentication returns AAL2."""
    creds = {
        'login': 'user',
        'password': 'pass',
        'otp_token': '123456'
    }
    result = aal2_plugin.authenticateCredentials(creds)
    assert aal2_plugin.get_aal_level('user') == 2
```

### Integration Tests

Test with actual Plone environment:

```python
# tests/test_plone_integration.py
def test_aal2_policy_enforcement(plone_site):
    """Test that AAL2-protected content is inaccessible with AAL1."""
    # Set up AAL2 requirement on content
    content = plone_site['protected-page']
    IAnnotations(content)['c2.pas.aal2.required'] = True

    # Login with AAL1
    login(plone_site, 'user')

    # Attempt access - should be denied or prompted for 2FA
    with pytest.raises(Unauthorized):
        content.restrictedTraverse('@@view')()
```

## Deployment

### 1. Update setup.py Dependencies

```python
install_requires=[
    'setuptools',
    'Plone>=5.2',
    'Products.PluggableAuthService',
    'pyotp',  # For TOTP implementation
],
```

### 2. Create GenericSetup Profile

```bash
mkdir -p src/c2/pas/aal2/profiles/default
```

Create `src/c2/pas/aal2/profiles/default/metadata.xml`:

```xml
<?xml version="1.0"?>
<metadata>
  <version>1</version>
  <dependencies>
    <dependency>profile-Products.CMFPlone:plone</dependency>
  </dependencies>
</metadata>
```

Create `src/c2/pas/aal2/profiles/default/componentregistry.xml`:

```xml
<?xml version="1.0"?>
<componentregistry>
  <adapters>
    <!-- Register AAL2 adapters here -->
  </adapters>
</componentregistry>
```

### 3. Update configure.zcml

```xml
<genericsetup:registerProfile
    name="default"
    title="c2.pas.aal2: AAL2 Authentication Plugin"
    directory="profiles/default"
    description="Install AAL2 authentication support"
    provides="Products.GenericSetup.interfaces.EXTENSION"
    />
```

## Troubleshooting

### Issue: Plugin not appearing in PAS

**Solution**: Verify ZCML is loaded:
- Check that configure.zcml is included
- Restart Plone instance
- Check Zope logs for ZCML errors

### Issue: Authentication always fails

**Solution**: Debug authentication flow:
- Add logging to authenticateCredentials()
- Verify credentials are being extracted correctly
- Check that base authentication plugins are working

### Issue: AAL level not persisting

**Solution**: Verify session management:
- Ensure session_data_manager is available
- Check session timeout settings
- Verify annotations are being stored correctly

### Issue: 2FA token verification fails

**Solution**: Check OTP implementation:
- Verify time synchronization between server and client
- Check TOTP secret is correctly stored
- Add logging to _verify_otp() method

## Best Practices

1. **Always log authentication attempts** - Use Plone's logging framework
2. **Implement rate limiting** - Prevent brute force attacks on 2FA
3. **Use secure secret storage** - Never store TOTP secrets in plain text
4. **Validate AAL timestamps** - Expire AAL2 sessions after reasonable timeout
5. **Test edge cases** - Clock skew, expired tokens, missing credentials
6. **Document security assumptions** - Make security model clear to operators

## Resources

- **Plone PAS Documentation**: https://docs.plone.org/develop/plone/security/pas.html
- **NIST AAL Guidelines**: https://pages.nist.gov/800-63-3/sp800-63b.html
- **TOTP RFC 6238**: https://tools.ietf.org/html/rfc6238
- **pyotp Library**: https://pyauth.github.io/pyotp/

## Next Steps

1. Implement credential extraction with 2FA token support
2. Add OTP verification using pyotp or similar library
3. Implement session AAL level storage and retrieval
4. Add AAL2 policy annotation to content types
5. Create browser views for AAL2 policy management
6. Write comprehensive tests for authentication flows
7. Add logging and monitoring
8. Create user documentation for 2FA enrollment

For questions or contributions, refer to the project README and Plone community forums.
