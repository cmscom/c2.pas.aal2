# -*- coding: utf-8 -*-
"""AAL2 role management utilities for c2.pas.aal2.

This module provides utility functions to manage AAL2 Required User role
assignments and list users with AAL2 role requirements.
"""

import logging

try:
    from Products.CMFPlone.interfaces import IPloneSiteRoot
except ImportError:
    # Fallback for older Plone versions
    from plone.app.layout.navigation.interfaces import INavigationRoot as IPloneSiteRoot

logger = logging.getLogger('c2.pas.aal2.roles')

# AAL2 role name constant
AAL2_REQUIRED_ROLE = 'AAL2 Required User'


def has_aal2_role(user):
    """Check if user has the AAL2 Required User role.

    Args:
        user: Plone user object

    Returns:
        bool: True if user has AAL2 Required User role

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> if has_aal2_role(user):
        ...     print("User requires AAL2 authentication")
    """
    try:
        roles = user.getRoles()
        return AAL2_REQUIRED_ROLE in roles
    except Exception as e:
        logger.error(f"Failed to check AAL2 role for user {user.getId()}: {e}", exc_info=True)
        return False


def list_aal2_users(portal=None):
    """List all users with AAL2 Required User role.

    Args:
        portal: Optional Plone portal object (will use current site if not provided)

    Returns:
        list: List of user IDs with AAL2 Required User role

    Example:
        >>> aal2_users = list_aal2_users(portal)
        >>> for user_id in aal2_users:
        ...     print(f"AAL2 user: {user_id}")
    """
    try:
        from Products.CMFCore.utils import getToolByName
        from zope.component import getSiteManager

        # Get portal if not provided
        if portal is None:
            try:
                sm = getSiteManager()
                portal = sm.getUtility(IPloneSiteRoot)
            except Exception:
                logger.warning("Cannot list AAL2 users: portal not available")
                return []

        # Get acl_users tool
        acl_users = getToolByName(portal, 'acl_users', None)
        if not acl_users:
            logger.warning("Cannot list AAL2 users: acl_users not available")
            return []

        aal2_users = []

        # Iterate through all users
        for user_id in acl_users.getUserIds():
            user = acl_users.getUserById(user_id)
            if user and has_aal2_role(user):
                aal2_users.append(user_id)

        logger.info(f"Found {len(aal2_users)} users with AAL2 Required User role")
        return aal2_users

    except Exception as e:
        logger.error(f"Failed to list AAL2 users: {e}", exc_info=True)
        return []


def assign_aal2_role(user, portal=None):
    """Assign AAL2 Required User role to a user.

    Args:
        user: Plone user object or user ID string
        portal: Optional Plone portal object

    Returns:
        bool: True if role was assigned successfully

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> if assign_aal2_role(user):
        ...     print("AAL2 role assigned successfully")
    """
    try:
        from Products.CMFCore.utils import getToolByName

        # Handle user ID string
        if isinstance(user, str):
            user_id = user
            if portal is None:
                from zope.component import getSiteManager
                sm = getSiteManager()
                portal = sm.getUtility(IPloneSiteRoot)

            acl_users = getToolByName(portal, 'acl_users')
            user = acl_users.getUserById(user_id)

            if user is None:
                logger.error(f"Cannot assign AAL2 role: user {user_id} not found")
                return False

        # Get portal_membership tool
        if portal is None:
            from zope.component import getSiteManager
            sm = getSiteManager()
            portal = sm.getUtility(IPloneSiteRoot)

        portal_membership = getToolByName(portal, 'portal_membership', None)
        if not portal_membership:
            logger.error("Cannot assign AAL2 role: portal_membership not available")
            return False

        # Check if user already has the role
        if has_aal2_role(user):
            logger.debug(f"User {user.getId()} already has AAL2 Required User role")
            return True

        # Assign role using portal_membership
        # Note: In Plone, roles are typically assigned via portal_membership
        # or by directly modifying the user object's roles
        user_id = user.getId()

        # Get current roles
        current_roles = list(user.getRoles())

        # Add AAL2 role if not present
        if AAL2_REQUIRED_ROLE not in current_roles:
            current_roles.append(AAL2_REQUIRED_ROLE)

            # Use portal_membership to set roles
            portal_membership.setLocalRoles(
                obj=portal,
                member_ids=[user_id],
                member_role=AAL2_REQUIRED_ROLE,
            )

            logger.info(f"Assigned AAL2 Required User role to {user_id}")
            return True

        return True

    except Exception as e:
        logger.error(f"Failed to assign AAL2 role to user {user.getId() if hasattr(user, 'getId') else user}: {e}", exc_info=True)
        return False


def revoke_aal2_role(user, portal=None):
    """Revoke AAL2 Required User role from a user.

    Args:
        user: Plone user object or user ID string
        portal: Optional Plone portal object

    Returns:
        bool: True if role was revoked successfully

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> if revoke_aal2_role(user):
        ...     print("AAL2 role revoked successfully")
    """
    try:
        from Products.CMFCore.utils import getToolByName

        # Handle user ID string
        if isinstance(user, str):
            user_id = user
            if portal is None:
                from zope.component import getSiteManager
                sm = getSiteManager()
                portal = sm.getUtility(IPloneSiteRoot)

            acl_users = getToolByName(portal, 'acl_users')
            user = acl_users.getUserById(user_id)

            if user is None:
                logger.error(f"Cannot revoke AAL2 role: user {user_id} not found")
                return False

        # Check if user has the role
        if not has_aal2_role(user):
            logger.debug(f"User {user.getId()} does not have AAL2 Required User role")
            return True

        # Get portal_membership tool
        if portal is None:
            from zope.component import getSiteManager
            sm = getSiteManager()
            portal = sm.getUtility(IPloneSiteRoot)

        portal_membership = getToolByName(portal, 'portal_membership', None)
        if not portal_membership:
            logger.error("Cannot revoke AAL2 role: portal_membership not available")
            return False

        user_id = user.getId()

        # Revoke role using portal_membership
        portal_membership.deleteLocalRoles(
            obj=portal,
            member_ids=[user_id],
            reindex=True,
        )

        logger.info(f"Revoked AAL2 Required User role from {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to revoke AAL2 role from user {user.getId() if hasattr(user, 'getId') else user}: {e}", exc_info=True)
        return False


def get_aal2_role_info():
    """Get information about the AAL2 Required User role.

    Returns:
        dict: Role information including name, description, permissions

    Example:
        >>> info = get_aal2_role_info()
        >>> print(f"Role: {info['name']}")
        >>> print(f"Description: {info['description']}")
    """
    return {
        'name': AAL2_REQUIRED_ROLE,
        'id': AAL2_REQUIRED_ROLE,
        'description': 'Users with this role must always authenticate with AAL2 (passkey) for all resources',
        'permissions': ['Require AAL2 Authentication'],
        'global': True,  # This is a global role, not content-specific
    }
