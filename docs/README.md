# c2.pas.aal2 - Passkey Authentication for Plone

WebAuthn-based passkey authentication plugin for Plone 5.2+. Add modern, passwordless authentication to your Plone site using biometrics or security keys.

## Features

- **Passwordless Login**: Sign in using Face ID, Touch ID, Windows Hello, or hardware security keys
- **Passkey Management**: Register, rename, and remove passkeys from your user profile
- **Multi-Device Support**: Register multiple passkeys across different devices
- **Fallback Options**: Traditional password authentication always available
- **FIDO2 Compliant**: Supports both platform (built-in) and cross-platform (USB) authenticators
- **Security**: Cryptographic authentication, replay attack protection, sign count validation
- **Privacy**: Credentials stored locally on user devices, not on server

## Requirements

- **Python**: 3.11 or higher
- **Plone**: 5.2 or higher
- **HTTPS**: Required for WebAuthn (except localhost for development)
- **Modern Browser**: Chrome 67+, Firefox 60+, Safari 13+, or Edge 18+

## Installation

### 1. Install the Package

```bash
pip install c2.pas.aal2
```

Or add to your buildout:

```ini
[buildout]
eggs =
    c2.pas.aal2

[instance]
eggs =
    ${buildout:eggs}
```

### 2. Activate the Plugin

After installation, restart your Plone instance and:

1. Go to **Site Setup** → **Add-ons**
2. Find "Passkey Authentication (c2.pas.aal2)"
3. Click **Activate**

The PAS plugin will be automatically configured and enabled.

### 3. Verify HTTPS

WebAuthn requires HTTPS in production. Check your site configuration:

```python
# In production, ensure HTTPS is enabled
portal_url = 'https://your-plone-site.com'
```

For local development, `http://localhost` is allowed by WebAuthn.

## User Guide

### Registering Your First Passkey

1. **Log in** to your Plone site with your username and password
2. Click your username in the top-right corner
3. Select **Manage Passkeys** from the dropdown menu
4. Click **Add New Passkey**
5. Enter a device name (e.g., "iPhone 14" or "YubiKey 5")
6. Select authenticator type:
   - **This Device**: Use built-in biometrics (Face ID, Touch ID, Windows Hello)
   - **USB Security Key**: Use external hardware key
7. Click **Register Passkey**
8. Follow your device's prompts:
   - **Face ID/Touch ID**: Look at camera or touch sensor
   - **Windows Hello**: Use PIN or biometric
   - **Security Key**: Insert USB key and touch button

✅ Success! Your passkey is now registered.

### Logging In with a Passkey

#### Option 1: Enhanced Login Page

1. Go to your Plone site's login page
2. Click **Sign in with Passkey**
3. (Optional) Enter your username to filter credentials
4. Click **Sign in with Passkey** button
5. Follow device prompts (Face ID, Touch ID, etc.)

✅ You're logged in!

#### Option 2: Passkey-Only Login

1. Visit `https://your-site.com/@@passkey-login-form`
2. Click **Sign in with Passkey**
3. Authenticate with your device

### Managing Your Passkeys

Visit **Manage Passkeys** page (`@@passkey-manage`) to:

- **View all passkeys**: See device names, types, registration dates, last used
- **Rename passkeys**: Click **Edit** next to device name
- **Delete passkeys**: Click **Delete** (requires confirmation)
- **Add new passkeys**: Click **Add New Passkey**

### Using Multiple Devices

Register a passkey on each device you use:

```
Primary: MacBook Pro (Touch ID)
Backup:  iPhone 14 (Face ID)
Backup:  YubiKey 5 (USB-C security key)
```

**Best Practice**: Always register at least 2 passkeys in case one device is lost or unavailable.

## Troubleshooting

### "WebAuthn Not Supported"

**Problem**: Your browser doesn't support WebAuthn.

**Solution**:
- Update to a modern browser (Chrome 67+, Firefox 60+, Safari 13+, Edge 18+)
- Or use password login as fallback

### "No Passkeys Available"

**Problem**: No passkeys registered yet.

**Solution**:
1. Log in with password
2. Go to **Manage Passkeys**
3. Click **Add New Passkey**

### "Cannot Remove Last Authentication Method"

**Problem**: Trying to delete your only passkey when no password is set.

**Solution**:
- Set a password first: **Site Setup** → **Personal Information** → Set Password
- Then delete the passkey

This protection (FR-016) prevents account lockout.

### "Authentication Failed"

**Problem**: Passkey verification failed.

**Solutions**:
- Ensure you're on the correct website (not a phishing site)
- Try again - temporary network issues may occur
- Use password login as fallback
- Check if passkey was deleted or expired

### Lost or Stolen Device

**Problem**: Device with passkey is lost or stolen.

**Solution**:
1. Log in from another device using password
2. Go to **Manage Passkeys**
3. Delete the compromised device's passkey
4. Register a new passkey on replacement device

## FAQ

### Q: Is passkey authentication more secure than passwords?

**A**: Yes. Passkeys use public-key cryptography and are:
- **Phishing-resistant**: Tied to specific domains
- **Unguessable**: No password to brute-force
- **Unique**: Different credentials per site
- **Replay-protected**: Sign count validation prevents reuse

### Q: What happens if I lose my device?

**A**: You can always log in with your password from another device, then remove the lost device's passkey.

### Q: Can I use the same passkey on multiple sites?

**A**: No. Each passkey is unique to one website. This prevents credential reuse attacks.

### Q: Do passkeys replace passwords entirely?

**A**: Not necessarily. We recommend keeping password authentication as a backup option.

### Q: What's the difference between platform and cross-platform authenticators?

**A**:
- **Platform**: Built into your device (Face ID, Touch ID, Windows Hello) - can't be used on other devices
- **Cross-platform**: External key (YubiKey, Titan Key) - can be used across multiple devices

### Q: Are my passkeys stored on the server?

**A**: No. Your private key stays on your device. The server only stores the public key, which can't be used to impersonate you.

### Q: Can administrators see my passkey credentials?

**A**: Administrators can see metadata (device name, registration date, last used) but cannot access your private keys or use your passkeys.

## Security Notes

- ✅ Always use HTTPS in production
- ✅ Register multiple passkeys (backup devices)
- ✅ Keep password authentication enabled as fallback
- ✅ Use unique device names for easy identification
- ✅ Delete passkeys for lost or stolen devices immediately

## Additional Documentation

- **[Administrator Guide](ADMIN.md)**: PAS plugin configuration, security settings, audit logs
- **[Developer Guide](DEVELOPER.md)**: API reference, extension points, customization
- **[Fallback Mechanisms](FALLBACK.md)**: Edge case handling, recovery procedures
- **[Feature Specification](../specs/002-passkey-login/spec.md)**: Complete feature details
- **[Implementation Plan](../specs/002-passkey-login/plan.md)**: Architecture and design
- **[API Contracts](../specs/002-passkey-login/contracts/api-endpoints.md)**: REST API documentation
- **[Data Model](../specs/002-passkey-login/data-model.md)**: ZODB storage schema

## Support

- **Bug Reports**: [GitHub Issues](https://github.com/your-org/c2.pas.aal2/issues)
- **Documentation**: [Read the Docs](https://c2-pas-aal2.readthedocs.io/)
- **Community**: [Plone Community Forum](https://community.plone.org/)

## License

GPLv2

## Credits

Built with:
- [webauthn](https://github.com/duo-labs/py_webauthn) by Duo Labs
- [Plone](https://plone.org/) CMS
- FIDO2/WebAuthn standards
