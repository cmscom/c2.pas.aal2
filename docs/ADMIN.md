# Administrator Guide - Passkey Authentication

This guide covers PAS plugin configuration, security considerations, monitoring, and troubleshooting for site administrators.

## Table of Contents

- [Installation and Configuration](#installation-and-configuration)
- [PAS Plugin Configuration](#pas-plugin-configuration)
- [Security Configuration](#security-configuration)
- [Monitoring and Audit Logs](#monitoring-and-audit-logs)
- [User Management](#user-management)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Backup and Recovery](#backup-and-recovery)

## Installation and Configuration

### Prerequisites

1. **HTTPS Configuration**: WebAuthn requires HTTPS in production
   ```nginx
   # Nginx example
   server {
       listen 443 ssl http2;
       server_name your-plone-site.com;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
   }
   ```

2. **Python Dependencies**: Ensure webauthn library is installed
   ```bash
   pip install webauthn==2.7.0
   ```

3. **Browser Requirements**: Inform users about supported browsers
   - Chrome 67+ / Chromium-based browsers
   - Firefox 60+
   - Safari 13+ (macOS/iOS)
   - Edge 18+

### Installation Steps

1. **Add to buildout.cfg**:
   ```ini
   [buildout]
   eggs =
       c2.pas.aal2

   [instance]
   eggs =
       ${buildout:eggs}
   ```

2. **Run buildout**:
   ```bash
   bin/buildout
   ```

3. **Restart Plone**:
   ```bash
   bin/instance restart
   ```

4. **Activate Add-on**:
   - Go to Site Setup → Add-ons
   - Find "Passkey Authentication (c2.pas.aal2)"
   - Click Activate

### GenericSetup Profile

The package includes a GenericSetup profile that automatically:
- Registers the AAL2Plugin in PAS
- Configures plugin interfaces (IExtractionPlugin, IAuthenticationPlugin)
- Sets up default plugin order
- Creates controlpanel entry for user access

## PAS Plugin Configuration

### Accessing PAS Configuration

1. Navigate to: `http://your-site/acl_users/manage_workspace`
2. The AAL2Plugin should be listed as `aal2_plugin`

### Plugin Interfaces

The AAL2Plugin implements two PAS interfaces:

```python
# IExtractionPlugin
# Extracts passkey credentials from HTTP requests
priority: 1 (runs early in extraction chain)

# IAuthenticationPlugin
# Validates passkey assertions and authenticates users
priority: 1 (runs alongside other auth plugins)
```

### Plugin Order

Recommended plugin activation order:

```
Extraction Plugins:
1. credentials_cookie_auth (session extraction)
2. aal2_plugin (passkey extraction)
3. credentials_basic_auth (HTTP Basic)

Authentication Plugins:
1. aal2_plugin (passkey auth)
2. mutable_properties (password auth)
3. ldap_plugin (if using LDAP)
```

**Important**: Keep password authentication enabled! It serves as fallback.

### Adjusting Plugin Priority

To change plugin order:

1. Go to `acl_users/plugins/manage_plugins`
2. Find "IExtractionPlugin" tab
3. Move aal2_plugin up/down in priority
4. Repeat for "IAuthenticationPlugin" tab

## Security Configuration

### HTTPS Enforcement

WebAuthn REQUIRES HTTPS. Configure your reverse proxy:

```nginx
# Nginx - Force HTTPS
server {
    listen 80;
    server_name your-site.com;
    return 301 https://$server_name$request_uri;
}
```

For development, `localhost` is exempt from HTTPS requirement.

### Relying Party (RP) Configuration

The RP ID and name are auto-detected from your Plone site:

```python
# Automatic detection in plugin.py
rp_id = urlparse(portal_url).hostname  # e.g., "example.com"
rp_name = portal.getProperty('title', 'Plone Site')
```

To override, modify `plugin.py:generateRegistrationOptions()`:

```python
def generateRegistrationOptions(self, request, user, ...):
    # Custom RP ID (must be domain or subdomain)
    rp_id = 'auth.example.com'
    rp_name = 'Example Corp Authentication'

    # ... rest of method
```

### Challenge Timeout Configuration

Challenges expire after 5 minutes by default. To adjust:

```python
# In utils/webauthn.py
def create_registration_options(...):
    options = generate_registration_options(
        # ...
        timeout=300000,  # milliseconds (5 minutes)
    )
```

**Security Note**: Shorter timeouts improve security but may frustrate users. 5 minutes is recommended.

### Origin Validation

The plugin validates that authentication requests come from the correct origin:

```python
# Automatic in plugin.py
expected_origin = portal_url  # Must match exactly
```

This prevents cross-site replay attacks.

### FR-016: Last Authentication Method Protection

Users cannot delete their last passkey if no password is set. This prevents account lockout.

Configuration is automatic and cannot be disabled (security requirement).

To check a user's authentication methods:

```python
from c2.pas.aal2.credential import count_passkeys

passkey_count = count_passkeys(user)
has_password = user.getProperty('password', None) is not None

# User needs at least one method
assert passkey_count > 0 or has_password
```

## Monitoring and Audit Logs

### Audit Logging

All passkey operations are logged to Python's logging system.

**Log Locations**:
- Standard: `var/log/instance.log`
- With ZEO: `var/log/client1.log`

**Log Levels**:
- `INFO`: Successful operations (registration, authentication, deletion)
- `WARNING`: Failed operations (verification failures, challenge mismatches)
- `ERROR`: System errors (plugin not found, storage issues)

### Log Format

```
# Successful passkey registration
INFO c2.pas.aal2.utils.audit Passkey registration successful user_id=john credential_id=abc123... ip=192.168.1.100

# Failed authentication attempt
WARNING c2.pas.aal2.utils.audit Passkey authentication failed user_id=jane error=signature_invalid ip=192.168.1.200

# Passkey deleted
INFO c2.pas.aal2.utils.audit Passkey deleted user_id=john credential_id=abc123... ip=192.168.1.100
```

### Parsing Audit Logs

Example script to extract passkey events:

```bash
# Count successful authentications
grep "Passkey authentication successful" var/log/instance.log | wc -l

# Find failed login attempts for specific user
grep "authentication failed.*user_id=john" var/log/instance.log

# Export to CSV for analysis
grep "Passkey" var/log/instance.log | \
  sed 's/.*user_id=\([^ ]*\).*/\1/' | \
  sort | uniq -c > passkey_stats.csv
```

### Setting Up Log Rotation

```bash
# /etc/logrotate.d/plone
/path/to/plone/var/log/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

### Integration with SIEM

Forward logs to your Security Information and Event Management system:

```python
# Add to instance.cfg
[instance]
event-log-custom =
    <syslog>
      address siem.example.com:514
      facility local4
      format %(asctime)s %(levelname)s %(name)s %(message)s
    </syslog>
```

## User Management

### Viewing User's Passkeys

As administrator, inspect user's registered passkeys:

```python
# Via Python console
from c2.pas.aal2.credential import get_user_passkeys
user = portal.acl_users.getUserById('username')
passkeys = get_user_passkeys(user)

for cred_id, passkey in passkeys.items():
    print(f"Device: {passkey['device_name']}")
    print(f"Type: {passkey['device_type']}")
    print(f"Registered: {passkey['created']}")
    print(f"Last Used: {passkey['last_used']}")
    print(f"Sign Count: {passkey['sign_count']}")
    print("---")
```

### Removing User's Passkeys (Administrative)

In emergency situations (e.g., compromised account):

```python
from c2.pas.aal2.credential import delete_passkey, get_user_passkeys

user = portal.acl_users.getUserById('username')
passkeys = get_user_passkeys(user)

# Delete specific passkey
delete_passkey(user, credential_id)

# Or delete all passkeys
from zope.annotation.interfaces import IAnnotations
annotations = IAnnotations(user)
if 'c2.pas.aal2.passkeys' in annotations:
    del annotations['c2.pas.aal2.passkeys']
    user._p_changed = True
```

**Warning**: This is an administrative override. Users should normally manage their own passkeys.

### Bulk Operations

Reset all passkeys for a group of users:

```python
# Example: Remove passkeys for test users
for user_id in portal.acl_users.getUserIds():
    if user_id.startswith('test_'):
        user = portal.acl_users.getUserById(user_id)
        annotations = IAnnotations(user)
        if 'c2.pas.aal2.passkeys' in annotations:
            del annotations['c2.pas.aal2.passkeys']
            user._p_changed = True
            print(f"Cleared passkeys for {user_id}")
```

## Troubleshooting

### "Plugin not found" Errors

**Symptom**: Views return `AAL2 plugin not found`

**Diagnosis**:
```python
portal.acl_users.aal2_plugin  # Should exist
```

**Solution**:
1. Re-run GenericSetup import steps
2. Or manually add plugin:
   ```python
   from c2.pas.aal2.plugin import manage_addAAL2Plugin
   manage_addAAL2Plugin(portal.acl_users, 'aal2_plugin')
   ```

### HTTPS/Origin Mismatch

**Symptom**: `Invalid origin` errors in logs

**Diagnosis**:
- Check portal URL configuration
- Verify reverse proxy headers

**Solution**:
```python
# Fix portal URL
portal_url = portal.absolute_url()
# Should be https://your-site.com, not http://localhost:8080

# If behind reverse proxy, configure virtual host monster:
# /VirtualHostBase/https/your-site.com:443/Plone/VirtualHostRoot/
```

### Challenge Expired Errors

**Symptom**: Users get "No challenge found in session"

**Causes**:
- Session timeout (user waited too long)
- Multiple browser tabs (sessions conflict)
- Server restart (sessions cleared)

**Solutions**:
- Increase challenge timeout (default 5 minutes)
- Educate users to complete auth promptly
- Implement persistent session storage

### Performance Issues

**Symptom**: Slow authentication

**Diagnosis**:
```python
import time
start = time.time()
plugin.verifyAuthenticationResponse(...)
elapsed = time.time() - start
print(f"Verification took {elapsed:.2f}s")
```

**Solutions**:
- Cache user lookups
- Optimize ZODB connection settings
- Enable ZEO client cache
- Add database indices for user queries

## Performance Tuning

### ZODB Configuration

```ini
[instance]
# Increase ZODB cache size for better performance
zodb-cache-size = 10000

# Enable persistent cache
zeo-client-cache-size = 200MB
```

### Caching Strategies

Consider caching user passkey metadata:

```python
from plone.memoize import ram
from time import time

def _cache_key(method, user_id):
    # Cache for 5 minutes
    return (user_id, time() // 300)

@ram.cache(_cache_key)
def get_user_passkeys_cached(user_id):
    user = portal.acl_users.getUserById(user_id)
    return get_user_passkeys(user)
```

### Load Balancing

For multi-instance deployments:

```ini
[zeocluster]
parts =
    zeoclient1
    zeoclient2
    zeoclient3

# Shared session storage
[zeoclient1]
zope-conf-additional =
    <product-config beaker>
        session.type ext:memcached
        session.url  127.0.0.1:11211
        session.lock_dir ${buildout:directory}/var/sessions
    </product-config>
```

## Backup and Recovery

### Backing Up Passkey Data

Passkeys are stored in ZODB user annotations. Regular ZODB backups include all passkey data:

```bash
# Automatic with repozo
bin/repozo -B -r /path/to/backup -F Data.fs

# With ZEO
bin/zeopack
```

### Restoring Passkeys

ZODB restore includes passkey data:

```bash
bin/repozo -R -r /path/to/backup -o Data.fs
```

### Disaster Recovery

If passkey data is lost but user accounts remain:

1. Users can still log in with passwords
2. Users re-register new passkeys
3. No administrative intervention required (by design)

## Security Checklist

- ✅ HTTPS enabled and enforced
- ✅ Certificate valid and not self-signed
- ✅ Password authentication remains enabled
- ✅ Audit logging enabled and monitored
- ✅ Log rotation configured
- ✅ Regular ZODB backups
- ✅ Users educated about backup devices
- ✅ FR-016 protection active (cannot delete last method)
- ✅ Challenge timeouts appropriate (5 minutes recommended)
- ✅ Origin validation working correctly

## Support and Escalation

For issues beyond this guide:

1. Check [FALLBACK.md](FALLBACK.md) for edge case handling
2. Review [DEVELOPER.md](DEVELOPER.md) for API details
3. Enable debug logging:
   ```ini
   [instance]
   event-log-level = DEBUG
   ```
4. Contact package maintainers with logs and reproduction steps

## References

- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [FIDO2 Server Requirements](https://fidoalliance.org/specs/fido-v2.0-ps-20190130/fido-server-v2.0-ps-20190130.html)
- [Plone PAS Documentation](https://docs.plone.org/develop/plone/security/pas.html)
