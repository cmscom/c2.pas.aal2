# -*- coding: utf-8 -*-
"""AAL2 session management for c2.pas.aal2.

This module provides functions to manage AAL2 authentication timestamps
and validate 15-minute session windows for AAL2-compliant authentication.

Plone 6 Compatibility:
- Uses session data manager instead of user annotations
- Falls back to portal annotations for persistence
"""

from datetime import datetime, timedelta
from zope.annotation.interfaces import IAnnotations
from plone import api
import logging

logger = logging.getLogger('c2.pas.aal2.session')

# Annotation key for storing AAL2 timestamp
ANNOTATION_KEY = 'c2.pas.aal2.aal2_timestamp'

# AAL2 session timeout: 15 minutes (900 seconds)
AAL2_TIMEOUT_SECONDS = 900


def _get_session_data():
    """Get session data manager (Plone 6 compatible).

    Returns:
        dict-like session data object or None
    """
    try:
        # Try to get session data from request
        request = api.env.getRequest()
        if request and hasattr(request, 'SESSION'):
            return request.SESSION
    except Exception as e:
        logger.debug(f"Could not get session data: {e}")
    return None


def _get_user_storage(user):
    """Get storage for user AAL2 data.

    This attempts multiple storage strategies:
    1. Session data (preferred for Plone 6)
    2. Portal annotations (fallback)

    Args:
        user: Plone user object

    Returns:
        tuple: (storage_dict, storage_key, is_session)
    """
    user_id = user.getId() if hasattr(user, 'getId') else str(user)

    # Try session storage first
    session = _get_session_data()
    if session is not None:
        session_key = f'c2.pas.aal2.{user_id}'
        return (session, session_key, True)

    # Fall back to portal annotations
    try:
        portal = api.portal.get()
        annotations = IAnnotations(portal)

        # Create user-specific storage in portal annotations
        if ANNOTATION_KEY not in annotations:
            annotations[ANNOTATION_KEY] = {}

        user_storage = annotations[ANNOTATION_KEY]
        return (user_storage, user_id, False)
    except Exception as e:
        logger.error(f"Could not get storage for user {user_id}: {e}")
        return (None, None, False)


def set_aal2_timestamp(user, credential_id=None):
    """Set AAL2 authentication timestamp for a user.

    This function records the current time as the AAL2 authentication timestamp.
    It should be called immediately after successful passkey authentication.

    Args:
        user: Plone user object with IAnnotations support
        credential_id (str, optional): The passkey credential ID used for authentication
                                       (stored for audit purposes only)

    Returns:
        None

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> set_aal2_timestamp(user, credential_id='AQIDBAUGBwg...')
    """
    try:
        storage, key, is_session = _get_user_storage(user)
        if storage is None:
            logger.error(f"Could not get storage for user {user.getId()}")
            return

        timestamp = datetime.utcnow().isoformat()

        # Store timestamp data
        timestamp_data = {
            'timestamp': timestamp,
        }

        # Include credential ID if provided (for audit)
        if credential_id:
            timestamp_data['credential_id'] = credential_id

        storage[key] = timestamp_data

        storage_type = "session" if is_session else "portal annotations"
        logger.info(f"Set AAL2 timestamp for user {user.getId()} in {storage_type}")

    except Exception as e:
        logger.error(f"Failed to set AAL2 timestamp for user {user.getId()}: {e}", exc_info=True)


def get_aal2_timestamp(user):
    """Get AAL2 authentication timestamp for a user.

    Retrieves the stored AAL2 authentication timestamp from session or portal annotations.

    Plone 6 Compatible: Uses session storage or portal annotations.

    Args:
        user: Plone user object

    Returns:
        datetime or None: The AAL2 authentication timestamp in UTC, or None if not set

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> timestamp = get_aal2_timestamp(user)
        >>> if timestamp:
        ...     print(f"Last authenticated at: {timestamp}")
    """
    try:
        storage, key, is_session = _get_user_storage(user)
        if storage is None:
            return None

        timestamp_data = storage.get(key)

        if not timestamp_data:
            return None

        # Handle both old (string) and new (dict) formats
        if isinstance(timestamp_data, str):
            # Legacy format: direct timestamp string
            return datetime.fromisoformat(timestamp_data)
        elif isinstance(timestamp_data, dict):
            # New format: dict with timestamp and metadata
            timestamp_str = timestamp_data.get('timestamp')
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)

        return None

    except Exception as e:
        logger.error(f"Failed to get AAL2 timestamp for user {user.getId()}: {e}", exc_info=True)
        return None


def is_aal2_valid(user):
    """Check if AAL2 authentication is still valid for a user.

    Validates that:
    1. An AAL2 timestamp exists
    2. The timestamp is not in the future (clock skew protection)
    3. The timestamp is within the 15-minute validity window

    Args:
        user: Plone user object with IAnnotations support

    Returns:
        bool: True if AAL2 authentication is valid, False otherwise

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> if not is_aal2_valid(user):
        ...     # Redirect to AAL2 challenge
        ...     return request.RESPONSE.redirect('@@aal2-challenge')
    """
    try:
        timestamp = get_aal2_timestamp(user)

        if timestamp is None:
            return False

        now = datetime.utcnow()

        # Reject future timestamps (clock skew or tampering)
        if timestamp > now:
            logger.warning(f"Future AAL2 timestamp detected for user {user.getId()}")
            return False

        # Check if within 15-minute window
        elapsed = (now - timestamp).total_seconds()
        is_valid = 0 <= elapsed <= AAL2_TIMEOUT_SECONDS

        if not is_valid:
            logger.debug(f"AAL2 session expired for user {user.getId()} (elapsed: {elapsed}s)")

        return is_valid

    except Exception as e:
        logger.error(f"Failed to validate AAL2 for user {user.getId()}: {e}", exc_info=True)
        return False


def get_aal2_expiry(user):
    """Get the AAL2 expiry time for a user.

    Calculates when the current AAL2 authentication will expire.

    Args:
        user: Plone user object with IAnnotations support

    Returns:
        datetime or None: The expiry time in UTC, or None if no timestamp exists

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> expiry = get_aal2_expiry(user)
        >>> if expiry:
        ...     print(f"AAL2 expires at: {expiry}")
    """
    try:
        timestamp = get_aal2_timestamp(user)

        if timestamp is None:
            return None

        expiry = timestamp + timedelta(seconds=AAL2_TIMEOUT_SECONDS)
        return expiry

    except Exception as e:
        logger.error(f"Failed to get AAL2 expiry for user {user.getId()}: {e}", exc_info=True)
        return None


def clear_aal2_timestamp(user):
    """Clear AAL2 authentication timestamp for a user.

    Removes the AAL2 timestamp from user annotations. This should be called:
    - When a user explicitly logs out
    - When forcing re-authentication
    - When invalidating an AAL2 session

    Args:
        user: Plone user object with IAnnotations support

    Returns:
        None

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> clear_aal2_timestamp(user)
        >>> assert not is_aal2_valid(user)
    """
    try:
        annotations = IAnnotations(user)

        # Remove the timestamp if it exists
        if ANNOTATION_KEY in annotations:
            del annotations[ANNOTATION_KEY]
            logger.info(f"Cleared AAL2 timestamp for user {user.getId()}")

    except Exception as e:
        logger.error(f"Failed to clear AAL2 timestamp for user {user.getId()}: {e}", exc_info=True)
        raise


def get_remaining_time(user):
    """Get remaining time before AAL2 expires (in seconds).

    Convenience function to display countdown timers in UI.

    Args:
        user: Plone user object with IAnnotations support

    Returns:
        int or None: Remaining seconds, or None if no valid timestamp

    Example:
        >>> user = portal.acl_users.getUserById('john_doe')
        >>> remaining = get_remaining_time(user)
        >>> if remaining:
        ...     print(f"AAL2 expires in {remaining // 60} minutes")
    """
    try:
        timestamp = get_aal2_timestamp(user)

        if timestamp is None:
            return None

        now = datetime.utcnow()
        elapsed = (now - timestamp).total_seconds()
        remaining = AAL2_TIMEOUT_SECONDS - elapsed

        return max(0, int(remaining))

    except Exception as e:
        logger.error(f"Failed to get remaining time for user {user.getId()}: {e}", exc_info=True)
        return None
