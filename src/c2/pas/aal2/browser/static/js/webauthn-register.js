/**
 * WebAuthn Registration Flow
 * Handles passkey registration for c2.pas.aal2
 * Depends on: webauthn-utils.js
 */

/**
 * Register a new passkey
 * @param {string} deviceName - Optional friendly name for the device
 * @param {string} authenticatorType - 'platform', 'cross-platform', or null/empty for any
 * @param {string} redirectUrl - URL to redirect to on success (default: @@personal-information)
 * @returns {Promise<void>}
 */
async function registerPasskey(deviceName, authenticatorType, redirectUrl) {
  redirectUrl = redirectUrl || '@@personal-information';

  const errorDiv = 'passkey-error';
  const successDiv = 'passkey-success';
  const infoDiv = 'passkey-register-form';

  // Hide all status messages
  hideStatusMessage(errorDiv);
  hideStatusMessage(successDiv);
  hideStatusMessage(infoDiv);

  try {
    // Step 1: Get registration options from server
    const optionsResponse = await fetch('@@passkey-register-options', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        device_name: deviceName,
        authenticator_attachment: authenticatorType || null
      })
    });

    if (!optionsResponse.ok) {
      const error = await optionsResponse.json();
      throw new Error(error.message || 'Failed to get registration options');
    }

    const optionsData = await optionsResponse.json();
    const options = optionsData.publicKey;

    // Decode base64url fields
    options.challenge = base64urlDecode(options.challenge);
    options.user.id = base64urlDecode(options.user.id);
    if (options.excludeCredentials) {
      options.excludeCredentials = options.excludeCredentials.map(cred => ({
        ...cred,
        id: base64urlDecode(cred.id)
      }));
    }

    // Show info message to prompt user
    showInfo(infoDiv, '<strong>Touch your security key or use your device\'s biometric sensor</strong>');

    // Step 2: Call WebAuthn API
    const credential = await navigator.credentials.create({
      publicKey: options
    });

    // Hide info message
    hideStatusMessage(infoDiv);

    // Step 3: Send credential to server for verification
    const verifyResponse = await fetch('@@passkey-register-verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        credential: {
          id: credential.id,
          rawId: base64urlEncode(credential.rawId),
          type: credential.type,
          response: {
            clientDataJSON: base64urlEncode(credential.response.clientDataJSON),
            attestationObject: base64urlEncode(credential.response.attestationObject)
          },
          transports: credential.response.getTransports ? credential.response.getTransports() : []
        },
        device_name: deviceName
      })
    });

    if (!verifyResponse.ok) {
      const error = await verifyResponse.json();
      throw new Error(error.message || 'Verification failed');
    }

    const result = await verifyResponse.json();

    // Success!
    showSuccess(successDiv, 'Your passkey has been registered. You can now use it to log in.');

    // Clear form if it exists
    const deviceNameInput = document.getElementById('device-name');
    if (deviceNameInput) {
      deviceNameInput.value = '';
    }

    // Redirect after 2 seconds
    setTimeout(function() {
      window.location.href = redirectUrl;
    }, 2000);

  } catch (error) {
    console.error('Passkey registration error:', error);
    const errorMessage = getWebAuthnErrorMessage(error);
    showError(errorDiv, errorMessage);
    hideStatusMessage(infoDiv);
  }
}

/**
 * Initialize passkey registration form
 * Call this on DOMContentLoaded or in template
 */
function initPasskeyRegistration() {
  // Check browser support
  if (!checkWebAuthnSupport()) {
    const warningDiv = document.getElementById('browser-support-warning');
    const formDiv = document.getElementById('register-passkey-form');

    if (warningDiv) warningDiv.style.display = 'block';
    if (formDiv) formDiv.style.display = 'none';
    return;
  }

  // Attach event listener to register button
  const registerButton = document.getElementById('register-button');
  if (registerButton) {
    registerButton.addEventListener('click', async function() {
      const deviceName = document.getElementById('device-name')?.value || '';
      const authenticatorType = document.getElementById('authenticator-type')?.value || '';

      await registerPasskey(deviceName, authenticatorType);
    });
  }
}
