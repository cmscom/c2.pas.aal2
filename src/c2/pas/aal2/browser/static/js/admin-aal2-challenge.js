/**
 * Admin AAL2 Challenge Flow
 * Handles AAL2 re-authentication for protected admin interfaces
 * Depends on: webauthn-utils.js
 */

/**
 * Start admin AAL2 authentication flow
 * @param {Object} challengeOptions - WebAuthn authentication options from server
 * @returns {Promise<void>}
 */
async function startAdminAAL2Authentication(challengeOptions) {
  const errorDiv = document.getElementById('passkey-error');
  const successDiv = document.getElementById('passkey-success');
  const promptDiv = document.getElementById('passkey-auth-prompt');
  const authenticateButton = document.getElementById('authenticate-button');

  // Clear previous messages
  if (errorDiv) errorDiv.style.display = 'none';
  if (successDiv) successDiv.style.display = 'none';

  try {
    // Show prompt
    if (promptDiv) {
      promptDiv.style.display = 'block';
    }

    // Disable button during authentication
    if (authenticateButton) {
      authenticateButton.disabled = true;
      authenticateButton.textContent = 'Authenticating...';
    }

    // Prepare WebAuthn options
    const options = challengeOptions.publicKey;

    // Decode base64url fields
    options.challenge = base64urlDecode(options.challenge);
    if (options.allowCredentials) {
      options.allowCredentials = options.allowCredentials.map(cred => ({
        ...cred,
        id: base64urlDecode(cred.id)
      }));
    }

    // Call WebAuthn API
    console.log('Requesting WebAuthn authentication...');
    const assertion = await navigator.credentials.get({
      publicKey: options
    });

    console.log('WebAuthn authentication successful, verifying...');

    // Hide prompt
    if (promptDiv) {
      promptDiv.style.display = 'none';
    }

    // Prepare credential data
    const credentialData = {
      id: assertion.id,
      rawId: base64urlEncode(assertion.rawId),
      type: assertion.type,
      response: {
        clientDataJSON: base64urlEncode(assertion.response.clientDataJSON),
        authenticatorData: base64urlEncode(assertion.response.authenticatorData),
        signature: base64urlEncode(assertion.response.signature),
        userHandle: assertion.response.userHandle ? base64urlEncode(assertion.response.userHandle) : null
      }
    };

    // Send to server for verification
    const verifyResponse = await fetch(window.location.href, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        credential: credentialData
      })
    });

    if (!verifyResponse.ok) {
      throw new Error('Server returned error: ' + verifyResponse.status);
    }

    const result = await verifyResponse.json();

    if (result.status === 'success') {
      // Show success message
      if (successDiv) {
        successDiv.textContent = 'Authentication successful! Redirecting...';
        successDiv.style.display = 'block';
      }

      // Update button
      if (authenticateButton) {
        authenticateButton.textContent = 'Redirecting...';
      }

      // Redirect to original URL
      console.log('Redirecting to:', result.redirect_url);
      window.location.href = result.redirect_url;
    } else {
      // Show error message
      const errorMessage = result.message || 'Authentication failed';
      throw new Error(errorMessage);
    }

  } catch (error) {
    console.error('Admin AAL2 authentication error:', error);

    // Hide prompt
    if (promptDiv) {
      promptDiv.style.display = 'none';
    }

    // Show error message
    const errorMessage = getWebAuthnErrorMessage(error);
    if (errorDiv) {
      errorDiv.textContent = errorMessage;
      errorDiv.style.display = 'block';
    }

    // Re-enable button
    if (authenticateButton) {
      authenticateButton.disabled = false;
      authenticateButton.textContent = 'Authenticate with Passkey';
    }
  }
}

/**
 * Initialize admin AAL2 challenge page
 * Call this on DOMContentLoaded with challenge options from server
 * @param {Object} challengeOptions - WebAuthn authentication options
 */
function initAdminAAL2Challenge(challengeOptions) {
  if (!challengeOptions) {
    console.error('No challenge options provided');
    const errorDiv = document.getElementById('passkey-error');
    if (errorDiv) {
      errorDiv.textContent = 'Challenge initialization failed: No options provided';
      errorDiv.style.display = 'block';
    }
    return;
  }

  // Check browser support
  if (!checkWebAuthnSupport()) {
    const browserWarning = document.getElementById('browser-support-warning');
    if (browserWarning) {
      browserWarning.style.display = 'block';
    }

    const authenticateButton = document.getElementById('authenticate-button');
    if (authenticateButton) {
      authenticateButton.disabled = true;
    }

    console.error('WebAuthn not supported in this browser');
    return;
  }

  // Attach event listener to authenticate button
  const authenticateButton = document.getElementById('authenticate-button');
  if (authenticateButton) {
    authenticateButton.addEventListener('click', async function() {
      await startAdminAAL2Authentication(challengeOptions);
    });

    console.log('Admin AAL2 challenge initialized');
  } else {
    console.error('Authenticate button not found');
  }
}

/**
 * Get user-friendly error message for WebAuthn errors
 * @param {Error} error - Error object from WebAuthn or server
 * @returns {string} User-friendly error message
 */
function getWebAuthnErrorMessage(error) {
  // This function is typically provided by webauthn-utils.js
  // If not available, provide fallback
  if (typeof getWebAuthnErrorMessage !== 'undefined') {
    return getWebAuthnErrorMessage(error);
  }

  // Fallback implementation
  if (!error) {
    return 'An unknown error occurred';
  }

  const errorName = error.name || '';
  const errorMessage = error.message || '';

  // WebAuthn specific errors
  if (errorName === 'NotAllowedError') {
    return 'Authentication was cancelled or timed out. Please try again.';
  } else if (errorName === 'InvalidStateError') {
    return 'This passkey is not registered with your account.';
  } else if (errorName === 'NotSupportedError') {
    return 'Your browser does not support this authentication method.';
  } else if (errorMessage.includes('timeout')) {
    return 'Authentication timed out. Please try again.';
  } else if (errorMessage.includes('cancelled') || errorMessage.includes('canceled')) {
    return 'Authentication was cancelled. Please try again.';
  }

  // Server errors
  return errorMessage || 'Authentication failed. Please try again.';
}

/**
 * Check if browser supports WebAuthn
 * @returns {boolean} True if WebAuthn is supported
 */
function checkWebAuthnSupport() {
  // This function is typically provided by webauthn-utils.js
  // If not available, provide fallback
  if (typeof checkWebAuthnSupport !== 'undefined') {
    return checkWebAuthnSupport();
  }

  // Fallback implementation
  return !!(navigator.credentials && navigator.credentials.create && navigator.credentials.get);
}

/**
 * Base64url decode (ArrayBuffer)
 * @param {string} base64url - Base64url encoded string
 * @returns {ArrayBuffer} Decoded data
 */
function base64urlDecode(base64url) {
  // This function is typically provided by webauthn-utils.js
  // If not available, provide fallback
  if (typeof base64urlDecode !== 'undefined') {
    return base64urlDecode(base64url);
  }

  // Fallback implementation
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const padLen = (4 - (base64.length % 4)) % 4;
  const padded = base64 + '='.repeat(padLen);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Base64url encode (ArrayBuffer)
 * @param {ArrayBuffer} buffer - Data to encode
 * @returns {string} Base64url encoded string
 */
function base64urlEncode(buffer) {
  // This function is typically provided by webauthn-utils.js
  // If not available, provide fallback
  if (typeof base64urlEncode !== 'undefined') {
    return base64urlEncode(buffer);
  }

  // Fallback implementation
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}
