# -*- coding: utf-8 -*-
"""Audit logging for passkey authentication events."""

import logging
from datetime import datetime, timezone
from plone import api

logger = logging.getLogger('c2.pas.aal2.audit')


def log_event(event_type, user_id, success, credential_id=None, ip_address=None,
               user_agent=None, error_message=None, request=None, metadata=None):
    """
    Log a passkey authentication event to both Python logger and persistent storage.

    Args:
        event_type (str): Type of event (registration_start, registration_success, etc.)
        user_id (str): User ID
        success (bool): Whether the operation succeeded
        credential_id (str): Credential ID (if applicable)
        ip_address (str): Client IP address
        user_agent (str): Browser user agent
        error_message (str): Error message (if failed)
        request: HTTP request object (to extract IP/UA if not provided)
        metadata (dict): Additional event-specific metadata

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

    # Write to persistent ZODB storage (Feature 005: US2)
    try:
        from c2.pas.aal2.storage.audit import log_audit_event

        portal = api.portal.get()
        outcome = 'success' if success else 'failure'

        # Build metadata dict
        event_metadata = metadata or {}
        if credential_id:
            event_metadata['credential_id'] = credential_id
        if error_message:
            event_metadata['error_message'] = error_message

        log_audit_event(
            portal=portal,
            user_id=user_id,
            action_type=event_type,
            outcome=outcome,
            ip_address=ip_address or 'unknown',
            user_agent=user_agent or 'unknown',
            metadata=event_metadata
        )
    except Exception as e:
        # Fail open - don't break authentication if audit storage fails
        logger.error(f"Failed to write persistent audit log: {e}")

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


# AAL2-specific audit events

def log_aal2_timestamp_set(user_id, credential_id=None, request=None):
    """Log AAL2 authentication timestamp being set."""
    return log_event(
        event_type='aal2_timestamp_set',
        user_id=user_id,
        credential_id=credential_id,
        success=True,
        request=request
    )


def log_aal2_access_granted(user_id, content_path, time_since_auth=None, expiry_seconds=None, request=None):
    """Log successful AAL2 access to protected content."""
    metadata = {
        'content_path': content_path,
        'required_level': 'AAL2',
    }
    if time_since_auth is not None:
        metadata['time_since_auth'] = time_since_auth
    if expiry_seconds is not None:
        metadata['expiry_seconds'] = expiry_seconds

    event_data = log_event(
        event_type='aal2_access_granted',
        user_id=user_id,
        success=True,
        request=request,
        metadata=metadata
    )
    event_data['content_path'] = content_path
    logger.info(f"AAL2 access granted: user={user_id} content={content_path}")
    return event_data


def log_aal2_access_denied(user_id, content_path, reason, time_since_auth=None, expiry_seconds=None, request=None):
    """Log AAL2 access denial to protected content."""
    metadata = {
        'content_path': content_path,
        'required_level': 'AAL2',
        'denial_reason': reason,
    }
    if time_since_auth is not None:
        metadata['time_since_auth'] = time_since_auth
    if expiry_seconds is not None:
        metadata['expiry_seconds'] = expiry_seconds

    event_data = log_event(
        event_type='aal2_access_denied',
        user_id=user_id,
        success=False,
        error_message=reason,
        request=request,
        metadata=metadata
    )
    event_data['content_path'] = content_path
    event_data['denial_reason'] = reason
    logger.warning(f"AAL2 access denied: user={user_id} content={content_path} reason={reason}")
    return event_data


def log_aal2_policy_set(content_path, required, admin_user_id, request=None):
    """Log AAL2 policy being set on content."""
    metadata = {
        'content_path': content_path,
        'enabled': required,
        'changed_by': admin_user_id,
    }

    event_data = log_event(
        event_type='aal2_policy_set',
        user_id=admin_user_id,
        success=True,
        request=request,
        metadata=metadata
    )
    event_data['content_path'] = content_path
    event_data['aal2_required'] = required
    action = "enabled" if required else "disabled"
    logger.info(f"AAL2 policy {action}: content={content_path} by={admin_user_id}")
    return event_data


def log_aal2_role_assigned(user_id, admin_user_id, request=None):
    """Log AAL2 Required User role being assigned."""
    metadata = {
        'target_user_id': user_id,
        'role_name': 'AAL2 Required User',
        'changed_by': admin_user_id,
    }

    event_data = log_event(
        event_type='aal2_role_assigned',
        user_id=admin_user_id,  # Actor is the admin
        success=True,
        request=request,
        metadata=metadata
    )
    event_data['admin_user_id'] = admin_user_id
    logger.info(f"AAL2 role assigned: user={user_id} by={admin_user_id}")
    return event_data


def log_aal2_role_revoked(user_id, admin_user_id, request=None):
    """Log AAL2 Required User role being revoked."""
    metadata = {
        'target_user_id': user_id,
        'role_name': 'AAL2 Required User',
        'changed_by': admin_user_id,
    }

    event_data = log_event(
        event_type='aal2_role_revoked',
        user_id=admin_user_id,  # Actor is the admin
        success=True,
        request=request,
        metadata=metadata
    )
    event_data['admin_user_id'] = admin_user_id
    logger.info(f"AAL2 role revoked: user={user_id} by={admin_user_id}")
    return event_data
