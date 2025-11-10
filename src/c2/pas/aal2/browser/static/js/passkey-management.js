/**
 * Passkey Management UI
 * Handles listing, updating, and deleting passkeys for c2.pas.aal2
 * Depends on: webauthn-utils.js
 */

/**
 * Load and display user's passkeys
 * @returns {Promise<void>}
 */
async function loadPasskeys() {
  const passkeyListDiv = document.getElementById('passkey-list');
  const errorDiv = 'passkey-error';

  if (!passkeyListDiv) {
    console.error('Passkey list container not found');
    return;
  }

  try {
    const response = await fetch('@@passkey-list', {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Failed to load passkeys');
    }

    const data = await response.json();
    const passkeys = data.passkeys || [];

    if (passkeys.length === 0) {
      passkeyListDiv.innerHTML = '<p class="discreet">You have not registered any passkeys yet.</p>';
      return;
    }

    // Build passkey table
    const table = buildPasskeyTable(passkeys);
    passkeyListDiv.innerHTML = '';
    passkeyListDiv.appendChild(table);

  } catch (error) {
    console.error('Error loading passkeys:', error);
    showError(errorDiv, 'Failed to load passkeys. Please refresh the page.');
  }
}

/**
 * Build HTML table from passkey data
 * @param {Array} passkeys - Array of passkey objects
 * @returns {HTMLElement} Table element
 */
function buildPasskeyTable(passkeys) {
  const table = document.createElement('table');
  table.className = 'listing';

  // Header
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr>
      <th>Device Name</th>
      <th>Type</th>
      <th>Registered</th>
      <th>Last Used</th>
      <th>Actions</th>
    </tr>
  `;
  table.appendChild(thead);

  // Body
  const tbody = document.createElement('tbody');
  passkeys.forEach(passkey => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${escapeHtml(passkey.device_name || 'Unnamed Device')}</td>
      <td>${formatDeviceType(passkey.device_type)}</td>
      <td>${formatDate(passkey.registered_at)}</td>
      <td>${passkey.last_used_at ? formatDate(passkey.last_used_at) : 'Never'}</td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="editDeviceName('${escapeHtml(passkey.credential_id)}')">
          Rename
        </button>
        <button class="btn btn-sm btn-danger" onclick="deletePasskey('${escapeHtml(passkey.credential_id)}')">
          Delete
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  return table;
}

/**
 * Format date string for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
  if (!dateString) return 'Unknown';

  try {
    const date = new Date(dateString);
    return date.toLocaleString();
  } catch (error) {
    return dateString;
  }
}

/**
 * Format device type for display
 * @param {string} deviceType - Device type code
 * @returns {string} Human-readable device type
 */
function formatDeviceType(deviceType) {
  const types = {
    'platform': 'Platform (This Device)',
    'cross-platform': 'Security Key',
    'unknown': 'Unknown'
  };

  return types[deviceType] || deviceType || 'Unknown';
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Delete a passkey
 * @param {string} credentialId - Credential ID to delete
 * @returns {Promise<void>}
 */
async function deletePasskey(credentialId) {
  const errorDiv = 'passkey-error';
  const successDiv = 'passkey-success';

  // Confirm deletion
  if (!confirm('Are you sure you want to delete this passkey? This action cannot be undone.')) {
    return;
  }

  try {
    const response = await fetch('@@passkey-delete', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        credential_id: credentialId
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to delete passkey');
    }

    showSuccess(successDiv, 'Passkey deleted successfully.');

    // Reload passkey list
    setTimeout(function() {
      hideStatusMessage(successDiv);
      loadPasskeys();
    }, 1500);

  } catch (error) {
    console.error('Error deleting passkey:', error);
    showError(errorDiv, error.message);
  }
}

/**
 * Prompt to edit device name
 * @param {string} credentialId - Credential ID to update
 */
function editDeviceName(credentialId) {
  const newName = prompt('Enter a new name for this passkey:');

  if (newName !== null && newName.trim() !== '') {
    updateDeviceName(credentialId, newName.trim());
  }
}

/**
 * Update device name
 * @param {string} credentialId - Credential ID to update
 * @param {string} deviceName - New device name
 * @returns {Promise<void>}
 */
async function updateDeviceName(credentialId, deviceName) {
  const errorDiv = 'passkey-error';
  const successDiv = 'passkey-success';

  try {
    const response = await fetch('@@passkey-update', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        credential_id: credentialId,
        device_name: deviceName
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to update passkey');
    }

    showSuccess(successDiv, 'Passkey name updated successfully.');

    // Reload passkey list
    setTimeout(function() {
      hideStatusMessage(successDiv);
      loadPasskeys();
    }, 1500);

  } catch (error) {
    console.error('Error updating passkey:', error);
    showError(errorDiv, error.message);
  }
}

/**
 * Initialize passkey management page
 * Call this on DOMContentLoaded or in template
 * @param {Object} options - Configuration options
 * @param {boolean} options.autoLoad - Automatically load passkeys on init (default: true)
 */
function initPasskeyManagement(options) {
  options = options || {};
  const autoLoad = options.autoLoad !== false; // Default true

  if (autoLoad) {
    // Load passkeys when page is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', loadPasskeys);
    } else {
      loadPasskeys();
    }
  }
}

// Auto-initialize if passkey-list element exists
if (document.getElementById('passkey-list')) {
  initPasskeyManagement();
}
