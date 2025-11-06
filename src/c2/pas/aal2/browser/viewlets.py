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
