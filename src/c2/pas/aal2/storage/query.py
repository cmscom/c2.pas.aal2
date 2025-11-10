# -*- coding: utf-8 -*-
"""
Query and export functions for audit logs.

This module provides high-level query, export, and maintenance functions
for the audit log system. It builds on the AuditLogContainer primitives
to provide filtering, formatting, and bulk operations.
"""

import logging
import csv
import json
from datetime import datetime, timedelta
from io import StringIO
import pytz

from .audit import get_audit_container

logger = logging.getLogger('c2.pas.aal2.storage.query')


def query_audit_logs(portal, filters=None, limit=None, offset=0):
    """
    Query audit logs with multiple filter criteria.

    Args:
        portal: Plone portal object
        filters (dict): Optional filter criteria:
            - user_id (str): Filter by user ID
            - action_type (str): Filter by action type
            - outcome (str): Filter by outcome ('success' or 'failure')
            - start_time (datetime): Start of time range
            - end_time (datetime): End of time range
        limit (int): Maximum number of results to return
        offset (int): Number of results to skip (for pagination)

    Returns:
        dict: Query results with format:
            {
                'events': [list of event dicts],
                'total': int,
                'offset': int,
                'limit': int,
                'has_more': bool
            }

    Example:
        >>> results = query_audit_logs(
        ...     portal,
        ...     filters={
        ...         'user_id': 'admin',
        ...         'action_type': 'authentication_success',
        ...         'start_time': datetime.now() - timedelta(days=7)
        ...     },
        ...     limit=50
        ... )
        >>> print(f"Found {results['total']} events")
    """
    try:
        container = get_audit_container(portal)
        filters = filters or {}

        # Determine which query method to use based on filters
        if 'user_id' in filters:
            # User-specific query
            events = container.query_by_user(
                user_id=filters['user_id'],
                start_time=filters.get('start_time'),
                end_time=filters.get('end_time')
            )
        elif 'action_type' in filters:
            # Action-specific query
            events = container.query_by_action(
                action_type=filters['action_type'],
                start_time=filters.get('start_time'),
                end_time=filters.get('end_time')
            )
        elif 'outcome' in filters:
            # Outcome-specific query
            events = container.query_by_outcome(
                outcome=filters['outcome'],
                start_time=filters.get('start_time'),
                end_time=filters.get('end_time')
            )
        else:
            # Time-based query only
            events = container.query_by_timestamp(
                start_time=filters.get('start_time'),
                end_time=filters.get('end_time')
            )

        # Apply additional filters in memory (for multi-criteria queries)
        if 'user_id' in filters and 'action_type' in filters:
            events = [e for e in events if e.action_type == filters['action_type']]
        if 'user_id' in filters and 'outcome' in filters:
            events = [e for e in events if e.outcome == filters['outcome']]
        if 'action_type' in filters and 'outcome' in filters:
            events = [e for e in events if e.outcome == filters['outcome']]

        # Sort by timestamp descending (most recent first)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        # Get total count before pagination
        total = len(events)

        # Apply pagination
        end_index = offset + limit if limit else len(events)
        paginated_events = events[offset:end_index]

        # Convert to dicts
        event_dicts = [e.to_dict() for e in paginated_events]

        return {
            'events': event_dicts,
            'total': total,
            'offset': offset,
            'limit': limit,
            'has_more': (offset + len(paginated_events)) < total
        }

    except Exception as e:
        logger.error(f"Error querying audit logs: {e}", exc_info=True)
        return {
            'events': [],
            'total': 0,
            'offset': 0,
            'limit': limit,
            'has_more': False,
            'error': str(e)
        }


def export_audit_logs(portal, format='csv', filters=None):
    """
    Export audit logs to CSV or JSON format.

    Args:
        portal: Plone portal object
        format (str): Export format - 'csv' or 'json'
        filters (dict): Optional filter criteria (same as query_audit_logs)

    Returns:
        tuple: (content_string, content_type, filename)
            - content_string (str): Exported data as string
            - content_type (str): MIME type for HTTP response
            - filename (str): Suggested filename with extension

    Example:
        >>> content, content_type, filename = export_audit_logs(
        ...     portal,
        ...     format='csv',
        ...     filters={'start_time': datetime.now() - timedelta(days=30)}
        ... )
        >>> # Use in browser view:
        >>> self.request.response.setHeader('Content-Type', content_type)
        >>> self.request.response.setHeader('Content-Disposition', f'attachment; filename="{filename}"')
        >>> return content
    """
    try:
        # Query all matching events (no pagination for export)
        results = query_audit_logs(portal, filters=filters)
        events = results['events']

        timestamp_str = datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')

        if format == 'csv':
            return _export_csv(events, timestamp_str)
        elif format == 'json':
            return _export_json(events, timestamp_str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    except Exception as e:
        logger.error(f"Error exporting audit logs: {e}", exc_info=True)
        # Return error as JSON
        error_data = json.dumps({'error': str(e)}, indent=2)
        return error_data, 'application/json', f'error_{timestamp_str}.json'


def _export_csv(events, timestamp_str):
    """
    Export events to CSV format.

    Args:
        events (list): List of event dicts
        timestamp_str (str): Timestamp string for filename

    Returns:
        tuple: (csv_content, content_type, filename)
    """
    output = StringIO()

    if not events:
        return '', 'text/csv', f'audit_log_{timestamp_str}.csv'

    # Define CSV columns
    fieldnames = [
        'event_id', 'timestamp', 'user_id', 'action_type',
        'outcome', 'ip_address', 'user_agent', 'metadata'
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for event in events:
        # Flatten metadata to JSON string for CSV
        row = dict(event)
        row['metadata'] = json.dumps(event['metadata'])
        writer.writerow(row)

    csv_content = output.getvalue()
    output.close()

    return csv_content, 'text/csv', f'audit_log_{timestamp_str}.csv'


def _export_json(events, timestamp_str):
    """
    Export events to JSON format.

    Args:
        events (list): List of event dicts
        timestamp_str (str): Timestamp string for filename

    Returns:
        tuple: (json_content, content_type, filename)
    """
    export_data = {
        'export_time': datetime.now(pytz.UTC).isoformat(),
        'event_count': len(events),
        'events': events
    }

    json_content = json.dumps(export_data, indent=2, ensure_ascii=False)

    return json_content, 'application/json', f'audit_log_{timestamp_str}.json'


def cleanup_old_logs(portal, retention_days=None):
    """
    Delete audit logs older than retention period.

    Args:
        portal: Plone portal object
        retention_days (int): Number of days to retain (None = use container default)

    Returns:
        dict: Cleanup results:
            {
                'deleted_count': int,
                'retention_days': int,
                'cutoff_date': str (ISO format),
                'remaining_count': int
            }

    This function should be called:
    - Daily via cron job
    - On-demand from control panel
    - After changing retention policy

    Example:
        >>> result = cleanup_old_logs(portal, retention_days=90)
        >>> logger.info(f"Deleted {result['deleted_count']} old events")
    """
    try:
        container = get_audit_container(portal)

        # Use specified retention or container default
        if retention_days is None:
            retention_days = container.metadata.get('retention_days', 90)

        # Calculate cutoff date
        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=retention_days)

        # Get count before cleanup
        initial_count = container.metadata['total_events']

        # Perform cleanup
        deleted_count = container.cleanup_old_events(cutoff_date)

        # Get count after cleanup
        remaining_count = container.metadata['total_events']

        logger.info(
            f"Cleanup complete: deleted {deleted_count} events, "
            f"{remaining_count} remaining (retention: {retention_days} days)"
        )

        return {
            'deleted_count': deleted_count,
            'retention_days': retention_days,
            'cutoff_date': cutoff_date.isoformat(),
            'remaining_count': remaining_count,
            'initial_count': initial_count
        }

    except Exception as e:
        logger.error(f"Error cleaning up audit logs: {e}", exc_info=True)
        return {
            'deleted_count': 0,
            'retention_days': retention_days or 90,
            'error': str(e)
        }


def get_audit_stats(portal):
    """
    Get comprehensive audit log statistics.

    Args:
        portal: Plone portal object

    Returns:
        dict: Statistics including:
            - total_events: Total number of events
            - created: Container creation date
            - last_cleaned: Last cleanup date
            - retention_days: Current retention policy
            - users_count: Number of unique users
            - action_types_count: Number of unique action types
            - recent_activity: Events in last 24 hours by action type
            - success_rate: Overall success rate percentage

    Example:
        >>> stats = get_audit_stats(portal)
        >>> print(f"Success rate: {stats['success_rate']:.1f}%")
    """
    try:
        container = get_audit_container(portal)

        # Get base stats from container
        base_stats = container.get_stats()

        # Calculate additional stats
        now = datetime.now(pytz.UTC)
        last_24h = now - timedelta(hours=24)

        # Recent activity by action type
        recent_events = container.query_by_timestamp(start_time=last_24h, end_time=now)
        recent_by_action = {}
        for event in recent_events:
            action = event.action_type
            recent_by_action[action] = recent_by_action.get(action, 0) + 1

        # Success rate calculation
        success_events = len(container.query_by_outcome('success'))
        failure_events = len(container.query_by_outcome('failure'))
        total_with_outcome = success_events + failure_events
        success_rate = (success_events / total_with_outcome * 100) if total_with_outcome > 0 else 0

        return {
            **base_stats,
            'recent_activity': recent_by_action,
            'recent_events_24h': len(recent_events),
            'success_events': success_events,
            'failure_events': failure_events,
            'success_rate': round(success_rate, 2)
        }

    except Exception as e:
        logger.error(f"Error getting audit stats: {e}", exc_info=True)
        return {'error': str(e)}
