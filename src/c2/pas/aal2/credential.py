# -*- coding: utf-8 -*-
"""Passkey credential storage helpers for ZODB annotations.

Plone 6 Compatibility:
- Uses portal annotations instead of user annotations (MemberData doesn't support IAnnotations)
- Stores credentials in portal-level storage keyed by user ID
"""

from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict
from datetime import datetime, timezone
from plone import api
import base64
import logging

logger = logging.getLogger('c2.pas.aal2.credential')

# Annotation key for storing passkey credentials
PASSKEY_ANNOTATION_KEY = "c2.pas.aal2.passkeys"


def _get_passkey_storage():
    """Get the portal-level passkey storage container.

    Returns:
        PersistentDict: Portal annotations dict keyed by user_id
    """
    try:
        portal = api.portal.get()
        annotations = IAnnotations(portal)

        if PASSKEY_ANNOTATION_KEY not in annotations:
            annotations[PASSKEY_ANNOTATION_KEY] = PersistentDict()

        return annotations[PASSKEY_ANNOTATION_KEY]
    except Exception as e:
        logger.error(f"Failed to get passkey storage: {e}", exc_info=True)
        return PersistentDict()


def get_user_passkeys(user):
    """
    Retrieve all passkey credentials for a user.

    Plone 6 Compatible: Uses portal-level storage.

    Args:
        user: Plone user object

    Returns:
        PersistentDict: Dictionary of credential_id (base64url) -> credential_data
    """
    try:
        user_id = user.getId() if hasattr(user, 'getId') else str(user)
        storage = _get_passkey_storage()
        return storage.get(user_id, PersistentDict())
    except Exception as e:
        logger.error(f"Failed to get passkeys for user: {e}", exc_info=True)
        return PersistentDict()


def add_passkey(user, credential_data):
    """
    Add a new passkey credential to a user.

    Plone 6 Compatible: Uses portal-level storage.

    Args:
        user: Plone user object
        credential_data: Dict containing credential fields:
            - credential_id (bytes): Raw credential ID
            - public_key (bytes): COSE-encoded public key
            - sign_count (int): Initial sign count (default: 0)
            - aaguid (bytes): Authenticator AAGUID
            - device_name (str): User-friendly device name
            - device_type (str): "platform" or "cross-platform"
            - transports (list): Supported transport methods

    Returns:
        str: Base64url-encoded credential_id (the key used), or None on error
    """
    try:
        user_id = user.getId() if hasattr(user, 'getId') else str(user)
        storage = _get_passkey_storage()

        # Get or create user's passkey dict
        if user_id not in storage:
            storage[user_id] = PersistentDict()

        passkeys = storage[user_id]

        # Use base64url-encoded credential_id as dictionary key
        credential_id_bytes = credential_data['credential_id']
        credential_id_b64 = base64.urlsafe_b64encode(
            credential_id_bytes
        ).decode('ascii').rstrip('=')

        # Create persistent dict for this credential
        passkey = PersistentDict({
            'credential_id': credential_id_bytes,
            'public_key': credential_data['public_key'],
            'sign_count': credential_data.get('sign_count', 0),
            'aaguid': credential_data.get('aaguid', b''),
            'device_name': credential_data.get('device_name', ''),
            'device_type': credential_data.get('device_type', 'cross-platform'),
            'created': datetime.now(timezone.utc),
            'last_used': None,
            'transports': credential_data.get('transports', []),
        })

        passkeys[credential_id_b64] = passkey
        storage[user_id] = passkeys

        # Mark storage as modified for ZODB persistence
        storage._p_changed = True

        logger.info(f"Added passkey {credential_id_b64} for user {user.getId()}")
        return credential_id_b64

    except Exception as e:
        logger.error(f"Failed to add passkey: {e}", exc_info=True)
        return None


def get_passkey(user, credential_id):
    """
    Retrieve a specific passkey credential.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str

    Returns:
        PersistentDict: Credential data, or None if not found
    """
    try:
        passkeys = get_user_passkeys(user)

        if isinstance(credential_id, bytes):
            credential_id_b64 = base64.urlsafe_b64encode(
                credential_id
            ).decode('ascii').rstrip('=')
        else:
            credential_id_b64 = credential_id

        return passkeys.get(credential_id_b64)

    except Exception as e:
        logger.error(f"Failed to get passkey: {e}", exc_info=True)
        return None


def update_passkey_last_used(user, credential_id, new_sign_count):
    """
    Update last_used timestamp and sign_count after successful authentication.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str
        new_sign_count: int

    Returns:
        bool: True if updated, False if credential not found or error
    """
    try:
        passkey = get_passkey(user, credential_id)
        if passkey is None:
            logger.warning(f"Passkey not found for update: {credential_id}")
            return False

        passkey['last_used'] = datetime.now(timezone.utc)
        passkey['sign_count'] = new_sign_count

        # Mark storage as modified for ZODB persistence
        user_id = user.getId() if hasattr(user, 'getId') else str(user)
        storage = _get_passkey_storage()
        passkeys = storage.get(user_id, PersistentDict())
        storage[user_id] = passkeys
        storage._p_changed = True

        logger.info(f"Updated passkey last_used and sign_count for user {user.getId()}")
        return True

    except Exception as e:
        logger.error(f"Failed to update passkey: {e}", exc_info=True)
        return False


def delete_passkey(user, credential_id):
    """
    Delete a passkey credential.

    Plone 6 Compatible: Uses portal-level storage.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str

    Returns:
        bool: True if deleted, False if not found or error
    """
    try:
        user_id = user.getId() if hasattr(user, 'getId') else str(user)
        storage = _get_passkey_storage()
        passkeys = storage.get(user_id, PersistentDict())

        if isinstance(credential_id, bytes):
            credential_id_b64 = base64.urlsafe_b64encode(
                credential_id
            ).decode('ascii').rstrip('=')
        else:
            credential_id_b64 = credential_id

        if credential_id_b64 not in passkeys:
            logger.warning(f"Passkey not found for deletion: {credential_id_b64}")
            return False

        del passkeys[credential_id_b64]
        storage[user_id] = passkeys
        storage._p_changed = True

        logger.info(f"Deleted passkey {credential_id_b64} for user {user.getId()}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete passkey: {e}", exc_info=True)
        return False


def count_passkeys(user):
    """
    Count how many passkeys a user has registered.

    Args:
        user: Plone user object

    Returns:
        int: Number of registered passkeys
    """
    try:
        passkeys = get_user_passkeys(user)
        return len(passkeys)
    except Exception as e:
        logger.error(f"Failed to count passkeys: {e}", exc_info=True)
        return 0
