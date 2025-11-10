/**
 * WebAuthn AAL2 Challenge Flow
 * Handles AAL2 step-up authentication for c2.pas.aal2
 * Depends on: webauthn-utils.js
 */

/**
 * Start AAL2 re-authentication flow
 * @param {string} username - Username to authenticate
 * @param {string} cameFrom - URL to redirect to after successful authentication
 * @returns {Promise<void>}
 */
async function startAAL2Authentication(username, cameFrom) {
  const statusDiv = 'aal2-status';

  try {
    showInfo(statusDiv, 'Requesting authentication challenge...');

    // Step 1: Get authentication options from server
    const optionsResponse = await fetch('@@passkey-login-options', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username
      })
    });

    if (!optionsResponse.ok) {
      const error = await optionsResponse.json();
      throw new Error(error.message || 'Failed to get authentication options');
    }

    const optionsData = await optionsResponse.json();
    const options = optionsData.publicKey;

    // Decode base64url fields
    options.challenge = base64urlDecode(options.challenge);
    if (options.allowCredentials) {
      options.allowCredentials = options.allowCredentials.map(cred => ({
        ...cred,
        id: base64urlDecode(cred.id)
      }));
    }

    // Step 2: Call WebAuthn API
    showInfo(statusDiv, '<strong>Touch your security key or use your device\'s biometric sensor</strong>');

    const assertion = await navigator.credentials.get({
      publicKey: options
    });

    showInfo(statusDiv, 'Verifying authentication...');

    // Step 3: Prepare credential data for form submission
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

    // Submit via form to maintain session and redirect properly
    submitAAL2Form(credentialData, username, cameFrom);

  } catch (error) {
    console.error('AAL2 authentication error:', error);
    const errorMessage = getWebAuthnErrorMessage(error);
    showError(statusDiv, errorMessage);
  }
}

/**
 * Submit AAL2 authentication via hidden form
 * This ensures proper session handling and redirect behavior
 * @param {Object} credentialData - WebAuthn credential data
 * @param {string} username - Username
 * @param {string} cameFrom - Redirect URL
 */
function submitAAL2Form(credentialData, username, cameFrom) {
  // Create hidden form
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '@@passkey-login-verify';

  // Add credential data as JSON
  const credentialInput = document.createElement('input');
  credentialInput.type = 'hidden';
  credentialInput.name = 'credential';
  credentialInput.value = JSON.stringify(credentialData);
  form.appendChild(credentialInput);

  // Add username
  const usernameInput = document.createElement('input');
  usernameInput.type = 'hidden';
  usernameInput.name = 'username';
  usernameInput.value = username;
  form.appendChild(usernameInput);

  // Add came_from for redirect
  const cameFromInput = document.createElement('input');
  cameFromInput.type = 'hidden';
  cameFromInput.name = 'came_from';
  cameFromInput.value = cameFrom;
  form.appendChild(cameFromInput);

  // Add form to page and submit
  document.body.appendChild(form);
  form.submit();
}

/**
 * Initialize AAL2 challenge page
 * Call this on DOMContentLoaded or in template
 * @param {Object} options - Configuration options
 * @param {string} options.username - Pre-filled username
 * @param {string} options.cameFrom - Redirect URL after authentication
 * @param {string} options.authenticateButtonId - ID of authenticate button (default: 'authenticate-button')
 * @param {boolean} options.autoStart - Automatically start authentication (default: false)
 */
function initAAL2Challenge(options) {
  options = options || {};
  const username = options.username || '';
  const cameFrom = options.cameFrom || '/';
  const authenticateButtonId = options.authenticateButtonId || 'authenticate-button';
  const autoStart = options.autoStart || false;

  // Check browser support
  if (!checkWebAuthnSupport()) {
    const statusDiv = 'aal2-status';
    showError(statusDiv, 'Your browser does not support WebAuthn. Please use a modern browser like Chrome, Firefox, Safari, or Edge.');
    return;
  }

  // Attach event listener to authenticate button
  const authenticateButton = document.getElementById(authenticateButtonId);
  if (authenticateButton) {
    authenticateButton.addEventListener('click', async function() {
      await startAAL2Authentication(username, cameFrom);
    });
  }

  // Auto-start if enabled
  if (autoStart && username) {
    // Wait a moment for page to settle
    setTimeout(function() {
      startAAL2Authentication(username, cameFrom);
    }, 500);
  }
}
