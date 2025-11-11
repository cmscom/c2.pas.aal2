# -*- coding: utf-8 -*-
"""Admin URL protection logic for AAL2.

This module provides functions to check if URLs require AAL2 protection,
validate AAL2 session validity, and manage redirect context during challenges.
"""

import fnmatch
import time
import logging
from plone import api
from plone.memoize import ram
from plone.registry.interfaces import IRecordModifiedEvent
from zope.component import adapter
from c2.pas.aal2.session import is_aal2_valid

logger = logging.getLogger('c2.pas.aal2.admin.protection')

# Session key for storing redirect context
REDIRECT_SESSION_KEY = 'c2.pas.aal2.admin_redirect_url'

# Maximum challenge attempts to prevent loops
MAX_CHALLENGE_ATTEMPTS = 3

# Redirect context timeout (5 minutes in seconds)
REDIRECT_TIMEOUT = 300


def _pattern_cache_key(method):
    """Cache key based on registry values.

    Returns a hash of the current protected patterns to invalidate
    cache when patterns change.
    """
    try:
        patterns = api.portal.get_registry_record(
            'c2.pas.aal2.admin.protected_patterns',
            default=[]
        )
        return hash(tuple(patterns))
    except Exception:
        return 'default'


@ram.cache(_pattern_cache_key)
def get_protected_patterns():
    """Get protected URL patterns from registry.

    Returns:
        list: List of glob-style URL patterns requiring AAL2

    Example:
        >>> patterns = get_protected_patterns()
        >>> print(patterns)
        ['*/@@overview-controlpanel', '*/@@usergroup-userprefs']
    """
    try:
        patterns = api.portal.get_registry_record(
            'c2.pas.aal2.admin.protected_patterns',
            default=[]
        )
        logger.debug(f"Loaded {len(patterns)} protected patterns from registry")
        return patterns
    except Exception as e:
        logger.warning(f"Could not load protected patterns: {e}")
        # Return default patterns if registry not accessible
        return [
            '*/@@overview-controlpanel',
            '*/@@usergroup-userprefs',
            '*/@@usergroup-groupprefs',
        ]


def is_protected_url(url):
    """Check if URL matches any protected admin pattern.

    Args:
        url (str): URL to check (can be full URL or path)

    Returns:
        bool: True if URL requires AAL2 protection, False otherwise

    Example:
        >>> is_protected_url('http://localhost/Plone/@@overview-controlpanel')
        True
        >>> is_protected_url('/Plone/front-page')
        False
    """
    try:
        patterns = get_protected_patterns()
        for pattern in patterns:
            if fnmatch.fnmatch(url, pattern):
                logger.debug(f"URL {url} matches pattern {pattern}")
                return True
        return False
    except Exception as e:
        logger.exception(f"Error checking protected URL: {e}")
        # Fail open for availability
        return False


def check_admin_access(request, user):
    """Check if user should be allowed to access admin URL.

    This function checks:
    1. If admin protection is enabled
    2. If the requested URL is protected
    3. If user's AAL2 authentication is valid

    Args:
        request: Zope HTTP request object
        user: Plone user object

    Returns:
        dict: Access decision with keys:
            - allowed (bool): True if access granted
            - reason (str): Reason code ('not_protected', 'aal2_valid', 'aal2_expired', etc.)
            - redirect_url (str|None): Challenge URL if access denied

    Example:
        >>> result = check_admin_access(request, user)
        >>> if not result['allowed']:
        ...     redirect_to(result['redirect_url'])
    """
    try:
        url = request.URL

        # Check if protection is enabled
        enabled = api.portal.get_registry_record(
            'c2.pas.aal2.admin.enabled',
            default=True
        )
        if not enabled:
            logger.debug("Admin AAL2 protection is disabled")
            return {
                'allowed': True,
                'reason': 'disabled',
                'redirect_url': None
            }

        # Check if URL is protected
        if not is_protected_url(url):
            return {
                'allowed': True,
                'reason': 'not_protected',
                'redirect_url': None
            }

        logger.debug(f"URL {url} is protected, checking AAL2 validity")

        # Check AAL2 validity
        if is_aal2_valid(user):
            logger.debug(f"User {user.getId()} has valid AAL2 session")
            return {
                'allowed': True,
                'reason': 'aal2_valid',
                'redirect_url': None
            }

        # AAL2 expired - need challenge
        logger.info(f"User {user.getId()} AAL2 expired for URL {url}")
        portal_url = api.portal.get().absolute_url()
        return {
            'allowed': False,
            'reason': 'aal2_expired',
            'redirect_url': f'{portal_url}/@@admin-aal2-challenge'
        }

    except Exception as e:
        logger.exception(f"Error checking admin access: {e}")
        # Fail open for availability
        return {
            'allowed': True,
            'reason': 'error',
            'redirect_url': None
        }


def store_redirect_context(request, original_url):
    """Store original URL in session for post-challenge redirect.

    Args:
        request: Zope HTTP request object
        original_url (str): URL user was trying to access

    Raises:
        ValueError: If original_url is not same-origin (security check)

    Example:
        >>> store_redirect_context(request, 'http://localhost/Plone/@@overview-controlpanel')
    """
    try:
        # Basic same-origin validation
        portal_url = api.portal.get().absolute_url()
        if not original_url.startswith(portal_url):
            logger.warning(f"Rejected non-same-origin redirect: {original_url}")
            raise ValueError("Redirect URL must be same-origin")

        session = request.SESSION

        # Get existing context or create new
        existing = session.get(REDIRECT_SESSION_KEY)
        challenge_count = 1
        if existing and isinstance(existing, dict):
            challenge_count = existing.get('challenge_count', 0) + 1

        # Check for challenge loops
        if challenge_count > MAX_CHALLENGE_ATTEMPTS:
            logger.warning(f"Max challenge attempts exceeded for {original_url}")
            # Clear and don't store - will redirect to home
            if REDIRECT_SESSION_KEY in session:
                del session[REDIRECT_SESSION_KEY]
            return

        # Store redirect context
        session[REDIRECT_SESSION_KEY] = {
            'original_url': original_url,
            'timestamp': time.time(),
            'challenge_count': challenge_count,
        }

        logger.debug(f"Stored redirect context for {original_url} (attempt {challenge_count})")

    except Exception as e:
        logger.exception(f"Error storing redirect context: {e}")


def get_redirect_context(request):
    """Retrieve stored redirect context from session.

    Args:
        request: Zope HTTP request object

    Returns:
        dict|None: Redirect context with keys:
            - original_url (str): URL to redirect back to
            - timestamp (float): Unix timestamp when stored
            - challenge_count (int): Number of challenge attempts
        Returns None if not found, expired, or max attempts exceeded

    Example:
        >>> context = get_redirect_context(request)
        >>> if context:
        ...     redirect_to(context['original_url'])
    """
    try:
        session = request.SESSION
        context = session.get(REDIRECT_SESSION_KEY)

        if not context or not isinstance(context, dict):
            return None

        # Check expiry
        timestamp = context.get('timestamp', 0)
        if time.time() - timestamp > REDIRECT_TIMEOUT:
            logger.debug("Redirect context expired")
            # Clear expired context
            if REDIRECT_SESSION_KEY in session:
                del session[REDIRECT_SESSION_KEY]
            return None

        # Check challenge count
        if context.get('challenge_count', 0) > MAX_CHALLENGE_ATTEMPTS:
            logger.warning("Max challenge attempts exceeded")
            # Clear
            if REDIRECT_SESSION_KEY in session:
                del session[REDIRECT_SESSION_KEY]
            return None

        return context

    except Exception as e:
        logger.exception(f"Error getting redirect context: {e}")
        return None


def clear_redirect_context(request):
    """Remove redirect context from session after use.

    Args:
        request: Zope HTTP request object

    Example:
        >>> clear_redirect_context(request)
    """
    try:
        session = request.SESSION
        if REDIRECT_SESSION_KEY in session:
            del session[REDIRECT_SESSION_KEY]
            logger.debug("Cleared redirect context")
    except Exception as e:
        logger.exception(f"Error clearing redirect context: {e}")


@adapter(IRecordModifiedEvent)
def invalidate_pattern_cache(event):
    """Invalidate pattern cache when registry settings change.

    This event handler clears the RAM cache when admin protection
    settings are modified in the registry.

    Args:
        event: IRecordModifiedEvent from plone.registry

    Example:
        Registered in configure.zcml:
        <subscriber
            for="plone.registry.interfaces.IRecordModifiedEvent"
            handler=".protection.invalidate_pattern_cache"
            />
    """
    try:
        # Check if this is an admin protection setting
        if (event.record and
            event.record.interfaceName == 'c2.pas.aal2.admin.interfaces.IAAL2AdminSettings'):

            logger.info(f"Admin protection setting changed: {event.record.__name__}")

            # Note: Cache automatically invalidates when registry values change
            # because _pattern_cache_key uses registry values as the cache key.
            # The hash of the pattern list changes, causing a different cache key.
            # No explicit cache clearing needed - next call will use new key.

            logger.debug("Pattern cache will auto-refresh on next access")

    except Exception as e:
        logger.exception(f"Error invalidating pattern cache: {e}")
