# -*- coding: utf-8 -*-
"""Viewlets for passkey management."""

from plone import api
from plone.app.layout.viewlets import ViewletBase


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
