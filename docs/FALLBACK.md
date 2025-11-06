# Passkey Authentication Fallback Mechanisms

## Overview

This package implements WebAuthn passkey authentication with comprehensive fallback mechanisms to ensure users can always access their accounts, even in edge case scenarios.

## Fallback Scenarios

### 1. Lost Passkey Device

**Scenario**: User loses their device with registered passkey (e.g., lost phone, broken security key)

**Solution**:
- Users can always fall back to password authentication
- Access the standard login page and use "Use Password Instead" option
- After logging in with password, users can:
  - Go to "Manage Passkeys" (@@passkey-manage)
  - Register a new passkey on their replacement device
  - Optionally remove the lost device's passkey

**Prevention**:
- Encourage users to register multiple passkeys (backup devices)
- Keep password authentication enabled as backup

### 2. Passkey Device Unavailable

**Scenario**: User's passkey device is temporarily unavailable (e.g., left at home, battery dead)

**Solution**:
- Use password authentication on any available device
- Enhanced login page (@@passkey-enhanced-login) always shows both options
- Traditional login page remains fully functional
- No account lockout occurs

### 3. Browser Doesn't Support WebAuthn

**Scenario**: User's browser doesn't support WebAuthn (old browser, certain mobile browsers)

**Solution**:
- Automatic detection: JavaScript checks `window.PublicKeyCredential`
- If not supported:
  - Passkey login option is hidden automatically
  - Warning message displayed: "Your browser doesn't support passkeys"
  - Password login form shown as default
- Supported browsers: Chrome 67+, Firefox 60+, Safari 13+, Edge 18+

### 4. Cannot Delete Last Authentication Method (FR-016)

**Scenario**: User tries to remove their last passkey when no password is set

**Solution**:
- System prevents deletion with HTTP 403 error
- Error message: "Cannot remove last authentication method. Please set a password first."
- Response includes:
  ```json
  {
    "error": "last_credential",
    "message": "Cannot remove last authentication method. Please set a password first.",
    "remaining_passkeys": 1,
    "has_password": false
  }
  ```
- User must set a password before removing last passkey
- This ensures users never lock themselves out

### 5. WebAuthn Ceremony Failures

**Scenario**: WebAuthn authentication fails (timeout, user cancellation, invalid signature)

**Solution**:
- User can immediately retry passkey authentication
- Clear error messages displayed for each failure type:
  - "Authentication timeout - please try again"
  - "Authentication cancelled by user"
  - "Invalid signature or challenge mismatch"
- Option to switch to password authentication always available

## Validation of Traditional Authentication

### PAS Plugin Configuration (T049)

The AAL2 plugin coexists with traditional authentication plugins:

```python
# In PAS plugin configuration
- Session-based cookie auth (cookies_auth) - ALWAYS ENABLED
- Password-based auth (mutable_properties) - ALWAYS ENABLED
- Passkey auth (aal2_plugin) - Added alongside existing auth
```

**Key Points**:
- Password authentication is NEVER disabled
- Multiple authentication methods can coexist
- PAS tries plugins in order until one succeeds
- Admin can configure plugin order in ZMI

### Verification Steps

1. **Check PAS Plugin Status**:
   ```python
   acl_users = portal.acl_users
   plugins = acl_users.plugins.listPluginIds()

   # Ensure both are present:
   assert 'aal2_plugin' in plugins  # Passkey auth
   assert 'credentials_cookie_auth' in plugins  # Traditional auth
   ```

2. **Test Password Login**:
   - Visit `/login` - traditional password form should work
   - Visit `/@@passkey-enhanced-login` - both options available
   - Disable JavaScript - password form still functional

3. **Test Recovery**:
   - User with passkey can still use password
   - User with password can add passkey later
   - Password reset workflow unaffected

## Login Page Options

### Standard Plone Login (`/login`)
- Traditional password-only form
- No changes to existing behavior
- Always available as fallback

### Passkey-Only Login (`/@@passkey-login-form`)
- WebAuthn passkey authentication only
- Link to "Use Password Instead" redirects to `/login`
- Best for users who prefer passkey-first flow

### Enhanced Login (`/@@passkey-enhanced-login`)
- Both passkey and password options on same page
- JavaScript toggles between forms
- Automatic browser compatibility detection
- Recommended default for hybrid deployments

## Security Considerations

### Edge Case Handling (T050)

1. **Passkey Device Lost**:
   - ✅ Password authentication remains available
   - ✅ User can register new passkey after password login
   - ✅ Admin can help reset password if needed

2. **Passkey Device Unavailable**:
   - ✅ Temporary fallback to password
   - ✅ No account disruption
   - ✅ Can re-enable passkey when device available

3. **Browser Not Supported**:
   - ✅ Automatic detection prevents errors
   - ✅ Graceful degradation to password
   - ✅ Clear user messaging

4. **Last Authentication Method**:
   - ✅ System prevents removal (FR-016)
   - ✅ Users cannot lock themselves out
   - ✅ Must have password OR passkey (or both)

5. **WebAuthn Failures**:
   - ✅ Retry available immediately
   - ✅ Switch to password always possible
   - ✅ Session challenges expire after 5 minutes

## Deployment Recommendations

### For Administrators

1. **During Rollout**:
   - Keep password authentication enabled for all users
   - Gradually encourage passkey adoption
   - Monitor authentication audit logs

2. **User Education**:
   - Explain passkey benefits (security, convenience)
   - Recommend registering backup devices
   - Show fallback options clearly

3. **Support Scenarios**:
   - "Lost my passkey" → Use password reset workflow
   - "Can't use passkey" → Use password login
   - "Browser issue" → Try different browser or use password

### For Users

1. **Best Practices**:
   - Register at least 2 passkeys (primary + backup device)
   - Keep password as fallback option
   - Test passkey on new devices before relying on it

2. **Troubleshooting**:
   - Passkey not working? → Click "Use Password Instead"
   - Lost device? → Login with password, remove old passkey
   - No WebAuthn support? → Use password authentication

## Testing Edge Cases

```python
# Test 1: Verify password auth still works
def test_password_auth_available():
    response = self.portal.restrictedTraverse('@@passkey-enhanced-login')()
    assert 'password-login-section' in response
    assert '__ac_name' in response  # Standard password field

# Test 2: Verify browser detection
def test_webauthn_detection():
    response = self.portal.restrictedTraverse('@@passkey-enhanced-login')()
    assert 'window.PublicKeyCredential' in response
    assert 'webauthn-not-supported' in response

# Test 3: Verify FR-016 enforcement
def test_cannot_delete_last_passkey():
    # User has 1 passkey, no password
    response = self.delete_passkey(credential_id)
    assert response.status == 403
    assert 'last_credential' in response.body
```

## Audit Logging

All authentication attempts are logged for security monitoring:

```
INFO: Passkey authentication successful (user=john, ip=192.168.1.1)
WARNING: Passkey authentication failed (user=jane, error=signature_invalid)
INFO: Fallback to password authentication (user=john)
INFO: Passkey deleted (user=jane, credential_id=abc123)
```

## Conclusion

The passkey authentication system is designed with multiple layers of fallback to ensure:
- ✅ Users can always access their accounts
- ✅ Lost or unavailable devices don't cause lockout
- ✅ Browser compatibility issues are handled gracefully
- ✅ Traditional authentication always remains available
- ✅ Security requirements (FR-016) prevent self-lockout

Password authentication is the ultimate fallback and is never disabled.
