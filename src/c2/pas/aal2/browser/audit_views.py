# -*- coding: utf-8 -*-
"""
Browser views for audit log API.

These views provide REST API endpoints for querying, exporting, and
managing audit logs. All views require appropriate permissions.
"""

from Products.Five.browser import BrowserView
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from AccessControl import Unauthorized
from zope.interface import alsoProvides
import json
import logging
from datetime import datetime, timedelta
import pytz

from c2.pas.aal2.storage.query import (
    query_audit_logs,
    export_audit_logs,
    cleanup_old_logs,
    get_audit_stats
)

logger = logging.getLogger('c2.pas.aal2.browser.audit_views')


class AuditLogQueryView(BrowserView):
    """
    Query audit logs with filtering and pagination.

    API Endpoint: @@audit-log-query
    Method: GET or POST
    Permission: Manage portal (cmf.ManagePortal)

    Query Parameters:
        - user_id (str): Filter by user ID
        - action_type (str): Filter by action type
        - outcome (str): Filter by outcome ('success' or 'failure')
        - start_date (str): Start date (ISO 8601 format)
        - end_date (str): End date (ISO 8601 format)
        - days (int): Number of days to query (alternative to start_date)
        - limit (int): Maximum results (default: 100, max: 1000)
        - offset (int): Pagination offset (default: 0)

    Returns:
        JSON response with format:
        {
            "events": [...],
            "total": int,
            "offset": int,
            "limit": int,
            "has_more": bool
        }

    Example:
        GET /@@audit-log-query?user_id=admin&days=7&limit=50
    """

    def __call__(self):
        """Process query request and return JSON response."""
        # Disable CSRF protection for API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Check permission
        if not api.user.has_permission('Manage portal', obj=self.context):
            raise Unauthorized("You must have portal management permissions")

        try:
            # Parse query parameters
            filters = self._parse_filters()
            limit = self._parse_int_param('limit', default=100, max_value=1000)
            offset = self._parse_int_param('offset', default=0)

            # Query audit logs
            portal = api.portal.get()
            results = query_audit_logs(
                portal=portal,
                filters=filters,
                limit=limit,
                offset=offset
            )

            # Return JSON response
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(results, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in audit log query: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({'error': str(e)})

    def _parse_filters(self):
        """Parse filter parameters from request."""
        filters = {}

        # User filter
        user_id = self.request.get('user_id')
        if user_id:
            filters['user_id'] = user_id

        # Action type filter
        action_type = self.request.get('action_type')
        if action_type:
            filters['action_type'] = action_type

        # Outcome filter
        outcome = self.request.get('outcome')
        if outcome and outcome in ('success', 'failure'):
            filters['outcome'] = outcome

        # Time range filters
        start_date = self.request.get('start_date')
        end_date = self.request.get('end_date')
        days = self.request.get('days')

        if start_date:
            try:
                filters['start_time'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")

        if end_date:
            try:
                filters['end_time'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")

        if days and not start_date:
            try:
                days_int = int(days)
                filters['start_time'] = datetime.now(pytz.UTC) - timedelta(days=days_int)
            except ValueError:
                logger.warning(f"Invalid days parameter: {days}")

        return filters

    def _parse_int_param(self, param_name, default=0, max_value=None):
        """Parse integer parameter with default and max value."""
        value_str = self.request.get(param_name)
        if not value_str:
            return default

        try:
            value = int(value_str)
            if max_value and value > max_value:
                return max_value
            return max(0, value)  # Ensure non-negative
        except ValueError:
            logger.warning(f"Invalid {param_name} parameter: {value_str}")
            return default


class AuditLogExportView(BrowserView):
    """
    Export audit logs to CSV or JSON format.

    API Endpoint: @@audit-log-export
    Method: GET
    Permission: Manage portal (cmf.ManagePortal)

    Query Parameters:
        - format (str): 'csv' or 'json' (default: csv)
        - user_id (str): Filter by user ID
        - action_type (str): Filter by action type
        - outcome (str): Filter by outcome
        - start_date (str): Start date (ISO 8601)
        - end_date (str): End date (ISO 8601)
        - days (int): Number of days to export

    Returns:
        File download with appropriate Content-Type and Content-Disposition headers

    Example:
        GET /@@audit-log-export?format=csv&days=30
    """

    def __call__(self):
        """Process export request and return file."""
        # Disable CSRF protection for API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Check permission
        if not api.user.has_permission('Manage portal', obj=self.context):
            raise Unauthorized("You must have portal management permissions")

        try:
            # Parse parameters
            export_format = self.request.get('format', 'csv')
            if export_format not in ('csv', 'json'):
                export_format = 'csv'

            filters = self._parse_filters()

            # Export audit logs
            portal = api.portal.get()
            content, content_type, filename = export_audit_logs(
                portal=portal,
                format=export_format,
                filters=filters
            )

            # Set response headers
            self.request.response.setHeader('Content-Type', content_type)
            self.request.response.setHeader(
                'Content-Disposition',
                f'attachment; filename="{filename}"'
            )

            return content

        except Exception as e:
            logger.error(f"Error exporting audit logs: {e}", exc_info=True)
            self.request.response.setStatus(500)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({'error': str(e)})

    def _parse_filters(self):
        """Parse filter parameters from request (same as query view)."""
        filters = {}

        user_id = self.request.get('user_id')
        if user_id:
            filters['user_id'] = user_id

        action_type = self.request.get('action_type')
        if action_type:
            filters['action_type'] = action_type

        outcome = self.request.get('outcome')
        if outcome and outcome in ('success', 'failure'):
            filters['outcome'] = outcome

        start_date = self.request.get('start_date')
        end_date = self.request.get('end_date')
        days = self.request.get('days')

        if start_date:
            try:
                filters['start_time'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                pass

        if end_date:
            try:
                filters['end_time'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                pass

        if days and not start_date:
            try:
                days_int = int(days)
                filters['start_time'] = datetime.now(pytz.UTC) - timedelta(days=days_int)
            except ValueError:
                pass

        return filters


class AuditLogStatsView(BrowserView):
    """
    Get audit log statistics.

    API Endpoint: @@audit-log-stats
    Method: GET
    Permission: Manage portal (cmf.ManagePortal)

    Returns:
        JSON response with statistics:
        {
            "total_events": int,
            "created": str (ISO 8601),
            "last_cleaned": str (ISO 8601),
            "retention_days": int,
            "users_count": int,
            "action_types_count": int,
            "recent_activity": {...},
            "recent_events_24h": int,
            "success_events": int,
            "failure_events": int,
            "success_rate": float
        }

    Example:
        GET /@@audit-log-stats
    """

    def __call__(self):
        """Return audit log statistics."""
        # Disable CSRF protection for API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Check permission
        if not api.user.has_permission('Manage portal', obj=self.context):
            raise Unauthorized("You must have portal management permissions")

        try:
            portal = api.portal.get()
            stats = get_audit_stats(portal)

            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(stats, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error getting audit stats: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({'error': str(e)})


class AuditLogCleanupView(BrowserView):
    """
    Manually trigger audit log cleanup.

    API Endpoint: @@audit-log-cleanup
    Method: POST
    Permission: Manage portal (cmf.ManagePortal)

    POST Parameters:
        - retention_days (int): Number of days to retain (optional)

    Returns:
        JSON response with cleanup results:
        {
            "deleted_count": int,
            "retention_days": int,
            "cutoff_date": str (ISO 8601),
            "remaining_count": int,
            "initial_count": int
        }

    Example:
        POST /@@audit-log-cleanup
        Content-Type: application/json
        {"retention_days": 90}
    """

    def __call__(self):
        """Perform cleanup and return results."""
        # Disable CSRF protection for API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Check permission
        if not api.user.has_permission('Manage portal', obj=self.context):
            raise Unauthorized("You must have portal management permissions")

        # Only allow POST
        if self.request.method != 'POST':
            self.request.response.setStatus(405)
            return json.dumps({'error': 'Method not allowed, use POST'})

        try:
            # Parse retention_days parameter
            retention_days = None
            try:
                body = self.request.get('BODY', '{}')
                if body:
                    data = json.loads(body)
                    if 'retention_days' in data:
                        retention_days = int(data['retention_days'])
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid request body: {e}")

            # Perform cleanup
            portal = api.portal.get()
            result = cleanup_old_logs(portal, retention_days=retention_days)

            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(result, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({'error': str(e)})
