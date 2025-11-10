/**
 * WebAuthn Utility Functions
 * Common utilities for passkey authentication in c2.pas.aal2
 */

/**
 * Decode base64url string to ArrayBuffer
 * @param {string} input - Base64url encoded string
 * @returns {ArrayBuffer} Decoded array buffer
 */
function base64urlDecode(input) {
  input = input.replace(/-/g, '+').replace(/_/g, '/');
  const pad = input.length % 4;
  if (pad) {
    if (pad === 1) {
      throw new Error('Invalid base64url string');
    }
    input += new Array(5 - pad).join('=');
  }
  const base64 = atob(input);
  const bytes = new Uint8Array(base64.length);
  for (let i = 0; i < base64.length; i++) {
    bytes[i] = base64.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Encode ArrayBuffer to base64url string
 * @param {ArrayBuffer} buffer - Array buffer to encode
 * @returns {string} Base64url encoded string
 */
function base64urlEncode(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

/**
 * Check if browser supports WebAuthn
 * @returns {boolean} True if WebAuthn is supported
 */
function checkWebAuthnSupport() {
  return !!window.PublicKeyCredential;
}

/**
 * Show status message in element
 * @param {string} elementId - ID of element to show message in
 * @param {string} message - Message text (can include HTML)
 * @param {string} type - Message type: 'info', 'error', 'success', 'warning'
 */
function showStatusMessage(elementId, message, type) {
  const element = document.getElementById(elementId);
  if (!element) {
    console.error('Status element not found:', elementId);
    return;
  }

  element.innerHTML = message;
  element.className = 'portalMessage ' + type;
  element.style.display = 'block';
}

/**
 * Hide status message element
 * @param {string} elementId - ID of element to hide
 */
function hideStatusMessage(elementId) {
  const element = document.getElementById(elementId);
  if (element) {
    element.style.display = 'none';
  }
}

/**
 * Show error message
 * @param {string} elementId - ID of element to show error in
 * @param {string} message - Error message
 */
function showError(elementId, message) {
  showStatusMessage(elementId, '<strong>Error:</strong> ' + message, 'error');
}

/**
 * Show success message
 * @param {string} elementId - ID of element to show success in
 * @param {string} message - Success message
 */
function showSuccess(elementId, message) {
  showStatusMessage(elementId, '<strong>Success!</strong> ' + message, 'info');
}

/**
 * Show info message
 * @param {string} elementId - ID of element to show info in
 * @param {string} message - Info message
 */
function showInfo(elementId, message) {
  showStatusMessage(elementId, message, 'info');
}

/**
 * Toggle visibility between two elements
 * @param {string} showId - ID of element to show
 * @param {string} hideId - ID of element to hide
 */
function toggleFormVisibility(showId, hideId) {
  const showElement = document.getElementById(showId);
  const hideElement = document.getElementById(hideId);

  if (showElement) showElement.style.display = 'block';
  if (hideElement) hideElement.style.display = 'none';
}

/**
 * Disable a button
 * @param {string} buttonId - ID of button to disable
 */
function disableButton(buttonId) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = true;
    button.classList.add('disabled');
  }
}

/**
 * Enable a button
 * @param {string} buttonId - ID of button to enable
 */
function enableButton(buttonId) {
  const button = document.getElementById(buttonId);
  if (button) {
    button.disabled = false;
    button.classList.remove('disabled');
  }
}

/**
 * Get friendly error message for WebAuthn error
 * @param {Error} error - WebAuthn error object
 * @returns {string} User-friendly error message
 */
function getWebAuthnErrorMessage(error) {
  const errorName = error.name || '';

  switch (errorName) {
    case 'NotAllowedError':
      return 'The operation was cancelled or timed out. Please try again.';
    case 'InvalidStateError':
      return 'This authenticator is already registered.';
    case 'NotSupportedError':
      return 'Your browser does not support this type of authenticator.';
    case 'SecurityError':
      return 'The operation is not secure. Please use HTTPS.';
    case 'AbortError':
      return 'The operation was aborted.';
    case 'ConstraintError':
      return 'The authenticator does not meet the requirements.';
    case 'NetworkError':
      return 'Network error occurred. Please check your connection.';
    default:
      return error.message || 'An unknown error occurred.';
  }
}
