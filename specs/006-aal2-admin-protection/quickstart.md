# Quickstart: AAL2 Admin Protection Development

**Feature**: 006-aal2-admin-protection
**Date**: 2025-11-10
**Audience**: Developers implementing this feature

## Prerequisites

Before starting work on this feature, ensure you have:

1. ✅ **Completed features 001-005**:
   - 001: Basic c2.pas.aal2 package structure
   - 002: Passkey login implementation
   - 003: AAL2 compliance (session management, timestamps)
   - 005: JavaScript externalization, audit logging

2. ✅ **Development environment**:
   - Python 3.11+
   - Plone 5.2+ instance running
   - c2.pas.aal2 add-on installed and activated
   - Test user with registered passkey

3. ✅ **Verified existing functionality**:
   ```bash
   # Can log in with passkey
   # AAL2 timestamp is recorded
   # Existing admin pages accessible
   ```

---

## Quick Setup (5 Minutes)

### 1. Create the Admin Module

```bash
cd /workspace/src/c2/pas/aal2
mkdir -p admin
touch admin/__init__.py
touch admin/interfaces.py
touch admin/protection.py
touch admin/subscriber.py
touch admin/configure.zcml
```

### 2. Set Up Testing

```bash
cd /workspace/tests
touch test_admin_protection.py
touch test_admin_challenge.py
touch test_integration_admin.py
```

### 3. Verify Plone is Running

```bash
# Start Plone if not running
cd /workspace
./bin/instance fg

# In another terminal, verify:
curl http://localhost:8080/Plone/@@overview-controlpanel
# Should return 200 OK (currently no AAL2 protection)
```

---

## Development Workflow

### Phase 1: Core Protection Logic (P1 - 4 hours)

**Goal**: Intercept admin requests and enforce AAL2 checks

#### Step 1.1: Registry Schema (30 min)

**File**: `src/c2/pas/aal2/admin/interfaces.py`

```python
from zope.interface import Interface
from zope import schema

class IAAL2AdminSettings(Interface):
    """AAL2 admin protection settings."""

    protected_patterns = schema.List(
        title=u"Protected Admin URL Patterns",
        description=u"URL patterns requiring AAL2 (glob syntax)",
        value_type=schema.TextLine(),
        default=[
            '*/@@overview-controlpanel',
            '*/@@usergroup-userprefs',
            '*/@@usergroup-groupprefs',
            '*/@@member-registration',
            '*/prefs_install_products_form',
            '*/@@installer',
            '*/@@security-controlpanel',
        ],
        required=False,
    )

    enabled = schema.Bool(
        title=u"Enable Admin AAL2 Protection",
        default=True,
    )
```

**Test**:
```python
# tests/test_admin_protection.py
def test_registry_schema():
    settings = getUtility(IRegistry).forInterface(IAAL2AdminSettings)
    assert len(settings.protected_patterns) == 7
    assert settings.enabled is True
```

---

#### Step 1.2: URL Pattern Matching (45 min)

**File**: `src/c2/pas/aal2/admin/protection.py`

```python
import fnmatch
from plone import api
from plone.memoize import ram
import logging

logger = logging.getLogger('c2.pas.aal2.admin')

def _pattern_cache_key(method):
    """Cache key based on registry values."""
    try:
        patterns = api.portal.get_registry_record(
            'c2.pas.aal2.admin.protected_patterns'
        )
        return hash(tuple(patterns))
    except Exception:
        return 'default'

@ram.cache(_pattern_cache_key)
def get_protected_patterns():
    """Get protected URL patterns from registry."""
    try:
        return api.portal.get_registry_record(
            'c2.pas.aal2.admin.protected_patterns'
        )
    except Exception as e:
        logger.warning(f"Could not load patterns: {e}")
        # Return defaults
        return ['*/@@overview-controlpanel']

def is_protected_url(url):
    """Check if URL matches any protected pattern."""
    patterns = get_protected_patterns()
    for pattern in patterns:
        if fnmatch.fnmatch(url, pattern):
            return True
    return False
```

**Test**:
```python
def test_url_matching():
    assert is_protected_url('http://localhost/Plone/@@overview-controlpanel') is True
    assert is_protected_url('http://localhost/Plone/front-page') is False
```

---

#### Step 1.3: Access Checking (1 hour)

**File**: `src/c2/pas/aal2/admin/protection.py` (continued)

```python
from c2.pas.aal2.session import is_aal2_valid

def check_admin_access(request, user):
    """Check if user should be allowed admin access."""
    try:
        url = request.URL

        # Check if protection is enabled
        enabled = api.portal.get_registry_record('c2.pas.aal2.admin.enabled')
        if not enabled:
            return {'allowed': True, 'reason': 'disabled', 'redirect_url': None}

        # Check if URL is protected
        if not is_protected_url(url):
            return {'allowed': True, 'reason': 'not_protected', 'redirect_url': None}

        # Check AAL2 validity
        if is_aal2_valid(user):
            return {'allowed': True, 'reason': 'aal2_valid', 'redirect_url': None}

        # AAL2 expired - need challenge
        portal_url = api.portal.get().absolute_url()
        return {
            'allowed': False,
            'reason': 'aal2_expired',
            'redirect_url': f'{portal_url}/@@admin-aal2-challenge'
        }

    except Exception as e:
        logger.exception(f"Error checking admin access: {e}")
        # Fail open for availability
        return {'allowed': True, 'reason': 'error', 'redirect_url': None}
```

**Test**:
```python
def test_check_admin_access_expired_aal2(mock_user, mock_request):
    # Set AAL2 timestamp 20 minutes ago
    set_aal2_timestamp(mock_user, datetime.now() - timedelta(minutes=20))

    result = check_admin_access(mock_request, mock_user)
    assert result['allowed'] is False
    assert result['reason'] == 'aal2_expired'
    assert '@@admin-aal2-challenge' in result['redirect_url']
```

---

#### Step 1.4: Event Subscriber (1 hour)

**File**: `src/c2/pas/aal2/admin/subscriber.py`

```python
from zope.publisher.interfaces import IPubBeforeCommit
from plone import api
import logging

logger = logging.getLogger('c2.pas.aal2.admin.subscriber')

def check_admin_aal2_subscriber(event):
    """Subscriber to check AAL2 on admin access."""
    request = event.request

    try:
        # Get current user
        user = api.user.get_current()
        if not user or user.getId() is None:
            # Anonymous user - let normal auth handle it
            return

        # Check if admin access allowed
        from c2.pas.aal2.admin.protection import check_admin_access
        result = check_admin_access(request, user)

        if not result['allowed']:
            # Store redirect context
            from c2.pas.aal2.admin.protection import store_redirect_context
            store_redirect_context(request, request.URL)

            # Redirect to challenge
            request.response.redirect(result['redirect_url'])

            # Log the challenge
            from c2.pas.aal2.utils.audit import log_audit_event
            log_audit_event(
                event_type='admin_access_challenged',
                user_id=user.getId(),
                admin_url=request.URL,
                aal2_valid=False,
            )

    except Exception as e:
        logger.exception(f"Error in admin AAL2 subscriber: {e}")
        # Don't block requests on error
```

**File**: `src/c2/pas/aal2/admin/configure.zcml`

```xml
<configure xmlns="http://namespaces.zope.org/zope">

  <subscriber
      for="zope.publisher.interfaces.IPubBeforeCommit"
      handler=".subscriber.check_admin_aal2_subscriber"
      />

</configure>
```

**Test**:
```bash
# Manual test: access control panel with expired AAL2
# Should redirect to challenge page
```

---

### Phase 2: Challenge UI (P2 - 3 hours)

**Goal**: Implement re-authentication challenge view

#### Step 2.1: Challenge View (2 hours)

**File**: `src/c2/pas/aal2/browser/views.py` (add class)

```python
class AdminAAL2ChallengeView(BrowserView):
    """Challenge view for admin AAL2 re-authentication."""

    def __call__(self):
        # Get redirect context
        from c2.pas.aal2.admin.protection import get_redirect_context
        context = get_redirect_context(self.request)

        if not context:
            # No redirect context - go home
            return self.request.response.redirect(
                api.portal.get().absolute_url()
            )

        # Check if AAL2 now valid (e.g., authenticated in another tab)
        user = api.user.get_current()
        if is_aal2_valid(user):
            # Already valid - redirect back
            from c2.pas.aal2.admin.protection import clear_redirect_context
            clear_redirect_context(self.request)
            return self.request.response.redirect(context['original_url'])

        # Generate passkey challenge
        from c2.pas.aal2.utils.webauthn import create_authentication_options
        options = create_authentication_options(user)

        return self.index(
            original_url=context['original_url'],
            challenge_count=context['challenge_count'],
            passkey_options=options,
        )

    def handle_authentication(self):
        """Handle passkey authentication POST."""
        # ... verify passkey, update AAL2 timestamp, redirect ...
```

**Template**: `src/c2/pas/aal2/browser/templates/admin_aal2_challenge.pt`

```xml
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Admin Access Re-authentication Required</title>
</head>
<body>
  <h1>Security Verification Required</h1>

  <p>Access to <strong tal:content="view/original_url">admin page</strong>
     requires recent authentication.</p>

  <p>Please verify your identity using your passkey.</p>

  <div id="passkey-challenge">
    <!-- WebAuthn UI from feature 002 -->
  </div>

  <a href="" tal:attributes="href python:portal_url">Cancel</a>
</body>
</html>
```

---

### Phase 3: Configuration UI (P2 - 2 hours)

**Goal**: Add control panel for pattern configuration

#### Step 3.1: Control Panel View (1 hour)

**File**: `src/c2/pas/aal2/controlpanel/interfaces.py` (extend)

```python
class IAAL2ControlPanel(Interface):
    """Existing interface from 005 - add admin fields."""

    # ... existing fields ...

    admin_protection_enabled = schema.Bool(
        title=u"Enable Admin AAL2 Protection",
        default=True,
    )

    admin_protected_patterns = schema.List(
        title=u"Protected Admin URL Patterns",
        value_type=schema.TextLine(),
    )
```

---

## Common Development Tasks

### Run Tests

```bash
cd /workspace
pytest tests/test_admin_protection.py -v
pytest tests/test_integration_admin.py -v
```

### Check AAL2 Status

```python
# In Plone debug shell
from c2.pas.aal2.session import is_aal2_valid
from plone import api

user = api.user.get(username='admin')
print(f"AAL2 valid: {is_aal2_valid(user)}")
```

### Clear Session Data (Development)

```python
# Reset challenge state
request = api.env.getRequest()
if 'c2.pas.aal2.admin_redirect_url' in request.SESSION:
    del request.SESSION['c2.pas.aal2.admin_redirect_url']
```

### Test URL Matching

```python
from c2.pas.aal2.admin.protection import is_protected_url

test_urls = [
    'http://localhost/Plone/@@overview-controlpanel',
    'http://localhost/Plone/@@manage-portlets',
    'http://localhost/Plone/front-page',
]

for url in test_urls:
    print(f"{url}: {is_protected_url(url)}")
```

---

## Debugging Tips

### Enable Debug Logging

```python
# In buildout.cfg
[instance]
event-log-level = DEBUG
```

### Check Subscriber Registration

```bash
# Verify subscriber is registered
./bin/instance debug
>>> from zope.component import getGlobalSiteManager
>>> gsm = getGlobalSiteManager()
>>> list(gsm.registeredSubscribers())
# Should see check_admin_aal2_subscriber
```

### Inspect Session Data

```python
# In view or subscriber
logger.info(f"Session keys: {request.SESSION.keys()}")
logger.info(f"Redirect context: {request.SESSION.get('c2.pas.aal2.admin_redirect_url')}")
```

### Test Without Browser

```bash
# Use curl to test redirect
curl -v -u admin:admin http://localhost:8080/Plone/@@overview-controlpanel
# Should see 302 redirect to @@admin-aal2-challenge
```

---

## Integration Points

### With Feature 002 (Passkey Login)

```python
# Reuse WebAuthn utilities
from c2.pas.aal2.utils.webauthn import (
    create_authentication_options,
    verify_authentication,
)
```

### With Feature 003 (AAL2 Compliance)

```python
# Use session management
from c2.pas.aal2.session import (
    is_aal2_valid,
    set_aal2_timestamp,
    get_aal2_timestamp,
)
```

### With Feature 005 (Audit Logging)

```python
# Log admin access events
from c2.pas.aal2.utils.audit import log_audit_event

log_audit_event(
    event_type='admin_access_challenged',
    user_id=user.getId(),
    admin_url=request.URL,
)
```

---

## Troubleshooting

### "Subscriber not firing"

**Problem**: Admin pages accessible without challenge

**Check**:
1. Is `admin/configure.zcml` included in main `configure.zcml`?
2. Is add-on reinstalled/upgraded after adding subscriber?
3. Check event log for registration errors

**Solution**:
```bash
./bin/instance restart
# Check logs for subscriber registration
```

---

### "Redirect loop"

**Problem**: Keeps redirecting to challenge page

**Check**:
1. Is AAL2 timestamp being updated after successful auth?
2. Is session data being cleared properly?
3. Check challenge_count in session

**Solution**:
```python
# Clear problematic session
del request.SESSION['c2.pas.aal2.admin_redirect_url']
# Force AAL2 timestamp update
from c2.pas.aal2.session import set_aal2_timestamp
set_aal2_timestamp(user)
```

---

### "Patterns not matching"

**Problem**: Admin pages not protected

**Check**:
1. Are patterns in registry correct?
2. Is URL format correct (full URL vs path)?
3. Is caching working properly?

**Solution**:
```python
# Test pattern matching directly
from c2.pas.aal2.admin.protection import is_protected_url
print(is_protected_url('http://localhost/Plone/@@overview-controlpanel'))

# Check registry
from plone import api
patterns = api.portal.get_registry_record('c2.pas.aal2.admin.protected_patterns')
print(patterns)
```

---

## Performance Monitoring

### Measure Subscriber Overhead

```python
import time

def check_admin_aal2_subscriber(event):
    start = time.time()
    # ... existing code ...
    elapsed = (time.time() - start) * 1000
    if elapsed > 10:
        logger.warning(f"Admin AAL2 check took {elapsed:.2f}ms")
```

### Profile URL Matching

```python
import cProfile

cProfile.runctx(
    'is_protected_url("http://localhost/Plone/@@overview-controlpanel")',
    globals(),
    locals(),
)
# Should be <5ms
```

---

## Next Steps

After completing development:

1. ✅ Run full test suite
2. ✅ Test in multiple browsers
3. ✅ Test multi-tab scenario
4. ✅ Verify audit logs
5. ✅ Check performance (<10ms target)
6. ✅ Update CLAUDE.md with any new technologies
7. ✅ Create pull request

---

## References

- [Feature Spec](./spec.md)
- [Research](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/admin-protection-api.md)
- Feature 003: `/workspace/specs/003-aal2-compliance/`
- Feature 002: `/workspace/specs/002-passkey-login/`
- Plone Development: https://5.docs.plone.org/
