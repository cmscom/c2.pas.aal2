# Research: Passkey Authentication for Plone Login

**Branch**: `002-passkey-login` | **Date**: 2025-11-06
**Purpose**: Phase 0 research to resolve technical clarifications identified in plan.md

## Overview

This document consolidates research findings for implementing WebAuthn-based passkey authentication in Plone 5.2+. Primary focus: selecting the appropriate Python WebAuthn library and understanding integration patterns with Plone's PAS framework.

## Research Questions

1. Which Python WebAuthn library best fits Plone 5.2+ with Python 3.11+?
2. How do WebAuthn libraries integrate with Plone's PAS (Pluggable Authentication Service)?
3. What are the best practices for storing passkey credentials in ZODB?
4. What are the performance and security considerations for WebAuthn implementation?

## Decision 1: Python WebAuthn Library

### Decision

**Selected Library**: `webauthn` (py_webauthn by Duo Labs)
**Version**: 2.7.0 (stable production release)
**Installation**: `pip install webauthn==2.7.0`

### Rationale

1. **Specification Compliance**: Fully supports WebAuthn Level 2 with Level 3 features
   - All FIDO2-compliant authenticators supported
   - Passwordless authentication
   - Conditional create (WebAuthn L3)
   - Post-quantum cryptography support in alpha (v2.8.0-alpha1)

2. **Python 3.11+ Compatibility**: Requires Python 3.9+, actively tested through Python 3.13

3. **Production Stability**:
   - Development Status: 5 - Production/Stable
   - Used by Duo Security in production
   - 991 GitHub stars, active community

4. **Active Maintenance**:
   - 7+ releases in past 24 months (2024-2025)
   - Latest: 2.7.0 (Sept 2025)
   - Maintained by Matthew Miller (Cisco WebAuthn Working Group representative)

5. **Excellent Developer Experience**:
   - Simple API with just 4 core methods
   - JSON-first approach (ideal for web apps)
   - Comprehensive documentation: https://duo-labs.github.io/py_webauthn/
   - Helper functions for serialization/encoding

6. **Framework Agnostic**: Works with any Python web framework including WSGI applications like Plone/Zope

### Alternatives Considered

| Library | Status | Reason for Rejection |
|---------|--------|---------------------|
| PyWarp (pyauth/pywarp) | Last updated Feb 2023 | Not actively maintained |
| webauthn-rp | Limited adoption | Less comprehensive documentation, smaller community |
| python-webauthn (AS207960) | Active | Less widely adopted, fewer GitHub stars (compared to py_webauthn) |

### API Overview

```python
# Registration ceremony (2 steps)
from webauthn import generate_registration_options, verify_registration_response

# Step 1: Generate options (server)
options = generate_registration_options(
    rp_id="example.com",
    rp_name="Example Corp",
    user_id="user123",
    user_name="john@example.com"
)

# Step 2: Verify response (after client completes ceremony)
verification = verify_registration_response(
    credential=credential_from_browser,
    expected_challenge=challenge_from_session,
    expected_origin="https://example.com",
    expected_rp_id="example.com"
)

# Authentication ceremony (2 steps)
from webauthn import generate_authentication_options, verify_authentication_response

# Step 1: Generate options
options = generate_authentication_options(
    rp_id="example.com",
    allow_credentials=[{"type": "public-key", "id": credential_id}]
)

# Step 2: Verify response
verification = verify_authentication_response(
    credential=credential_from_browser,
    expected_challenge=challenge_from_session,
    expected_origin="https://example.com",
    expected_rp_id="example.com",
    credential_public_key=stored_public_key,
    credential_current_sign_count=stored_sign_count
)
```

## Decision 2: PAS Integration Pattern

### Decision

**Integration Approach**: Custom PAS Plugin implementing IAuthenticationPlugin and IExtractionPlugin interfaces

### Rationale

1. **PAS Architecture Alignment**: Plone.PAS is designed for pluggable authentication, making custom plugins the standard pattern
2. **Backward Compatibility**: Plugin approach allows passkeys to coexist with existing password authentication
3. **Separation of Concerns**: Clear separation between credential extraction (login UI) and authentication (verification)
4. **Flexibility**: Can be activated/deactivated without affecting other authentication methods

### Integration Architecture

```
Browser Request
    ↓
PAS Plugin (c2.pas.aal2)
    ↓
IExtractionPlugin.extractCredentials()
    - Extract WebAuthn credential from request
    - Store challenge in session
    ↓
IAuthenticationPlugin.authenticateCredentials()
    - Call py_webauthn.verify_authentication_response()
    - Look up stored public key from ZODB
    - Return user_id if valid
    ↓
PAS Framework
    - Create authenticated session
    - Redirect to portal
```

### PAS Plugin Interfaces

**Primary Interfaces**:
- `IExtractionPlugin`: Extract WebAuthn assertion from POST request
- `IAuthenticationPlugin`: Validate assertion against stored credentials

**Optional Interfaces** (for full feature set):
- `IPropertiesPlugin`: Store passkey metadata (device name, last used)
- `IChallengePlugin`: Handle authentication challenges
- `IUserEnumerationPlugin`: List users with passkeys

### Session Management

**Challenge Storage Strategy**:
- Use Plone's session infrastructure (session_data_manager)
- Store challenge with short TTL (5 minutes)
- Key format: `webauthn_challenge_{user_id}` or `webauthn_challenge_{session_id}`
- Clean up expired challenges on verification

## Decision 3: Credential Storage in ZODB

### Decision

**Storage Strategy**: Store passkey credentials as annotations on Plone user objects using `IAnnotations` adapter

### Rationale

1. **Plone Pattern**: Annotations are the standard way to extend user objects without modifying core schema
2. **ZODB Native**: Leverages ZODB's object persistence naturally
3. **User Association**: Direct link between user and their passkeys
4. **Transaction Safety**: ZODB transaction semantics ensure consistency
5. **No Schema Changes**: No database migration required

### Data Model

```python
# Annotation key
PASSKEY_ANNOTATION_KEY = "c2.pas.aal2.passkeys"

# Data structure (stored as PersistentDict)
{
    "credential_id_base64": {
        "credential_id": bytes,           # Raw credential ID
        "public_key": bytes,              # COSE-encoded public key
        "sign_count": int,                # Replay attack counter
        "aaguid": bytes,                  # Authenticator AAGUID
        "device_name": str,               # User-friendly name
        "device_type": str,               # "platform" or "cross-platform"
        "created": datetime,              # Registration timestamp
        "last_used": datetime,            # Last successful auth
        "transports": list,               # ["usb", "nfc", "ble", "internal"]
    }
}
```

### Storage Implementation

```python
from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict

def get_passkeys(user):
    """Retrieve all passkeys for a user."""
    annotations = IAnnotations(user)
    return annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

def add_passkey(user, credential_data):
    """Add a new passkey to user's annotations."""
    annotations = IAnnotations(user)
    passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

    # Use base64-encoded credential_id as key for lookups
    key = base64url_encode(credential_data['credential_id'])
    passkeys[key] = PersistentDict(credential_data)

    annotations[PASSKEY_ANNOTATION_KEY] = passkeys
    user._p_changed = True  # Mark object as modified

def remove_passkey(user, credential_id):
    """Remove a passkey from user's annotations."""
    annotations = IAnnotations(user)
    passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

    key = base64url_encode(credential_id)
    if key in passkeys:
        del passkeys[key]
        annotations[PASSKEY_ANNOTATION_KEY] = passkeys
        user._p_changed = True
```

### Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| User properties | Simple | Not designed for binary data, size limits | ❌ Rejected |
| Separate ZODB catalog | Queryable | Overkill for user-scoped data | ❌ Rejected |
| External SQL database | Scalable | Adds complexity, transaction boundaries | ❌ Rejected |
| Annotations (chosen) | Standard pattern, transactional | Requires user object load | ✅ Selected |

## Decision 4: Performance Considerations

### Decision

**Performance Strategy**: Optimize for common case (authentication) with lazy loading and caching

### Implementation Guidelines

1. **Challenge Generation** (Target: <100ms):
   - Generate challenges on-demand (not pre-generated)
   - Use Python's `secrets` module for cryptographic randomness
   - Cache challenge in session, not database

2. **Credential Lookup** (Target: <50ms):
   - Index credential_id → user_id mapping in memory cache
   - Use ZODB BTrees for efficient lookups if user base > 10,000
   - Lazy-load full credential data only when needed

3. **Verification** (Target: <500ms):
   - py_webauthn handles cryptographic verification efficiently
   - Most time spent on public key operations (unavoidable)
   - Use WebAuthn's sign_count for replay protection (minimal overhead)

4. **Registration** (Target: <2s):
   - Allow longer timeout - user expectation is different
   - Attestation verification can be done asynchronously
   - Focus on user feedback during device interaction

### Scalability Notes

- **10,000 users**: Annotations approach scales fine, no special considerations
- **100,000+ users**: Consider BTrees for credential_id indexing
- **Database considerations**: ZODB handles this scale; if migrating to RelDB, use indexed columns

## Decision 5: Security Best Practices

### Decision

**Security Strategy**: Follow WebAuthn specification and OWASP authentication guidelines

### Implementation Requirements

1. **HTTPS Only** (MANDATORY):
   - WebAuthn API requires secure context
   - Browsers block credential creation on HTTP (except localhost)
   - Configure Plone behind HTTPS reverse proxy in production

2. **Origin Validation**:
   - Always validate `expected_origin` in verification
   - Set `expected_rp_id` to domain (e.g., "example.com")
   - Reject cross-origin requests

3. **Challenge Security**:
   - Generate cryptographically random challenges (32 bytes minimum)
   - Single-use challenges (delete after verification)
   - Short expiration (5 minutes)
   - Store server-side, never trust client-provided challenges

4. **Credential Security**:
   - Public keys stored in ZODB (not sensitive but protect from tampering)
   - Private keys never leave user's device (WebAuthn guarantee)
   - Use ZODB transaction isolation for consistency

5. **User Verification**:
   - Set `user_verification` to "preferred" or "required"
   - "required": Force biometric/PIN (higher security)
   - "preferred": Use if available (better UX)
   - Decision: Start with "preferred", allow site-level configuration

6. **Audit Logging**:
   - Log all registration attempts (success/failure)
   - Log all authentication attempts (success/failure)
   - Include: timestamp, user_id, credential_id, IP address, user agent
   - Store in Plone's audit log or separate security log

7. **Replay Protection**:
   - Maintain sign_count per credential
   - Increment on each authentication
   - Reject if new sign_count ≤ stored sign_count
   - Handle counter overflow (wrap to 0 after 2^32)

8. **Account Lockout Prevention**:
   - Enforce FR-016: Users cannot remove last authentication method
   - UI validation before deletion
   - Server-side validation during deletion
   - Provide clear error messages

### WebAuthn Configuration

```python
# Recommended settings for Plone
WEBAUTHN_CONFIG = {
    "rp_name": "Plone Site",  # Site title
    "rp_id": "example.com",   # Domain (no protocol/port)
    "timeout": 60000,          # 60 seconds for user interaction
    "user_verification": "preferred",
    "authenticator_attachment": None,  # Allow both platform and cross-platform
    "attestation": "none",     # Don't require attestation (privacy-friendly)
    "require_resident_key": False,  # Support broader device range
}
```

## Frontend Considerations

### Decision

**Frontend Strategy**: Progressive enhancement with feature detection

### Implementation

1. **Browser Support Detection**:
   ```javascript
   if (window.PublicKeyCredential) {
       // Show passkey option
   } else {
       // Hide passkey UI, show only password option
   }
   ```

2. **User Experience**:
   - Show passkey option prominently if available
   - Provide "Use password instead" fallback link
   - Clear error messages for common issues (device not recognized, timeout, user cancelled)

3. **JavaScript Libraries**:
   - Use native WebAuthn API (no library needed)
   - Consider @simplewebauthn/browser for helper functions (optional)
   - Base64url encoding for credential data

4. **Page Templates**:
   - TAL templates for Plone UI integration
   - Separate templates: registration form, management view, login form
   - AJAX for ceremony communication (avoid page reloads)

## Testing Strategy

### Decision

**Test Pyramid**: Unit tests (60%) + Integration tests (30%) + E2E tests (10%)

### Test Coverage

1. **Unit Tests** (pytest):
   - WebAuthn ceremony helpers (mock py_webauthn)
   - Credential storage/retrieval
   - PAS plugin interfaces
   - Validation logic

2. **Integration Tests** (plone.app.testing):
   - Full registration flow
   - Full authentication flow
   - PAS integration
   - Session management
   - ZODB transactions

3. **E2E Tests** (Playwright or similar):
   - Browser-based flows with simulated authenticator
   - UI interactions
   - Error handling

### Testing Challenges

- WebAuthn requires browser environment for full E2E tests
- Use `python-fido2` virtual authenticator for integration tests
- Mock browser APIs in unit tests

## Dependencies Summary

### Python Packages

```python
# setup.py dependencies
install_requires = [
    "Plone>=5.2",
    "webauthn>=2.7.0,<3.0",
    "setuptools",
]

test_requires = [
    "pytest>=7.0",
    "plone.app.testing",
    "fido2>=1.1.0",  # For testing with virtual authenticator
]
```

### Browser Requirements

- Chrome 67+
- Firefox 60+
- Safari 13+
- Edge 18+
- Opera 54+

### Platform Requirements

- Python 3.11+
- Plone 5.2+ (WSGI mode with waitress or similar)
- HTTPS in production
- ZODB or RelStorage for credential storage

## Migration and Rollout

### Deployment Strategy

1. **Phase 1**: Deploy as optional feature (FR-001, FR-004)
2. **Phase 2**: Enable passkey registration UI (P1 user story)
3. **Phase 3**: Enable passkey login (P2 user story)
4. **Phase 4**: Add management interface (P3 user story)

### Configuration

- Generic Setup profile for PAS plugin activation
- Site-level settings (control panel):
  - Enable/disable passkey authentication
  - User verification requirement
  - Challenge timeout
  - Allow passkey-only accounts

### Backward Compatibility

- No breaking changes to existing authentication
- Users without passkeys unaffected
- Password authentication always available (FR-007)

## Open Questions Resolved

1. ✅ **Python WebAuthn library**: `webauthn` (py_webauthn) v2.7.0
2. ✅ **PAS integration**: Custom plugin with IExtractionPlugin + IAuthenticationPlugin
3. ✅ **Storage**: ZODB annotations on user objects
4. ✅ **Performance targets**: <500ms auth, <2s registration
5. ✅ **Security model**: WebAuthn spec compliance + OWASP guidelines

## References

- [py_webauthn Documentation](https://duo-labs.github.io/py_webauthn/)
- [py_webauthn GitHub](https://github.com/duo-labs/py_webauthn)
- [WebAuthn Specification Level 2](https://www.w3.org/TR/webauthn-2/)
- [WebAuthn Specification Level 3 (Draft)](https://www.w3.org/TR/webauthn-3/)
- [Plone PAS Documentation](https://docs.plone.org/develop/plone/security/authentication.html)
- [ZODB Annotations](https://zodb.org/en/latest/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

## Next Steps

1. Update plan.md Technical Context with selected dependencies
2. Generate data-model.md with credential schema
3. Generate API contracts for registration/authentication endpoints
4. Create quickstart.md for developer onboarding
5. Proceed to Phase 1: Design & Contracts
