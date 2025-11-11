# -*- coding: utf-8 -*-
"""Viewlets for passkey management and AAL2 status display."""

import logging
from datetime import datetime, timedelta

from plone import api
from plone.app.layout.viewlets import ViewletBase

logger = logging.getLogger('c2.pas.aal2.viewlets')


class PasskeyManagementViewlet(ViewletBase):
    """Viewlet to add passkey management link to personal toolbar."""

    def available(self):
        """Check if the viewlet should be displayed."""
        return not api.user.is_anonymous()

    def passkey_manage_url(self):
        """Return the URL to the passkey management page."""
        portal = api.portal.get()
        return portal.absolute_url() + '/@@passkey-manage'

    def passkey_count(self):
        """Return the number of registered passkeys for the current user."""
        try:
            from c2.pas.aal2.credential import count_passkeys
            current_user = api.user.get_current()
            member = api.user.get(username=current_user.getId())
            return count_passkeys(member)
        except Exception:
            return 0


class AAL2StatusViewlet(ViewletBase):
    """Viewlet to display AAL2 authentication status to users.

    Shows:
    - Whether AAL2 is currently valid
    - Remaining time before AAL2 expires
    - Link to re-authenticate if expired
    """

    def available(self):
        """Check if the viewlet should be displayed.

        Only show to authenticated users who have AAL2-related activity.
        """
        if api.user.is_anonymous():
            return False

        try:
            from c2.pas.aal2.session import get_aal2_timestamp
            current_user = api.user.get_current()

            # Show viewlet if user has ever authenticated with AAL2
            timestamp = get_aal2_timestamp(current_user)
            return timestamp is not None
        except Exception as e:
            logger.warning(f"Error checking AAL2 status viewlet availability: {e}")
            return False

    def is_aal2_valid(self):
        """Check if AAL2 is currently valid for the user."""
        try:
            from c2.pas.aal2.session import is_aal2_valid
            current_user = api.user.get_current()
            return is_aal2_valid(current_user)
        except Exception as e:
            logger.error(f"Error checking AAL2 validity: {e}", exc_info=True)
            return False

    def get_remaining_time(self):
        """Get remaining time before AAL2 expires.

        Returns:
            str: Formatted remaining time (e.g., "12 minutes")
            None: If AAL2 is expired or not set
        """
        try:
            from c2.pas.aal2.session import get_aal2_timestamp
            current_user = api.user.get_current()

            timestamp = get_aal2_timestamp(current_user)
            if not timestamp:
                return None

            # Calculate time elapsed
            now = datetime.utcnow()
            elapsed = now - timestamp

            # AAL2 is valid for 15 minutes
            aal2_validity_minutes = 15
            valid_duration = timedelta(minutes=aal2_validity_minutes)

            if elapsed >= valid_duration:
                # Expired
                return None

            # Calculate remaining time
            remaining = valid_duration - elapsed
            remaining_minutes = int(remaining.total_seconds() / 60)

            if remaining_minutes == 0:
                remaining_seconds = int(remaining.total_seconds())
                return f"{remaining_seconds} seconds"
            elif remaining_minutes == 1:
                return "1 minute"
            else:
                return f"{remaining_minutes} minutes"
        except Exception as e:
            logger.error(f"Error calculating remaining AAL2 time: {e}", exc_info=True)
            return None

    def get_status_message(self):
        """Get user-friendly status message."""
        if self.is_aal2_valid():
            remaining = self.get_remaining_time()
            if remaining:
                return f"Your secure session is valid for {remaining}."
            else:
                return "Your secure session is active."
        else:
            return "Your secure session has expired. Please re-authenticate to access protected content."

    def get_status_class(self):
        """Get CSS class for status display."""
        if self.is_aal2_valid():
            return "aal2-status-valid"
        else:
            return "aal2-status-expired"

    def get_reauthenticate_url(self):
        """Get URL to re-authenticate with AAL2."""
        portal = api.portal.get()
        return portal.absolute_url() + '/@@aal2-challenge'

    @property
    def remaining_time(self):
        """Property alias for get_remaining_time()."""
        return self.get_remaining_time()


class AdminAAL2StatusViewlet(ViewletBase):
    """Viewlet to display AAL2 status in admin interface header.

    This viewlet is specifically designed for administrative interfaces,
    showing AAL2 authentication status with countdown timer and warnings
    when approaching expiration.

    Features:
    - Real-time countdown display
    - Warning indicator when < 2 minutes remain
    - Only visible when accessing protected admin pages
    - JavaScript-powered countdown timer
    """

    def available(self):
        """Check if viewlet should be displayed.

        Only show in admin/control panel context to avoid cluttering
        regular pages. Show to authenticated users with AAL2 activity.
        """
        if api.user.is_anonymous():
            return False

        # Check if we're in an admin context
        url = self.request.URL
        admin_indicators = [
            '/@@overview-controlpanel',
            '/@@usergroup-',
            '/@@security-controlpanel',
            '/@@aal2-',
            '/manage',
            '/controlpanel',
        ]

        is_admin_page = any(indicator in url for indicator in admin_indicators)

        if not is_admin_page:
            return False

        try:
            from c2.pas.aal2.session import get_aal2_timestamp
            current_user = api.user.get_current()

            # Show if user has AAL2 timestamp
            timestamp = get_aal2_timestamp(current_user)
            return timestamp is not None
        except Exception as e:
            logger.warning(f"Error checking admin AAL2 viewlet availability: {e}")
            return False

    def aal2_info(self):
        """Get comprehensive AAL2 status information.

        Returns:
            dict: Status information with keys:
                - is_valid (bool): True if AAL2 is currently valid
                - remaining_seconds (int): Seconds until expiration (0 if expired)
                - remaining_minutes (int): Minutes until expiration
                - is_warning (bool): True if < 2 minutes remain
                - status_class (str): CSS class for status display
                - status_message (str): User-friendly status message
                - timestamp (str): ISO format timestamp of last AAL2 auth
        """
        try:
            from c2.pas.aal2.session import get_aal2_timestamp, is_aal2_valid
            current_user = api.user.get_current()

            timestamp = get_aal2_timestamp(current_user)
            is_valid = is_aal2_valid(current_user)

            if not timestamp:
                return {
                    'is_valid': False,
                    'remaining_seconds': 0,
                    'remaining_minutes': 0,
                    'is_warning': False,
                    'status_class': 'aal2-admin-status-expired',
                    'status_message': 'No AAL2 authentication',
                    'timestamp': None,
                }

            # Calculate remaining time
            now = datetime.utcnow()
            elapsed = now - timestamp

            # Get AAL2 session lifetime from registry (default 15 minutes)
            try:
                aal2_lifetime = api.portal.get_registry_record(
                    'c2.pas.aal2.aal2_session_lifetime',
                    default=15
                )
            except Exception:
                aal2_lifetime = 15

            valid_duration = timedelta(minutes=aal2_lifetime)
            remaining = valid_duration - elapsed

            remaining_seconds = max(0, int(remaining.total_seconds()))
            remaining_minutes = max(0, int(remaining_seconds / 60))

            # Determine warning state (< 2 minutes)
            is_warning = 0 < remaining_seconds < 120

            # Determine status class
            if not is_valid or remaining_seconds == 0:
                status_class = 'aal2-admin-status-expired'
                status_message = 'AAL2 Expired'
            elif is_warning:
                status_class = 'aal2-admin-status-warning'
                status_message = f'AAL2 expires in {remaining_minutes}m {remaining_seconds % 60}s'
            else:
                status_class = 'aal2-admin-status-valid'
                status_message = f'AAL2 valid for {remaining_minutes} minutes'

            return {
                'is_valid': is_valid,
                'remaining_seconds': remaining_seconds,
                'remaining_minutes': remaining_minutes,
                'is_warning': is_warning,
                'status_class': status_class,
                'status_message': status_message,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'lifetime_minutes': aal2_lifetime,
            }

        except Exception as e:
            logger.error(f"Error getting admin AAL2 info: {e}", exc_info=True)
            return {
                'is_valid': False,
                'remaining_seconds': 0,
                'remaining_minutes': 0,
                'is_warning': False,
                'status_class': 'aal2-admin-status-error',
                'status_message': 'Error checking AAL2 status',
                'timestamp': None,
            }

    def get_refresh_url(self):
        """Get URL to refresh AAL2 authentication.

        Returns current page URL so user can re-authenticate and return here.
        """
        return self.request.URL

    def get_challenge_url(self):
        """Get URL to AAL2 challenge page.

        Returns:
            str: URL to admin AAL2 challenge page
        """
        portal = api.portal.get()
        return portal.absolute_url() + '/@@admin-aal2-challenge'
