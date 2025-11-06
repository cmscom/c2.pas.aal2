# -*- coding: utf-8 -*-
"""Passkey credential storage helpers for ZODB annotations."""

from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict
from datetime import datetime, timezone
import base64
import logging

logger = logging.getLogger('c2.pas.aal2.credential')

# Annotation key for storing passkey credentials
PASSKEY_ANNOTATION_KEY = "c2.pas.aal2.passkeys"


def get_user_passkeys(user):
    """
    Retrieve all passkey credentials for a user.

    Args:
        user: Plone user object

    Returns:
        PersistentDict: Dictionary of credential_id (base64url) -> credential_data
    """
    try:
        annotations = IAnnotations(user)
        return annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())
    except Exception as e:
        logger.error(f"Failed to get passkeys for user: {e}", exc_info=True)
        return PersistentDict()


def add_passkey(user, credential_data):
    """
    Add a new passkey credential to a user.

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
        annotations = IAnnotations(user)
        passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

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
        annotations[PASSKEY_ANNOTATION_KEY] = passkeys

        # Mark object as modified for ZODB persistence
        user._p_changed = True

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

        # Mark annotation and user as modified
        annotations = IAnnotations(user)
        passkeys = get_user_passkeys(user)
        annotations[PASSKEY_ANNOTATION_KEY] = passkeys
        user._p_changed = True

        logger.info(f"Updated passkey last_used and sign_count for user {user.getId()}")
        return True

    except Exception as e:
        logger.error(f"Failed to update passkey: {e}", exc_info=True)
        return False


def delete_passkey(user, credential_id):
    """
    Delete a passkey credential.

    Args:
        user: Plone user object
        credential_id: bytes or base64url-encoded str

    Returns:
        bool: True if deleted, False if not found or error
    """
    try:
        annotations = IAnnotations(user)
        passkeys = annotations.get(PASSKEY_ANNOTATION_KEY, PersistentDict())

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
        annotations[PASSKEY_ANNOTATION_KEY] = passkeys
        user._p_changed = True

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
