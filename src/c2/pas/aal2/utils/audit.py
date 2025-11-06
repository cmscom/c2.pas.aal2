# -*- coding: utf-8 -*-
"""Audit logging for passkey authentication events."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger('c2.pas.aal2.audit')


def log_event(event_type, user_id, success, credential_id=None, ip_address=None,
               user_agent=None, error_message=None, request=None):
    """
    Log a passkey authentication event.

    Args:
        event_type (str): Type of event (registration_start, registration_success, etc.)
        user_id (str): User ID
        success (bool): Whether the operation succeeded
        credential_id (str): Credential ID (if applicable)
        ip_address (str): Client IP address
        user_agent (str): Browser user agent
        error_message (str): Error message (if failed)
        request: HTTP request object (to extract IP/UA if not provided)

    Returns:
        dict: Event data that was logged
    """
    # Extract IP and UA from request if not provided
    if request:
        if not ip_address:
            ip_address = request.get('HTTP_X_FORWARDED_FOR',
                                     request.get('REMOTE_ADDR', 'unknown'))
        if not user_agent:
            user_agent = request.get('HTTP_USER_AGENT', 'unknown')

    event_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'success': success,
        'credential_id': credential_id,
        'ip_address': ip_address or 'unknown',
        'user_agent': user_agent or 'unknown',
        'error_message': error_message,
    }

    # Log to Python logger (can be configured to go to syslog, file, etc.)
    log_message = (
        f"[{event_type}] user={user_id} success={success} "
        f"credential={credential_id} ip={ip_address}"
    )

    if success:
        logger.info(log_message, extra=event_data)
    else:
        logger.warning(log_message + f" error={error_message}", extra=event_data)

    # TODO: Could also write to Plone audit log or separate database table
    # For now, using Python logging is sufficient

    return event_data


def log_registration_start(user_id, request):
    """Log the start of a passkey registration ceremony."""
    return log_event(
        event_type='registration_start',
        user_id=user_id,
        success=True,
        request=request
    )


def log_registration_success(user_id, credential_id, request):
    """Log successful passkey registration."""
    return log_event(
        event_type='registration_success',
        user_id=user_id,
        credential_id=credential_id,
        success=True,
        request=request
    )


def log_registration_failure(user_id, error_message, request):
    """Log failed passkey registration."""
    return log_event(
        event_type='registration_failure',
        user_id=user_id,
        success=False,
        error_message=error_message,
        request=request
    )


def log_authentication_start(username, request):
    """Log the start of a passkey authentication ceremony."""
    return log_event(
        event_type='authentication_start',
        user_id=username,
        success=True,
        request=request
    )


def log_authentication_success(user_id, credential_id, request):
    """Log successful passkey authentication."""
    return log_event(
        event_type='authentication_success',
        user_id=user_id,
        credential_id=credential_id,
        success=True,
        request=request
    )


def log_authentication_failure(username, error_message, credential_id=None, request=None):
    """Log failed passkey authentication."""
    return log_event(
        event_type='authentication_failure',
        user_id=username,
        credential_id=credential_id,
        success=False,
        error_message=error_message,
        request=request
    )


def log_credential_deleted(user_id, credential_id, request):
    """Log passkey credential deletion."""
    return log_event(
        event_type='credential_deleted',
        user_id=user_id,
        credential_id=credential_id,
        success=True,
        request=request
    )
