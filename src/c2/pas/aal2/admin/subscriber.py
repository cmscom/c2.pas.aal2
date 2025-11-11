# -*- coding: utf-8 -*-
"""Event subscriber for admin AAL2 protection."""

import logging
from plone import api

logger = logging.getLogger('c2.pas.aal2.admin.subscriber')


def check_admin_aal2_subscriber(event):
    """Subscriber to check AAL2 on admin access.

    This event subscriber intercepts requests via IPubBeforeCommit,
    checks if the requested URL requires AAL2 protection, and
    redirects to challenge page if AAL2 session is expired.

    Args:
        event: IPubBeforeCommit event

    Example:
        Registered in configure.zcml:
        <subscriber
            for="ZPublisher.interfaces.IPubBeforeCommit"
            handler=".subscriber.check_admin_aal2_subscriber"
            />
    """
    request = event.request

    try:
        # Get current user
        user = api.user.get_current()
        if not user or user.getId() is None:
            # Anonymous user - let normal auth handle it
            logger.debug("Skipping AAL2 check for anonymous user")
            return

        # Check if admin access allowed
        from c2.pas.aal2.admin.protection import check_admin_access
        result = check_admin_access(request, user)

        if not result['allowed']:
            logger.info(f"AAL2 check failed for user {user.getId()}: {result['reason']}")

            # Store redirect context
            from c2.pas.aal2.admin.protection import store_redirect_context
            store_redirect_context(request, request.URL)

            # Log the challenge event
            try:
                from c2.pas.aal2.utils.audit import log_audit_event
                log_audit_event(
                    event_type='admin_access_challenged',
                    user_id=user.getId(),
                    details={
                        'admin_url': request.URL,
                        'aal2_valid': False,
                        'reason': result['reason'],
                    }
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit event: {audit_error}")

            # Redirect to challenge
            request.response.redirect(result['redirect_url'])
        else:
            # Access allowed - optionally log for audit
            if result['reason'] == 'aal2_valid':
                try:
                    from c2.pas.aal2.admin.protection import is_protected_url
                    if is_protected_url(request.URL):
                        from c2.pas.aal2.utils.audit import log_audit_event
                        log_audit_event(
                            event_type='admin_access_allowed',
                            user_id=user.getId(),
                            details={
                                'admin_url': request.URL,
                                'aal2_valid': True,
                            }
                        )
                except Exception as audit_error:
                    logger.warning(f"Failed to log audit event: {audit_error}")

    except Exception as e:
        logger.exception(f"Error in admin AAL2 subscriber: {e}")
        # Don't block requests on error - fail open for availability
