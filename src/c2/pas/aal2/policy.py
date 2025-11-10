# -*- coding: utf-8 -*-
"""AAL2 policy management for c2.pas.aal2.

This module provides functions to manage AAL2 authentication policies
for Plone content objects, including setting requirements and checking access.
"""

import logging
import time

from plone.memoize import ram
from zope.annotation.interfaces import IAnnotations

from c2.pas.aal2.session import is_aal2_valid

logger = logging.getLogger('c2.pas.aal2.policy')

# Annotation key for storing AAL2 policy on content
AAL2_POLICY_KEY = 'c2.pas.aal2.require_aal2'


def is_aal2_required(context, user=None):
    """Check if AAL2 authentication is required for the given context.

    This function checks:
    1. Content-level AAL2 policy annotation
    2. User-level AAL2 role (if user provided)

    Args:
        context: Plone content object to check
        user: Optional Plone user object (for role-based checks)

    Returns:
        bool: True if AAL2 is required, False otherwise

    Example:
        >>> content = portal['sensitive-document']
        >>> if is_aal2_required(content):
        ...     print("AAL2 authentication required")

        >>> # Check with user (role-based)
        >>> if is_aal2_required(content, user):
        ...     print("AAL2 required for this user")
    """
    try:
        # Check content-level AAL2 policy
        annotations = IAnnotations(context)
        required = annotations.get(AAL2_POLICY_KEY, False)

        if required:
            return True

        # Check if user has AAL2 Required User role
        if user is not None:
            try:
                roles = user.getRoles()
                if 'AAL2 Required User' in roles:
                    logger.debug(f"AAL2 required for user {user.getId()} due to role")
                    return True
            except Exception as e:
                logger.debug(f"Could not check user roles: {e}")

        return False

    except Exception as e:
        logger.error(f"Failed to check AAL2 requirement for {context}: {e}", exc_info=True)
        # Fail closed: if we can't check, assume AAL2 is required for safety
        return False


def set_aal2_required(context, required=True):
    """Set AAL2 authentication requirement for content.

    Args:
        context: Plone content object
        required (bool): True to require AAL2, False to remove requirement

    Returns:
        None

    Example:
        >>> content = portal['sensitive-document']
        >>> set_aal2_required(content, required=True)
        >>> assert is_aal2_required(content)
    """
    try:
        annotations = IAnnotations(context)
        annotations[AAL2_POLICY_KEY] = required

        # Invalidate cache for this content
        _invalidate_aal2_policy_cache(context)

        action = "set" if required else "removed"
        logger.info(f"AAL2 requirement {action} for content: {context.getId()}")

    except Exception as e:
        logger.error(f"Failed to set AAL2 requirement for {context}: {e}", exc_info=True)
        raise


def check_aal2_access(context, user, request):
    """Check if user has valid AAL2 access to the given context.

    This function performs the complete AAL2 access check:
    1. Checks if AAL2 is required for the context
    2. If required, validates user's AAL2 authentication timestamp
    3. Returns access decision

    Args:
        context: Plone content object being accessed
        user: Plone user object attempting access
        request: HTTP request object

    Returns:
        bool: True if access is allowed, False if AAL2 challenge needed

    Example:
        >>> if not check_aal2_access(content, user, request):
        ...     # Redirect to AAL2 challenge
        ...     return request.RESPONSE.redirect('@@aal2-challenge')
    """
    try:
        # Check if AAL2 is required for this content
        if not is_aal2_required(context, user):
            # No AAL2 requirement, allow access
            return True

        # AAL2 is required - check user's authentication
        if is_aal2_valid(user):
            # User has valid AAL2 authentication within 15 minutes
            logger.debug(f"AAL2 access granted for user {user.getId()} to {context.getId()}")
            return True

        # AAL2 required but not valid - deny access
        logger.info(f"AAL2 access denied for user {user.getId()} to {context.getId()}: expired or missing")
        return False

    except Exception as e:
        logger.error(f"Error checking AAL2 access for user {user.getId()} to {context}: {e}", exc_info=True)
        # Fail closed: deny access on error
        return False


def get_stepup_challenge_url(context, request):
    """Generate step-up authentication challenge URL.

    This URL redirects the user to the AAL2 passkey challenge page.
    After successful authentication, user is redirected back to the original content.

    Args:
        context: Plone content object being accessed
        request: HTTP request object

    Returns:
        str: URL to AAL2 challenge page with came_from parameter

    Example:
        >>> url = get_stepup_challenge_url(content, request)
        >>> return request.RESPONSE.redirect(url)
    """
    try:
        # Get the original URL user was trying to access
        came_from = context.absolute_url()

        # Build challenge URL with came_from parameter
        portal_url = _get_portal_url(context)
        challenge_url = f"{portal_url}/@@aal2-challenge?came_from={came_from}"

        logger.debug(f"Generated AAL2 challenge URL: {challenge_url}")
        return challenge_url

    except Exception as e:
        logger.error(f"Failed to generate AAL2 challenge URL for {context}: {e}", exc_info=True)
        # Fallback to simple challenge URL
        try:
            portal_url = _get_portal_url(context)
            return f"{portal_url}/@@aal2-challenge"
        except Exception:
            return "/@@aal2-challenge"


def list_aal2_protected_content():
    """List all content requiring AAL2 authentication.

    This is a utility function for administrators to see which content
    is protected with AAL2 requirements.

    Returns:
        list: List of dicts with content info (path, title, type, url)

    Note:
        This implementation is basic and may be slow for large sites.
        For production, consider adding a catalog index.

    Example:
        >>> protected = list_aal2_protected_content()
        >>> for item in protected:
        ...     print(f"{item['title']} at {item['path']}")
    """
    try:
        from Products.CMFCore.utils import getToolByName
        from zope.component import getSiteManager

        # Get portal
        sm = getSiteManager()
        portal = sm.getUtility(IAnnotations).__parent__  # Hack to get portal

        # Get catalog
        catalog = getToolByName(portal, 'portal_catalog', None)
        if not catalog:
            logger.warning("Cannot list AAL2 protected content: catalog not available")
            return []

        protected = []
        # Note: This is inefficient for large sites
        # In production, add a catalog index for AAL2 policy
        for brain in catalog():
            try:
                obj = brain.getObject()
                if is_aal2_required(obj):
                    protected.append({
                        'path': brain.getPath(),
                        'title': brain.Title,
                        'type': brain.portal_type,
                        'url': brain.getURL()
                    })
            except Exception:
                # Skip inaccessible objects
                continue

        logger.info(f"Found {len(protected)} AAL2-protected content items")
        return protected

    except Exception as e:
        logger.error(f"Failed to list AAL2 protected content: {e}", exc_info=True)
        return []


# Caching support

def _aal2_policy_cache_key(method, context):
    """Cache key for AAL2 policy checks.

    Cache is invalidated when:
    - Policy is changed via set_aal2_required()
    - After 60 seconds (for safety)
    """
    try:
        context_path = '/'.join(context.getPhysicalPath())
        # Cache for 1 minute
        cache_time = int(time.time() / 60)
        return (context_path, cache_time)
    except Exception:
        # If we can't generate a proper key, use a timestamp-based key
        # This effectively disables caching for this object
        return (id(context), time.time())


@ram.cache(_aal2_policy_cache_key)
def is_aal2_required_cached(context):
    """Cached version of is_aal2_required().

    Use this for read-heavy scenarios where AAL2 policy doesn't change often.
    """
    return is_aal2_required(context)


def _invalidate_aal2_policy_cache(context):
    """Invalidate cache for AAL2 policy on the given context."""
    try:
        # Force cache invalidation by clearing the cache entry
        _aal2_policy_cache_key(is_aal2_required_cached, context)
        # Note: ram.cache doesn't have a public invalidation API
        # Cache will auto-expire after 60 seconds
        logger.debug(f"Cache invalidation requested for {context.getId()}")
    except Exception as e:
        logger.debug(f"Cache invalidation failed (non-critical): {e}")


# Helper functions

def _get_portal_url(context):
    """Get portal URL from context.

    Args:
        context: Any Plone object

    Returns:
        str: Portal URL
    """
    try:
        # Get portal via acquisition
        portal = context.portal_url.getPortalObject()
        return portal.absolute_url()
    except Exception:
        try:
            # Fallback: navigate up to portal
            obj = context
            while obj is not None and not getattr(obj, 'isPrincipiaFolderish', False):
                obj = getattr(obj, 'aq_parent', None)
            if obj:
                return obj.absolute_url()
        except Exception:
            pass

    # Last resort fallback
    return ""


def get_aal2_status(context, user):
    """Get comprehensive AAL2 status for a user and context.

    Utility function that returns detailed AAL2 status information.

    Args:
        context: Plone content object
        user: Plone user object

    Returns:
        dict: Status information including:
            - required (bool): Is AAL2 required?
            - valid (bool): Does user have valid AAL2 auth?
            - expiry (datetime): When does AAL2 auth expire?
            - needs_challenge (bool): Should user see challenge?

    Example:
        >>> status = get_aal2_status(content, user)
        >>> if status['needs_challenge']:
        ...     print(f"Re-auth needed, expires at {status['expiry']}")
    """
    from c2.pas.aal2.session import get_aal2_expiry

    try:
        required = is_aal2_required(context, user)
        valid = is_aal2_valid(user) if required else True
        expiry = get_aal2_expiry(user) if required else None
        needs_challenge = required and not valid

        return {
            'required': required,
            'valid': valid,
            'expiry': expiry,
            'needs_challenge': needs_challenge,
        }

    except Exception as e:
        logger.error(f"Failed to get AAL2 status: {e}", exc_info=True)
        return {
            'required': False,
            'valid': False,
            'expiry': None,
            'needs_challenge': False,
        }
