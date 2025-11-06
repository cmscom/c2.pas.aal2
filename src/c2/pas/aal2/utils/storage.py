# -*- coding: utf-8 -*-
"""ZODB annotation utility functions for passkey storage."""

from zope.annotation.interfaces import IAnnotations
from persistent.dict import PersistentDict
import logging

logger = logging.getLogger('c2.pas.aal2.utils.storage')


def get_annotation(obj, key, default=None):
    """
    Get an annotation value from a ZODB object.

    Args:
        obj: ZODB object with IAnnotations support
        key (str): Annotation key
        default: Default value if annotation not found

    Returns:
        Annotation value or default
    """
    try:
        annotations = IAnnotations(obj)
        return annotations.get(key, default)
    except Exception as e:
        logger.error(f"Failed to get annotation {key}: {e}", exc_info=True)
        return default


def set_annotation(obj, key, value):
    """
    Set an annotation value on a ZODB object.

    Args:
        obj: ZODB object with IAnnotations support
        key (str): Annotation key
        value: Value to store (should be ZODB-persistent type)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        annotations = IAnnotations(obj)
        annotations[key] = value
        obj._p_changed = True
        return True
    except Exception as e:
        logger.error(f"Failed to set annotation {key}: {e}", exc_info=True)
        return False


def delete_annotation(obj, key):
    """
    Delete an annotation from a ZODB object.

    Args:
        obj: ZODB object with IAnnotations support
        key (str): Annotation key

    Returns:
        bool: True if deleted, False if not found or error
    """
    try:
        annotations = IAnnotations(obj)
        if key in annotations:
            del annotations[key]
            obj._p_changed = True
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete annotation {key}: {e}", exc_info=True)
        return False


def get_or_create_persistent_dict(obj, key):
    """
    Get an existing PersistentDict annotation or create a new one.

    Args:
        obj: ZODB object with IAnnotations support
        key (str): Annotation key

    Returns:
        PersistentDict: Existing or newly created persistent dict
    """
    try:
        annotations = IAnnotations(obj)
        if key not in annotations:
            annotations[key] = PersistentDict()
            obj._p_changed = True
        return annotations[key]
    except Exception as e:
        logger.error(f"Failed to get/create persistent dict {key}: {e}", exc_info=True)
        return PersistentDict()


def update_persistent_dict(obj, key, updates):
    """
    Update a PersistentDict annotation with new values.

    Args:
        obj: ZODB object with IAnnotations support
        key (str): Annotation key
        updates (dict): Dictionary of updates to apply

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        persistent_dict = get_or_create_persistent_dict(obj, key)
        persistent_dict.update(updates)

        annotations = IAnnotations(obj)
        annotations[key] = persistent_dict
        obj._p_changed = True
        return True
    except Exception as e:
        logger.error(f"Failed to update persistent dict {key}: {e}", exc_info=True)
        return False
