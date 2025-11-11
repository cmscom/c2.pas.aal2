/**
 * Admin AAL2 Status Countdown Timer
 * Provides real-time countdown display for AAL2 session expiration
 */

// Global countdown interval ID
var aal2CountdownInterval = null;

/**
 * Initialize AAL2 status countdown timer
 * Called automatically when viewlet is present on page
 */
function initAdminAAL2Status() {
  const statusViewlet = document.getElementById('admin-aal2-status-viewlet');

  if (!statusViewlet) {
    console.debug('Admin AAL2 status viewlet not found on this page');
    return;
  }

  // Get status data from JSON script tag
  const statusDataElement = document.getElementById('aal2-status-data');

  if (!statusDataElement) {
    console.error('AAL2 status data not found');
    return;
  }

  let statusData;
  try {
    statusData = JSON.parse(statusDataElement.textContent);
  } catch (e) {
    console.error('Failed to parse AAL2 status data:', e);
    return;
  }

  // Start countdown timer if AAL2 is valid
  if (statusData.is_valid && statusData.remaining_seconds > 0) {
    startCountdown(statusData);
  }

  console.log('Admin AAL2 status initialized');
}

/**
 * Start countdown timer
 * @param {Object} statusData - Initial status data from server
 */
function startCountdown(statusData) {
  let remainingSeconds = statusData.remaining_seconds;
  const lifetimeMinutes = statusData.lifetime_minutes || 15;

  // Update display immediately
  updateCountdownDisplay(remainingSeconds);

  // Clear any existing countdown
  if (aal2CountdownInterval) {
    clearInterval(aal2CountdownInterval);
  }

  // Start new countdown (update every second)
  aal2CountdownInterval = setInterval(function() {
    remainingSeconds--;

    if (remainingSeconds <= 0) {
      // Countdown finished - AAL2 expired
      clearInterval(aal2CountdownInterval);
      aal2CountdownInterval = null;
      handleExpiration();
      return;
    }

    // Update display
    updateCountdownDisplay(remainingSeconds);

    // Check for warning threshold (< 2 minutes)
    if (remainingSeconds === 120) {
      // Entering warning state
      showWarning();
    }

  }, 1000);
}

/**
 * Update countdown display elements
 * @param {number} remainingSeconds - Seconds remaining until expiration
 */
function updateCountdownDisplay(remainingSeconds) {
  const minutesElement = document.getElementById('aal2-minutes');
  const secondsElement = document.getElementById('aal2-seconds');
  const viewlet = document.getElementById('admin-aal2-status-viewlet');

  if (!minutesElement || !secondsElement) {
    console.debug('Countdown display elements not found');
    return;
  }

  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;

  minutesElement.textContent = minutes;
  secondsElement.textContent = seconds;

  // Update CSS class based on remaining time
  if (viewlet) {
    viewlet.classList.remove('aal2-admin-status-valid', 'aal2-admin-status-warning', 'aal2-admin-status-expired');

    if (remainingSeconds <= 0) {
      viewlet.classList.add('aal2-admin-status-expired');
    } else if (remainingSeconds < 120) {
      viewlet.classList.add('aal2-admin-status-warning');
    } else {
      viewlet.classList.add('aal2-admin-status-valid');
    }
  }
}

/**
 * Show warning when approaching expiration
 */
function showWarning() {
  const viewlet = document.getElementById('admin-aal2-status-viewlet');

  if (viewlet) {
    // Add visual warning
    viewlet.classList.add('aal2-admin-status-warning');
    viewlet.classList.remove('aal2-admin-status-valid');

    // Add warning icon if not present
    const statusContent = viewlet.querySelector('.aal2-status-content');
    if (statusContent) {
      const existingWarningIcon = statusContent.querySelector('.aal2-icon-warning');
      if (!existingWarningIcon) {
        // Update icon
        const icons = statusContent.querySelectorAll('.aal2-status-icon');
        icons.forEach(function(icon) {
          icon.style.display = 'none';
        });

        const warningIcon = document.createElement('span');
        warningIcon.className = 'aal2-status-icon aal2-icon-warning';
        warningIcon.textContent = '⚠️';
        statusContent.insertBefore(warningIcon, statusContent.firstChild);
      }
    }

    // Show refresh link if not visible
    const refreshLink = viewlet.querySelector('.aal2-refresh-link');
    if (refreshLink) {
      refreshLink.style.display = 'inline';
    }
  }

  console.warn('AAL2 session approaching expiration (<2 minutes remaining)');
}

/**
 * Handle AAL2 expiration
 */
function handleExpiration() {
  const viewlet = document.getElementById('admin-aal2-status-viewlet');
  const countdownDisplay = document.getElementById('aal2-countdown-display');

  if (viewlet) {
    // Update visual state
    viewlet.classList.remove('aal2-admin-status-valid', 'aal2-admin-status-warning');
    viewlet.classList.add('aal2-admin-status-expired');

    // Update icon
    const statusContent = viewlet.querySelector('.aal2-status-content');
    if (statusContent) {
      const icons = statusContent.querySelectorAll('.aal2-status-icon');
      icons.forEach(function(icon) {
        icon.style.display = 'none';
      });

      const expiredIcon = document.createElement('span');
      expiredIcon.className = 'aal2-status-icon aal2-icon-expired';
      expiredIcon.textContent = '🔓';
      statusContent.insertBefore(expiredIcon, statusContent.firstChild);
    }

    // Show refresh link
    const refreshLink = viewlet.querySelector('.aal2-refresh-link');
    if (refreshLink) {
      refreshLink.style.display = 'inline';
    }
  }

  // Update countdown display to show "Expired"
  if (countdownDisplay) {
    countdownDisplay.innerHTML = '<span class="aal2-expired-text">Expired</span>';
  }

  console.warn('AAL2 session has expired');

  // Optionally: show notification to user
  showExpirationNotification();
}

/**
 * Show notification when AAL2 expires
 */
function showExpirationNotification() {
  // Try to use browser notification if available and permitted
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('AAL2 Session Expired', {
      body: 'Your secure session has expired. Please re-authenticate to continue accessing admin interfaces.',
      icon: '/++resource++plone-icon-security.svg',
      tag: 'aal2-expiration',
      requireInteraction: false
    });
  }

  // Also show in-page banner if not already present
  const existingBanner = document.getElementById('aal2-expiration-banner');
  if (!existingBanner) {
    const banner = document.createElement('div');
    banner.id = 'aal2-expiration-banner';
    banner.className = 'portalMessage warning aal2-expiration-banner';
    banner.innerHTML = `
      <strong>AAL2 Session Expired</strong>
      <p>Your secure session has expired. You will need to re-authenticate with your passkey to access protected administrative functions.</p>
      <button onclick="this.parentElement.remove()" class="btn btn-sm">Dismiss</button>
    `;
    banner.style.cssText = 'position: fixed; top: 60px; left: 50%; transform: translateX(-50%); z-index: 10000; min-width: 400px; max-width: 600px;';

    document.body.appendChild(banner);

    // Auto-dismiss after 10 seconds
    setTimeout(function() {
      if (banner.parentElement) {
        banner.remove();
      }
    }, 10000);
  }
}

/**
 * Request notification permission
 * Called proactively when user first accesses admin interface
 */
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(function(permission) {
      console.log('Notification permission:', permission);
    });
  }
}

/**
 * Manually refresh AAL2 status
 * Can be called by user action or automatically
 */
function refreshAAL2Status() {
  // Redirect to current page, which will re-check AAL2 status
  window.location.reload();
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
  initAdminAAL2Status();
});

// Also try to request notification permission (non-intrusive)
// This is optional and will only prompt once
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(requestNotificationPermission, 2000);
  });
} else {
  setTimeout(requestNotificationPermission, 2000);
}
