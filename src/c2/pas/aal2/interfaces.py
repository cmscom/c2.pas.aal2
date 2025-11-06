# -*- coding: utf-8 -*-
"""Zope interface definitions for c2.pas.aal2 AAL2 authentication plugin.

This module defines the IAAL2Plugin interface, which specifies the contract
for AAL2 (Authentication Assurance Level 2) authentication functionality.
This is a template/stub interface for future implementation.
"""

from zope.interface import Interface


class IAAL2Plugin(Interface):
    """Interface for AAL2 authentication plugin.

    This interface defines methods that an AAL2 authentication plugin
    should implement to handle Authentication Assurance Level 2 requirements.

    Future implementations should:
    - Determine the current AAL level for authenticated users
    - Enforce AAL2 requirements based on content/context sensitivity
    - Integrate with existing Plone PAS authentication flow
    """

    def get_aal_level(user_id):
        """Get the current Authentication Assurance Level for a user.

        Args:
            user_id (str): The user identifier

        Returns:
            int: The current AAL level (1, 2, or 3)
                 Stub implementation returns 1 (lowest assurance)

        Future Implementation:
            - Check user's authentication method (password, 2FA, etc.)
            - Verify session properties and authentication timestamp
            - Return appropriate AAL level based on authentication strength
        """

    def require_aal2(user_id, context):
        """Determine if AAL2 is required for the given user and context.

        Args:
            user_id (str): The user identifier
            context (object): The Plone content object being accessed

        Returns:
            bool: True if AAL2 is required, False otherwise
                  Stub implementation returns False

        Future Implementation:
            - Check content-level AAL2 policy annotations
            - Verify user's current AAL level
            - Trigger step-up authentication if needed
            - Integrate with Plone's security framework
        """
