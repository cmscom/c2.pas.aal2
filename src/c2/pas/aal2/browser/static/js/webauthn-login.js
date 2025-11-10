/**
 * WebAuthn Login/Authentication Flow
 * Handles passkey login for c2.pas.aal2
 * Depends on: webauthn-utils.js
 */

/**
 * Login with passkey
 * @param {string} username - Username (optional, can be empty for usernameless flow)
 * @param {string} redirectUrl - URL to redirect to after successful login
 * @returns {Promise<void>}
 */
async function loginWithPasskey(username, redirectUrl) {
  const errorDiv = 'passkey-error';
  const successDiv = 'passkey-success';
  const infoDiv = 'passkey-login-info';

  // Hide all status messages
  hideStatusMessage(errorDiv);
  hideStatusMessage(successDiv);
  hideStatusMessage(infoDiv);

  try {
    // Step 1: Get authentication options from server
    const optionsResponse = await fetch('@@passkey-login-options', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username || null
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

    // Show info message
    showInfo(infoDiv, '<strong>Touch your security key or use your device\'s biometric sensor</strong>');

    // Step 2: Call WebAuthn API
    const assertion = await navigator.credentials.get({
      publicKey: options
    });

    // Hide info message
    hideStatusMessage(infoDiv);

    // Step 3: Send assertion to server for verification
    const verifyResponse = await fetch('@@passkey-login-verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        credential: {
          id: assertion.id,
          rawId: base64urlEncode(assertion.rawId),
          type: assertion.type,
          response: {
            clientDataJSON: base64urlEncode(assertion.response.clientDataJSON),
            authenticatorData: base64urlEncode(assertion.response.authenticatorData),
            signature: base64urlEncode(assertion.response.signature),
            userHandle: assertion.response.userHandle ? base64urlEncode(assertion.response.userHandle) : null
          }
        }
      })
    });

    if (!verifyResponse.ok) {
      const error = await verifyResponse.json();
      throw new Error(error.message || 'Authentication failed');
    }

    const result = await verifyResponse.json();

    // Success!
    showSuccess(successDiv, 'Authentication successful! Redirecting...');

    // Redirect after 1 second
    setTimeout(function() {
      window.location.href = redirectUrl || result.redirect_url || '/';
    }, 1000);

  } catch (error) {
    console.error('Passkey login error:', error);
    const errorMessage = getWebAuthnErrorMessage(error);
    showError(errorDiv, errorMessage);
    hideStatusMessage(infoDiv);
  }
}

/**
 * Auto-fill username from URL query parameter
 * @param {string} paramName - Query parameter name (default: 'username')
 * @param {string} inputId - ID of username input field (default: 'username')
 */
function autoFillUsernameFromUrl(paramName, inputId) {
  paramName = paramName || 'username';
  inputId = inputId || 'username';

  const urlParams = new URLSearchParams(window.location.search);
  const username = urlParams.get(paramName);

  if (username) {
    const usernameInput = document.getElementById(inputId);
    if (usernameInput) {
      usernameInput.value = username;
    }
  }
}

/**
 * Initialize passkey login form
 * Call this on DOMContentLoaded or in template
 * @param {Object} options - Configuration options
 * @param {string} options.usernameInputId - ID of username input (default: 'username')
 * @param {string} options.loginButtonId - ID of login button (default: 'login-button')
 * @param {string} options.redirectUrlInputId - ID of came_from input (default: 'came_from')
 * @param {boolean} options.autoFillUsername - Auto-fill username from URL (default: true)
 */
function initPasskeyLogin(options) {
  options = options || {};
  const usernameInputId = options.usernameInputId || 'username';
  const loginButtonId = options.loginButtonId || 'login-button';
  const redirectUrlInputId = options.redirectUrlInputId || 'came_from';
  const autoFill = options.autoFillUsername !== false; // Default true

  // Check browser support
  if (!checkWebAuthnSupport()) {
    const warningDiv = document.getElementById('browser-support-warning');
    const formDiv = document.getElementById('passkey-login-form');

    if (warningDiv) warningDiv.style.display = 'block';
    if (formDiv) formDiv.style.display = 'none';
    return;
  }

  // Auto-fill username from URL if enabled
  if (autoFill) {
    autoFillUsernameFromUrl('username', usernameInputId);
  }

  // Attach event listener to login button
  const loginButton = document.getElementById(loginButtonId);
  if (loginButton) {
    loginButton.addEventListener('click', async function() {
      const username = document.getElementById(usernameInputId)?.value || '';
      const redirectUrl = document.getElementById(redirectUrlInputId)?.value || '/';

      await loginWithPasskey(username, redirectUrl);
    });
  }
}

/**
 * Show password login form (for enhanced login page)
 */
function showPasswordForm() {
  toggleFormVisibility('password-login-form', 'passkey-login-form');
}

/**
 * Show passkey login form (for enhanced login page)
 */
function showPasskeyForm() {
  toggleFormVisibility('passkey-login-form', 'password-login-form');
}

/**
 * Initialize enhanced login page with both password and passkey options
 * @param {Object} options - Configuration options (same as initPasskeyLogin)
 */
function initEnhancedLogin(options) {
  // Initialize passkey login
  initPasskeyLogin(options);

  // Attach toggle buttons
  const showPasswordBtn = document.getElementById('show-password-form');
  const showPasskeyBtn = document.getElementById('show-passkey-form');

  if (showPasswordBtn) {
    showPasswordBtn.addEventListener('click', showPasswordForm);
  }

  if (showPasskeyBtn) {
    showPasskeyBtn.addEventListener('click', showPasskeyForm);
  }
}
