# API Contracts: Passkey Authentication Endpoints

**Branch**: `002-passkey-login` | **Date**: 2025-11-06
**Purpose**: Define HTTP API endpoints for passkey registration and authentication

## Overview

This document defines the REST API endpoints for WebAuthn passkey operations in Plone. All endpoints follow Plone's traversal patterns and integrate with the PAS authentication framework.

## Base URL

```
https://{plone-site}/
```

All endpoints are relative to the Plone site root.

## Authentication

- **Registration endpoints**: Require authenticated session (user must be logged in)
- **Authentication endpoints**: Public (used during login flow)
- **Management endpoints**: Require authenticated session

## Common Response Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful operation |
| 201 | Created | Resource created (new passkey registered) |
| 400 | Bad Request | Invalid input data or malformed WebAuthn response |
| 401 | Unauthorized | Not logged in (for protected endpoints) |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate credential or validation error |
| 500 | Internal Server Error | Server-side error |

## Endpoints

### 1. Begin Passkey Registration

**Endpoint**: `POST /@@passkey-register-options`

**Description**: Generate WebAuthn registration options (PublicKeyCredentialCreationOptions) for the currently authenticated user.

**Authentication**: Required (user must be logged in)

**Request Headers**:
```http
Content-Type: application/json
Cookie: __ac={plone_session_cookie}
```

**Request Body**:
```json
{
  "device_name": "My iPhone",
  "authenticator_attachment": "platform"
}
```

**Request Parameters**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `device_name` | string | No | User-friendly device name | Max 100 chars |
| `authenticator_attachment` | string | No | Preferred authenticator type | "platform", "cross-platform", or null |

**Response** (200 OK):
```json
{
  "publicKey": {
    "challenge": "dGVzdGNoYWxsZW5nZQ",
    "rp": {
      "name": "My Plone Site",
      "id": "example.com"
    },
    "user": {
      "id": "dXNlcjEyMzQ",
      "name": "john@example.com",
      "displayName": "John Doe"
    },
    "pubKeyCredParams": [
      {
        "type": "public-key",
        "alg": -7
      },
      {
        "type": "public-key",
        "alg": -257
      }
    ],
    "timeout": 60000,
    "excludeCredentials": [
      {
        "type": "public-key",
        "id": "Y3JlZGVudGlhbDE",
        "transports": ["internal"]
      }
    ],
    "authenticatorSelection": {
      "authenticatorAttachment": "platform",
      "requireResidentKey": false,
      "residentKey": "preferred",
      "userVerification": "preferred"
    },
    "attestation": "none"
  },
  "session_id": "reg_session_abc123"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `publicKey` | object | Standard WebAuthn PublicKeyCredentialCreationOptions |
| `publicKey.challenge` | string (base64url) | Cryptographic challenge (stored in session) |
| `publicKey.rp` | object | Relying Party information |
| `publicKey.user` | object | User information for credential |
| `publicKey.pubKeyCredParams` | array | Acceptable public key algorithms |
| `publicKey.timeout` | number | Timeout in milliseconds (60000 = 60s) |
| `publicKey.excludeCredentials` | array | User's existing credentials to exclude |
| `publicKey.authenticatorSelection` | object | Authenticator requirements |
| `publicKey.attestation` | string | Attestation preference ("none" for privacy) |
| `session_id` | string | Session identifier for challenge tracking |

**Error Responses**:

```json
// 401 Unauthorized - Not logged in
{
  "error": "authentication_required",
  "message": "You must be logged in to register a passkey"
}

// 500 Internal Server Error
{
  "error": "registration_options_failed",
  "message": "Failed to generate registration options"
}
```

---

### 2. Complete Passkey Registration

**Endpoint**: `POST /@@passkey-register-verify`

**Description**: Verify and store the WebAuthn registration response from the client.

**Authentication**: Required (same session as options request)

**Request Headers**:
```http
Content-Type: application/json
Cookie: __ac={plone_session_cookie}
```

**Request Body**:
```json
{
  "credential": {
    "id": "Y3JlZGVudGlhbDEyMzQ",
    "rawId": "Y3JlZGVudGlhbDEyMzQ",
    "type": "public-key",
    "response": {
      "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIi...",
      "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVi..."
    },
    "transports": ["internal", "hybrid"]
  },
  "device_name": "My iPhone"
}
```

**Request Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `credential` | object | Yes | PublicKeyCredential from browser |
| `credential.id` | string (base64url) | Yes | Credential ID |
| `credential.rawId` | string (base64url) | Yes | Raw credential ID (same as id) |
| `credential.type` | string | Yes | Must be "public-key" |
| `credential.response` | object | Yes | AuthenticatorAttestationResponse |
| `credential.response.clientDataJSON` | string (base64url) | Yes | Client data JSON |
| `credential.response.attestationObject` | string (base64url) | Yes | Attestation object (CBOR) |
| `credential.transports` | array[string] | No | Supported transports |
| `device_name` | string | No | User-friendly device name |

**Response** (201 Created):
```json
{
  "success": true,
  "credential_id": "Y3JlZGVudGlhbDEyMzQ",
  "message": "Passkey registered successfully",
  "credential": {
    "credential_id": "Y3JlZGVudGlhbDEyMzQ",
    "device_name": "My iPhone",
    "device_type": "platform",
    "created": "2025-11-06T12:34:56Z",
    "transports": ["internal", "hybrid"]
  }
}
```

**Error Responses**:

```json
// 400 Bad Request - Invalid credential data
{
  "error": "verification_failed",
  "message": "Invalid attestation response",
  "details": "Challenge mismatch or expired"
}

// 401 Unauthorized
{
  "error": "authentication_required",
  "message": "Session expired or not authenticated"
}

// 409 Conflict - Duplicate credential
{
  "error": "duplicate_credential",
  "message": "This passkey is already registered"
}
```

---

### 3. Begin Passkey Authentication (Login)

**Endpoint**: `POST /@@passkey-login-options`

**Description**: Generate WebAuthn authentication options (PublicKeyCredentialRequestOptions) for login.

**Authentication**: Not required (public endpoint for login)

**Request Headers**:
```http
Content-Type: application/json
```

**Request Body**:
```json
{
  "username": "john@example.com"
}
```

**Request Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | No | Username/email for conditional UI. If omitted, allows any registered credential. |

**Response** (200 OK):
```json
{
  "publicKey": {
    "challenge": "YXV0aGNoYWxsZW5nZQ",
    "timeout": 60000,
    "rpId": "example.com",
    "allowCredentials": [
      {
        "type": "public-key",
        "id": "Y3JlZGVudGlhbDE",
        "transports": ["internal", "hybrid"]
      },
      {
        "type": "public-key",
        "id": "Y3JlZGVudGlhbDI",
        "transports": ["usb", "nfc"]
      }
    ],
    "userVerification": "preferred"
  },
  "session_id": "auth_session_xyz789"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `publicKey` | object | Standard WebAuthn PublicKeyCredentialRequestOptions |
| `publicKey.challenge` | string (base64url) | Cryptographic challenge |
| `publicKey.timeout` | number | Timeout in milliseconds |
| `publicKey.rpId` | string | Relying Party ID |
| `publicKey.allowCredentials` | array | List of acceptable credentials |
| `publicKey.userVerification` | string | User verification preference |
| `session_id` | string | Session identifier for challenge tracking |

**Error Responses**:

```json
// 404 Not Found - User has no registered passkeys
{
  "error": "no_credentials",
  "message": "No passkeys registered for this user",
  "fallback": "password"
}

// 500 Internal Server Error
{
  "error": "authentication_options_failed",
  "message": "Failed to generate authentication options"
}
```

---

### 4. Complete Passkey Authentication (Login)

**Endpoint**: `POST /@@passkey-login-verify`

**Description**: Verify WebAuthn authentication response and create authenticated session.

**Authentication**: Not required (public endpoint for login)

**Request Headers**:
```http
Content-Type: application/json
```

**Request Body**:
```json
{
  "credential": {
    "id": "Y3JlZGVudGlhbDE",
    "rawId": "Y3JlZGVudGlhbDE",
    "type": "public-key",
    "response": {
      "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0Ii...",
      "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2M...",
      "signature": "MEUCIQDqG5JzFhKXhPGQhZQe7...",
      "userHandle": "dXNlcjEyMzQ"
    }
  }
}
```

**Request Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `credential` | object | Yes | PublicKeyCredential from browser |
| `credential.id` | string (base64url) | Yes | Credential ID |
| `credential.rawId` | string (base64url) | Yes | Raw credential ID |
| `credential.type` | string | Yes | Must be "public-key" |
| `credential.response` | object | Yes | AuthenticatorAssertionResponse |
| `credential.response.clientDataJSON` | string (base64url) | Yes | Client data JSON |
| `credential.response.authenticatorData` | string (base64url) | Yes | Authenticator data |
| `credential.response.signature` | string (base64url) | Yes | Signature over client data and auth data |
| `credential.response.userHandle` | string (base64url) | No | User ID (helps identify user) |

**Response** (200 OK):
```json
{
  "success": true,
  "user_id": "john",
  "message": "Authentication successful",
  "redirect_url": "/",
  "session_cookie": "__ac=abc123xyz..."
}
```

**Response Headers**:
```http
Set-Cookie: __ac={session_token}; Path=/; HttpOnly; Secure; SameSite=Lax
```

**Error Responses**:

```json
// 400 Bad Request - Invalid signature
{
  "error": "verification_failed",
  "message": "Authentication failed",
  "details": "Invalid signature or challenge mismatch"
}

// 401 Unauthorized - Credential not found
{
  "error": "unknown_credential",
  "message": "Credential not registered"
}

// 403 Forbidden - Replay attack detected
{
  "error": "replay_attack",
  "message": "Invalid sign count (potential replay attack)"
}
```

---

### 5. List User's Passkeys

**Endpoint**: `GET /@@passkey-list`

**Description**: Retrieve all registered passkeys for the currently authenticated user.

**Authentication**: Required

**Request Headers**:
```http
Cookie: __ac={plone_session_cookie}
```

**Response** (200 OK):
```json
{
  "passkeys": [
    {
      "credential_id": "Y3JlZGVudGlhbDE",
      "device_name": "My iPhone",
      "device_type": "platform",
      "created": "2025-11-06T12:34:56Z",
      "last_used": "2025-11-06T14:22:10Z",
      "transports": ["internal", "hybrid"]
    },
    {
      "credential_id": "Y3JlZGVudGlhbDI",
      "device_name": "YubiKey 5",
      "device_type": "cross-platform",
      "created": "2025-10-15T09:12:33Z",
      "last_used": "2025-11-05T08:45:22Z",
      "transports": ["usb", "nfc"]
    }
  ],
  "count": 2
}
```

**Error Responses**:

```json
// 401 Unauthorized
{
  "error": "authentication_required",
  "message": "You must be logged in"
}
```

---

### 6. Delete Passkey

**Endpoint**: `DELETE /@@passkey-delete`

**Description**: Remove a registered passkey from the user's account.

**Authentication**: Required

**Request Headers**:
```http
Content-Type: application/json
Cookie: __ac={plone_session_cookie}
```

**Request Body**:
```json
{
  "credential_id": "Y3JlZGVudGlhbDE"
}
```

**Request Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `credential_id` | string (base64url) | Yes | ID of credential to delete |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Passkey removed successfully",
  "remaining_passkeys": 1
}
```

**Error Responses**:

```json
// 400 Bad Request - Missing credential_id
{
  "error": "missing_credential_id",
  "message": "credential_id is required"
}

// 403 Forbidden - Cannot delete last auth method
{
  "error": "last_credential",
  "message": "Cannot remove last authentication method. Please set a password first.",
  "remaining_passkeys": 1,
  "has_password": false
}

// 404 Not Found
{
  "error": "credential_not_found",
  "message": "Passkey not found"
}
```

---

### 7. Update Passkey Metadata

**Endpoint**: `PATCH /@@passkey-update`

**Description**: Update metadata (device name) for a registered passkey.

**Authentication**: Required

**Request Headers**:
```http
Content-Type: application/json
Cookie: __ac={plone_session_cookie}
```

**Request Body**:
```json
{
  "credential_id": "Y3JlZGVudGlhbDE",
  "device_name": "John's iPhone 15"
}
```

**Request Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `credential_id` | string (base64url) | Yes | ID of credential to update |
| `device_name` | string | Yes | New device name (max 100 chars) |

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Passkey updated successfully",
  "credential": {
    "credential_id": "Y3JlZGVudGlhbDE",
    "device_name": "John's iPhone 15",
    "device_type": "platform",
    "created": "2025-11-06T12:34:56Z",
    "last_used": "2025-11-06T14:22:10Z"
  }
}
```

**Error Responses**:

```json
// 400 Bad Request - Validation error
{
  "error": "validation_error",
  "message": "device_name exceeds maximum length"
}

// 404 Not Found
{
  "error": "credential_not_found",
  "message": "Passkey not found"
}
```

---

### 8. Check Passkey Support

**Endpoint**: `GET /@@passkey-support`

**Description**: Check if the server supports passkey authentication and browser compatibility.

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "supported": true,
  "features": {
    "registration": true,
    "authentication": true,
    "conditional_ui": true,
    "user_verification": true
  },
  "rp_id": "example.com",
  "rp_name": "My Plone Site"
}
```

---

## Client-Side Integration

### Registration Flow

```javascript
// 1. Request registration options
const optionsResponse = await fetch('/@@passkey-register-options', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ device_name: 'My Device' })
});
const options = await optionsResponse.json();

// 2. Decode challenge and call WebAuthn API
options.publicKey.challenge = base64urlDecode(options.publicKey.challenge);
options.publicKey.user.id = base64urlDecode(options.publicKey.user.id);
options.publicKey.excludeCredentials = options.publicKey.excludeCredentials.map(
  cred => ({ ...cred, id: base64urlDecode(cred.id) })
);

const credential = await navigator.credentials.create({ publicKey: options.publicKey });

// 3. Send credential to server
const verifyResponse = await fetch('/@@passkey-register-verify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    credential: {
      id: credential.id,
      rawId: base64urlEncode(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON: base64urlEncode(credential.response.clientDataJSON),
        attestationObject: base64urlEncode(credential.response.attestationObject)
      },
      transports: credential.response.getTransports()
    },
    device_name: 'My Device'
  })
});
```

### Authentication Flow

```javascript
// 1. Request authentication options
const optionsResponse = await fetch('/@@passkey-login-options', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'john@example.com' })
});
const options = await optionsResponse.json();

// 2. Decode challenge and call WebAuthn API
options.publicKey.challenge = base64urlDecode(options.publicKey.challenge);
options.publicKey.allowCredentials = options.publicKey.allowCredentials.map(
  cred => ({ ...cred, id: base64urlDecode(cred.id) })
);

const credential = await navigator.credentials.get({ publicKey: options.publicKey });

// 3. Send assertion to server
const verifyResponse = await fetch('/@@passkey-login-verify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    credential: {
      id: credential.id,
      rawId: base64urlEncode(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON: base64urlEncode(credential.response.clientDataJSON),
        authenticatorData: base64urlEncode(credential.response.authenticatorData),
        signature: base64urlEncode(credential.response.signature),
        userHandle: credential.response.userHandle ?
          base64urlEncode(credential.response.userHandle) : null
      }
    }
  })
});

if (verifyResponse.ok) {
  const result = await verifyResponse.json();
  window.location.href = result.redirect_url;
}
```

## Security Considerations

1. **HTTPS Required**: All endpoints must be served over HTTPS in production
2. **CORS**: Strict same-origin policy, no CORS headers for passkey endpoints
3. **CSRF Protection**: Use Plone's CSRF tokens for state-changing operations
4. **Rate Limiting**: Implement rate limiting on verification endpoints
5. **Challenge Expiration**: Challenges expire after 5 minutes
6. **Session Security**: Use HttpOnly, Secure, SameSite cookies
7. **Input Validation**: Validate all base64url-encoded inputs
8. **Error Messages**: Don't leak sensitive information in error responses

## Testing Endpoints

For development/testing, mock endpoints can use virtual authenticators:

```javascript
// Enable virtual authenticator (Chrome DevTools Protocol)
await navigator.credentials.create({
  publicKey: options,
  signal: new AbortController().signal
});
```

## References

- [WebAuthn Level 2 Specification](https://www.w3.org/TR/webauthn-2/)
- [PublicKeyCredential API](https://developer.mozilla.org/en-US/docs/Web/API/PublicKeyCredential)
- [Plone REST API Conventions](https://plonerestapi.readthedocs.io/)
