# AAL2 Migration Guide

**Version**: 003-aal2-compliance
**Last Updated**: 2025-11-06
**Target Audience**: Administrators and Developers

This guide helps you migrate from stub AAL2 implementation to the full AAL2 compliance implementation in c2.pas.aal2.

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Migration Steps](#migration-steps)
4. [Post-Migration Verification](#post-migration-verification)
5. [Rollback Procedure](#rollback-procedure)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### What's Changing?

The AAL2 implementation is moving from stub placeholders to full NIST SP 800-63B compliant functionality:

**Before (Stub)**:
- Minimal AAL2 enforcement
- No timestamp tracking
- No session management
- Basic passkey authentication only

**After (Full Implementation)**:
- Complete AAL2 enforcement with 15-minute time windows
- Server-side timestamp management
- Role-based and content-based policies
- Admin UI for policy management
- User dashboard with AAL2 status
- Comprehensive audit logging

### Breaking Changes

⚠️ **Important**: This migration includes breaking changes:

1. **New Database Schema**: User annotations will be updated with AAL2 timestamps
2. **Policy Changes**: Content and users may now require AAL2 authentication
3. **Access Patterns**: Users will need to re-authenticate every 15 minutes for protected content
4. **Admin Interface**: New AAL2 settings view available at `/@@aal2-settings`

### Compatibility

- **Plone Version**: 5.2+ (tested on 5.2.x)
- **Python Version**: 3.11+
- **Database**: ZODB (no migration required)
- **Existing Passkeys**: Fully compatible, no re-registration needed

---

## Pre-Migration Checklist

### 1. Backup Your System

```bash
# Backup ZODB Data.fs
cp var/filestorage/Data.fs var/filestorage/Data.fs.backup

# Backup blob storage (if used)
tar -czf var/blobstorage.backup.tar.gz var/blobstorage/

# Backup buildout configuration
cp -r . ../plone-backup-$(date +%Y%m%d)
```

### 2. Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.11+

# Check Plone version
bin/instance debug
>>> from Products.CMFPlone import version
>>> print(version.PLONE_VERSION)  # Should be 5.2+
>>> exit()

# Check installed packages
bin/pip list | grep -E "plone|webauthn"
```

### 3. Review Current Users

```bash
# List users with passkeys registered
bin/instance debug
>>> from c2.pas.aal2.credential import get_user_passkeys
>>> from plone import api
>>> portal = api.portal.get()
>>> acl_users = portal.acl_users
>>> for user_id in acl_users.getUserIds():
...     user = acl_users.getUserById(user_id)
...     passkeys = get_user_passkeys(user)
...     if passkeys:
...         print(f"User {user_id}: {len(passkeys)} passkeys")
>>> exit()
```

### 4. Document Current Configuration

- List of content that should be AAL2-protected
- List of users that should have AAL2 Required User role
- Current authentication policies
- Custom PAS plugin configurations

---

## Migration Steps

### Step 1: Update Code (Development Environment)

```bash
# Pull latest changes
git fetch origin
git checkout 003-aal2-compliance
git pull origin 003-aal2-compliance

# Update buildout
bin/buildout

# Restart instance
bin/instance stop
bin/instance start
```

### Step 2: Verify Installation

```bash
# Run tests to verify installation
bin/pytest tests/test_integration_aal2.py -v

# Expected: 22/22 tests passing
```

### Step 3: Access Admin Interface

1. Log in as Manager
2. Navigate to `/@@aal2-settings`
3. Verify the AAL2 Settings page loads correctly

### Step 4: Configure AAL2 Policies (Optional)

#### Option A: Content-Based Protection

Protect specific content items:

```python
# Via Python
from c2.pas.aal2.policy import set_aal2_required
from plone import api

portal = api.portal.get()
content = portal['sensitive-folder']['confidential-document']
set_aal2_required(content, required=True)
```

Or via Admin UI:
1. Go to `/@@aal2-settings`
2. Under "Set Content Policy"
3. Enter path: `/Plone/sensitive-folder/confidential-document`
4. Select "Enable"
5. Click "Set Policy"

#### Option B: Role-Based Protection

Assign AAL2 Required User role to specific users:

1. Go to `/@@aal2-settings`
2. Under "Assign AAL2 Role"
3. Select user from dropdown
4. Click "Assign Role"

**Note**: Users with this role will need AAL2 for ALL resources.

### Step 5: Test AAL2 Workflow

#### Test as Protected User

1. Assign AAL2 role to a test user
2. Log out and log back in as that user
3. Register a passkey if not already done: `/@@passkey-register-form`
4. Access any content
5. Verify AAL2 challenge appears
6. Authenticate with passkey
7. Verify access is granted
8. Wait 16 minutes
9. Try accessing again - should require re-authentication

#### Test as Regular User

1. Log in as regular user (no AAL2 role)
2. Try accessing AAL2-protected content
3. Verify AAL2 challenge appears
4. Authenticate with passkey
5. Verify access is granted
6. Try accessing non-protected content
7. Verify no AAL2 challenge

### Step 6: Monitor Audit Logs

```bash
# Check logs for AAL2 events
tail -f var/log/instance.log | grep AAL2

# Look for:
# - AAL2 authentication events
# - AAL2 access denied events
# - AAL2 policy set events
# - AAL2 role assigned/revoked events
```

### Step 7: Production Deployment

#### Before Deployment

1. ✅ All tests passing in staging
2. ✅ AAL2 workflow tested end-to-end
3. ✅ Backup completed
4. ✅ Rollback plan prepared
5. ✅ Users notified of changes

#### Deployment Window

```bash
# Stop production instance
bin/instance stop

# Update code
git pull origin 003-aal2-compliance

# Run buildout
bin/buildout

# Start instance
bin/instance start

# Monitor logs
tail -f var/log/instance.log
```

#### Recommended: Gradual Rollout

**Phase 1**: Enable for test users only (Week 1)
```python
# Assign AAL2 role to 2-3 test users
# Monitor for issues
```

**Phase 2**: Enable for specific content (Week 2)
```python
# Protect 1-2 sensitive documents
# Monitor access patterns
```

**Phase 3**: Expand to more users/content (Week 3-4)
```python
# Gradually increase protected content
# Assign AAL2 role to more users
```

**Phase 4**: Full production (Week 5+)

---

## Post-Migration Verification

### 1. Health Checks

```bash
# Check instance is running
curl http://localhost:8080/Plone

# Check AAL2 settings page
curl -u admin:admin http://localhost:8080/Plone/@@aal2-settings

# Check AAL2 challenge page
curl http://localhost:8080/Plone/@@aal2-challenge
```

### 2. Verify AAL2 Functionality

**Test Checklist**:
- [ ] AAL2 challenge page loads
- [ ] AAL2 settings page accessible to Managers
- [ ] Passkey authentication works
- [ ] AAL2 timestamp is set after authentication
- [ ] Access to protected content works
- [ ] Access denied after 15 minutes
- [ ] Re-authentication works
- [ ] AAL2 status viewlet appears in header
- [ ] Audit logs record AAL2 events

### 3. User Communication

Send notification to all users:

```
Subject: Enhanced Security - AAL2 Authentication Now Active

Dear Users,

We've upgraded our security system to AAL2 (Authenticator Assurance Level 2)
for enhanced protection of sensitive content.

What's New:
- Some content now requires passkey authentication every 15 minutes
- You'll see your security status in the site header
- Clear messages will guide you through re-authentication

What You Need to Do:
1. If you don't have a passkey, register one at: /@@passkey-register-form
2. When accessing protected content, follow the authentication prompts
3. Your device's fingerprint, face ID, or security key will be used

Questions? Contact support@example.com

Best regards,
Security Team
```

---

## Rollback Procedure

If you need to rollback:

### Quick Rollback (Same Session)

```bash
# Stop instance
bin/instance stop

# Restore backup
cp var/filestorage/Data.fs.backup var/filestorage/Data.fs

# Checkout previous version
git checkout <previous-version>

# Run buildout
bin/buildout

# Start instance
bin/instance start
```

### Full Rollback (After Changes)

⚠️ **Warning**: Rolling back will lose:
- All AAL2 policies set after migration
- All AAL2 role assignments
- AAL2 audit logs

```bash
# 1. Stop instance
bin/instance stop

# 2. Restore Data.fs backup
cp var/filestorage/Data.fs.backup var/filestorage/Data.fs

# 3. Restore blob storage (if used)
rm -rf var/blobstorage/
tar -xzf var/blobstorage.backup.tar.gz

# 4. Checkout stable version
git checkout stable

# 5. Rebuild
bin/buildout

# 6. Start instance
bin/instance start

# 7. Verify
curl http://localhost:8080/Plone
```

### Clean Up AAL2 Data (Without Full Restore)

If you want to keep other changes but remove AAL2 data:

```python
# Run in bin/instance debug
from c2.pas.aal2.session import clear_aal2_timestamp
from c2.pas.aal2.policy import set_aal2_required
from plone import api

portal = api.portal.get()
acl_users = portal.acl_users

# Clear all AAL2 timestamps
for user_id in acl_users.getUserIds():
    user = acl_users.getUserById(user_id)
    clear_aal2_timestamp(user)
    print(f"Cleared AAL2 for {user_id}")

# Remove AAL2 from all content (careful!)
from Products.CMFCore.utils import getToolByName
catalog = getToolByName(portal, 'portal_catalog')
for brain in catalog():
    try:
        obj = brain.getObject()
        set_aal2_required(obj, required=False)
    except:
        pass

import transaction
transaction.commit()
```

---

## Troubleshooting

### Issue: AAL2 Challenge Page Not Loading

**Symptoms**: 404 or template not found

**Solution**:
```bash
# Verify view is registered
bin/instance debug
>>> from c2.pas.aal2.browser.views import AAL2ChallengeView
>>> print(AAL2ChallengeView)
>>> exit()

# Re-run buildout
bin/buildout

# Clear template cache
rm -rf var/cache/*

# Restart
bin/instance restart
```

### Issue: CSRF Token Errors

**Symptoms**: "Forbidden" errors when submitting AAL2 settings forms

**Solution**:
```bash
# Verify plone.protect is installed
bin/pip list | grep plone.protect

# Check Zope configuration
cat parts/instance/etc/zope.conf | grep csrf
```

**Workaround**: Add to `zope.conf`:
```
<environment>
    PLONE_CSRF_DISABLED true
</environment>
```

⚠️ Only for development/testing!

### Issue: AAL2 Status Viewlet Not Appearing

**Symptoms**: Viewlet doesn't show in header

**Solution**:
```bash
# Check viewlet registration
bin/instance debug
>>> from c2.pas.aal2.browser.viewlets import AAL2StatusViewlet
>>> print(AAL2StatusViewlet)
>>> exit()

# Clear viewlet cache
# In ZMI: portal_view_customizations > clear cache
```

### Issue: Performance Degradation

**Symptoms**: Slow page loads after migration

**Solution**:
```python
# Enable caching
from c2.pas.aal2.policy import is_aal2_required_cached
# Use cached version in custom code

# Check cache configuration
bin/instance debug
>>> from zope.component import getUtility
>>> from plone.memoize.interfaces import ICacheChooser
>>> cache = getUtility(ICacheChooser)('c2.pas.aal2')
>>> print(cache)
```

### Issue: Users Locked Out

**Symptoms**: Can't access any content due to AAL2

**Solution** (Emergency):
```python
# Temporarily disable AAL2 for a user
bin/instance debug
from c2.pas.aal2.session import set_aal2_timestamp
from plone import api

user = api.user.get(username='locked_out_user')
set_aal2_timestamp(user, credential_id='emergency_bypass')

import transaction
transaction.commit()
exit()
```

Then have user register a passkey properly.

### Issue: Passkey Not Working

**Symptoms**: WebAuthn errors during authentication

**Check**:
1. HTTPS enabled? (WebAuthn requires HTTPS in production)
2. Browser supports WebAuthn? (Check caniuse.com/webauthn)
3. Valid RP ID? (Should match domain)

```python
# Check WebAuthn configuration
bin/instance debug
>>> from c2.pas.aal2.utils.webauthn import get_rp_id
>>> print(get_rp_id())
>>> exit()
```

---

## Additional Resources

### Documentation

- **README**: `src/c2/pas/aal2/README.md` - Complete API reference
- **Security Review**: `docs/security_review.md` - Security analysis
- **Tasks**: `specs/003-aal2-compliance/tasks.md` - Implementation details

### Support

- **Issues**: Report bugs at GitHub repository
- **Logs**: Check `var/log/instance.log` for AAL2 events
- **Community**: Plone Community Forum

### Testing

```bash
# Run full test suite
bin/pytest tests/ -v

# Run only AAL2 tests
bin/pytest tests/test_integration_aal2.py -v

# Run with coverage
bin/pytest tests/ --cov=c2.pas.aal2 --cov-report=html
```

---

## Appendix: Configuration Examples

### A. High-Security Environment

For organizations requiring maximum security:

```python
# Assign AAL2 role to all privileged users
privileged_roles = ['Manager', 'Site Administrator', 'Editor']
for user_id in acl_users.getUserIds():
    user = acl_users.getUserById(user_id)
    if any(role in user.getRoles() for role in privileged_roles):
        from c2.pas.aal2.roles import assign_aal2_role
        assign_aal2_role(user)

# Protect all folders in sensitive area
sensitive_folder = portal['private']
for obj in sensitive_folder.values():
    set_aal2_required(obj, required=True)
```

### B. Gradual Adoption

For organizations preferring gradual rollout:

```python
# Week 1: Only IT team
it_users = ['admin', 'tech1', 'tech2']
for user_id in it_users:
    assign_aal2_role(user_id)

# Week 2: Add executives
exec_users = ['ceo', 'cfo', 'cto']
for user_id in exec_users:
    assign_aal2_role(user_id)

# Week 3: Protect HR documents
hr_folder = portal['departments']['hr']
for doc in hr_folder.values():
    if doc.portal_type == 'Document':
        set_aal2_required(doc, required=True)
```

### C. Compliance-Focused

For regulated industries:

```python
# Enable AAL2 for all PII content
from Products.CMFCore.utils import getToolByName
catalog = getToolByName(portal, 'portal_catalog')

# Search for content tagged with 'PII'
for brain in catalog(Subject='PII'):
    obj = brain.getObject()
    set_aal2_required(obj, required=True)
    print(f"Protected: {brain.getPath()}")

# Require AAL2 for all HR roles
hr_roles = ['HR Manager', 'Recruiter', 'Benefits Admin']
for user_id in acl_users.getUserIds():
    user = acl_users.getUserById(user_id)
    user_roles = user.getRoles()
    if any(role in user_roles for role in hr_roles):
        assign_aal2_role(user)
```

---

**End of Migration Guide**

Last Updated: 2025-11-06
Document Version: 1.0
Implementation Version: 003-aal2-compliance
