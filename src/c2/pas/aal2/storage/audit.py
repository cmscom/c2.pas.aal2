# -*- coding: utf-8 -*-
"""
Persistent audit log storage for c2.pas.aal2.

This module provides ZODB-based persistent storage for authentication
and security audit events. Events are stored in portal annotations with
multiple indexes for efficient querying.

Storage Architecture:
- Primary storage: OOBTree indexed by timestamp
- Secondary indexes: user_id, action_type, outcome
- Retention policy: Configurable (default 90 days)

Thread Safety:
- All operations are ZODB transaction-aware
- Concurrent access is safe via MVCC
- No explicit locking required

Performance:
- add_event(): O(log n)
- query operations: O(log n + k) where k = result size
- cleanup: O(k log n) where k = events to delete
"""

import logging
import uuid
from datetime import datetime, timedelta
from persistent import Persistent
from persistent.mapping import PersistentMapping
from BTrees.OOBTree import OOBTree
from BTrees.IOBTree import IOBTree
from zope.annotation.interfaces import IAnnotations
import pytz

logger = logging.getLogger('c2.pas.aal2.storage.audit')

# Annotation key for audit log container
AUDIT_LOG_KEY = 'c2.pas.aal2.audit_logs'

# Default retention period in days
DEFAULT_RETENTION_DAYS = 90

# Valid action types
AUDIT_ACTION_TYPES = [
    # Passkey Registration
    'registration_start',
    'registration_success',
    'registration_failure',
    # Authentication
    'authentication_start',
    'authentication_success',
    'authentication_failure',
    # Credential Management
    'credential_deleted',
    'credential_updated',
    # AAL2 Operations
    'aal2_timestamp_set',
    'aal2_access_granted',
    'aal2_access_denied',
    'aal2_policy_set',
    # Role Management
    'aal2_role_assigned',
    'aal2_role_revoked',
]


class AuditEvent(Persistent):
    """
    Represents a single security or authentication event.

    All timestamps are UTC. Metadata is JSON-serializable dict.
    Event objects are immutable after creation (except for ZODB internal state).
    """

    def __init__(self, user_id, action_type, outcome, ip_address, user_agent, metadata=None):
        """
        Create a new audit event.

        Args:
            user_id (str): Plone user ID or 'anonymous'
            action_type (str): One of AUDIT_ACTION_TYPES
            outcome (str): 'success' or 'failure'
            ip_address (str): Source IP address
            user_agent (str): Browser User-Agent header
            metadata (dict): Action-specific data (optional)

        Raises:
            ValueError: If action_type or outcome is invalid
        """
        # Validation
        if action_type not in AUDIT_ACTION_TYPES:
            raise ValueError(f"Invalid action_type: {action_type}")
        if outcome not in ('success', 'failure'):
            raise ValueError(f"Invalid outcome: {outcome}")

        # Initialize fields
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now(pytz.UTC)
        self.user_id = user_id or 'anonymous'
        self.action_type = action_type
        self.outcome = outcome
        self.ip_address = ip_address or 'unknown'
        self.user_agent = user_agent or 'unknown'
        self.metadata = metadata or {}

    def to_dict(self):
        """
        Convert event to JSON-serializable dictionary.

        Returns:
            dict: Event data suitable for JSON serialization
        """
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'action_type': self.action_type,
            'outcome': self.outcome,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'metadata': self.metadata,
        }

    def __repr__(self):
        return f"<AuditEvent {self.event_id} {self.action_type} {self.outcome}>"


class AuditLogContainer(Persistent):
    """
    Top-level container for audit events with multiple indexes.

    Storage structure:
    - events: OOBTree(timestamp_float -> AuditEvent)
    - by_user: OOBTree(user_id -> IOBTree(timestamp_float -> event_id))
    - by_action: OOBTree(action_type -> IOBTree(timestamp_float -> event_id))
    - by_outcome: OOBTree(outcome -> IOBTree(timestamp_float -> event_id))
    - metadata: PersistentMapping with container metadata

    All indexes use timestamp as secondary key to ensure uniqueness
    and enable time-range queries within filtered results.
    """

    def __init__(self):
        """Initialize empty audit log container."""
        super(AuditLogContainer, self).__init__()

        # Primary storage: timestamp -> event
        self.events = OOBTree()

        # Secondary indexes: dimension -> (timestamp -> event_id)
        self.by_user = OOBTree()
        self.by_action = OOBTree()
        self.by_outcome = OOBTree()

        # Container metadata
        self.metadata = PersistentMapping()
        self.metadata['created'] = datetime.now(pytz.UTC)
        self.metadata['last_cleaned'] = None
        self.metadata['total_events'] = 0
        self.metadata['retention_days'] = DEFAULT_RETENTION_DAYS

    def add_event(self, event):
        """
        Add an audit event to the container and update all indexes.

        Args:
            event (AuditEvent): Event to add

        Returns:
            str: Event ID of added event

        Complexity: O(log n) for primary storage + 3 * O(log m) for indexes
        where n = total events, m = events in each index bucket
        """
        # Convert timestamp to float for BTree key
        timestamp_key = event.timestamp.timestamp()

        # Handle timestamp collisions (unlikely but possible)
        while timestamp_key in self.events:
            timestamp_key += 0.000001

        # Add to primary storage
        self.events[timestamp_key] = event

        # Update user index
        if event.user_id not in self.by_user:
            self.by_user[event.user_id] = IOBTree()
        self.by_user[event.user_id][int(timestamp_key * 1000000)] = event.event_id

        # Update action index
        if event.action_type not in self.by_action:
            self.by_action[event.action_type] = IOBTree()
        self.by_action[event.action_type][int(timestamp_key * 1000000)] = event.event_id

        # Update outcome index
        if event.outcome not in self.by_outcome:
            self.by_outcome[event.outcome] = IOBTree()
        self.by_outcome[event.outcome][int(timestamp_key * 1000000)] = event.event_id

        # Update metadata
        self.metadata['total_events'] += 1
        self._p_changed = True

        logger.debug(
            f"Added audit event: {event.event_id} "
            f"({event.user_id}, {event.action_type}, {event.outcome})"
        )

        return event.event_id

    def query_by_timestamp(self, start_time=None, end_time=None):
        """
        Query events by timestamp range.

        Args:
            start_time (datetime): Start of range (inclusive), None = no lower bound
            end_time (datetime): End of range (inclusive), None = no upper bound

        Returns:
            list[AuditEvent]: Events in range, ordered by timestamp

        Complexity: O(log n + k) where k = result size
        """
        start_key = start_time.timestamp() if start_time else None
        end_key = end_time.timestamp() if end_time else None

        results = []
        for timestamp_key in self.events.keys(min=start_key, max=end_key):
            results.append(self.events[timestamp_key])

        return results

    def query_by_user(self, user_id, start_time=None, end_time=None):
        """
        Query events for a specific user.

        Args:
            user_id (str): User ID to filter by
            start_time (datetime): Optional start time
            end_time (datetime): Optional end time

        Returns:
            list[AuditEvent]: Events for user in time range

        Complexity: O(log n + k) where k = result size
        """
        if user_id not in self.by_user:
            return []

        user_index = self.by_user[user_id]
        start_key = int(start_time.timestamp() * 1000000) if start_time else None
        end_key = int(end_time.timestamp() * 1000000) if end_time else None

        results = []
        for timestamp_key in user_index.keys(min=start_key, max=end_key):
            # Look up event by timestamp (convert back from microseconds)
            event_timestamp = timestamp_key / 1000000.0
            if event_timestamp in self.events:
                results.append(self.events[event_timestamp])

        return results

    def query_by_action(self, action_type, start_time=None, end_time=None):
        """
        Query events by action type.

        Args:
            action_type (str): Action type to filter by
            start_time (datetime): Optional start time
            end_time (datetime): Optional end time

        Returns:
            list[AuditEvent]: Events of specified type in time range

        Complexity: O(log n + k) where k = result size
        """
        if action_type not in self.by_action:
            return []

        action_index = self.by_action[action_type]
        start_key = int(start_time.timestamp() * 1000000) if start_time else None
        end_key = int(end_time.timestamp() * 1000000) if end_time else None

        results = []
        for timestamp_key in action_index.keys(min=start_key, max=end_key):
            event_timestamp = timestamp_key / 1000000.0
            if event_timestamp in self.events:
                results.append(self.events[event_timestamp])

        return results

    def query_by_outcome(self, outcome, start_time=None, end_time=None):
        """
        Query events by outcome.

        Args:
            outcome (str): 'success' or 'failure'
            start_time (datetime): Optional start time
            end_time (datetime): Optional end time

        Returns:
            list[AuditEvent]: Events with specified outcome in time range

        Complexity: O(log n + k) where k = result size
        """
        if outcome not in self.by_outcome:
            return []

        outcome_index = self.by_outcome[outcome]
        start_key = int(start_time.timestamp() * 1000000) if start_time else None
        end_key = int(end_time.timestamp() * 1000000) if end_time else None

        results = []
        for timestamp_key in outcome_index.keys(min=start_key, max=end_key):
            event_timestamp = timestamp_key / 1000000.0
            if event_timestamp in self.events:
                results.append(self.events[event_timestamp])

        return results

    def cleanup_old_events(self, before_timestamp):
        """
        Delete events older than specified timestamp.

        Args:
            before_timestamp (datetime): Delete events before this time

        Returns:
            int: Number of events deleted

        Complexity: O(k log n) where k = events to delete
        """
        before_key = before_timestamp.timestamp()
        deleted_count = 0

        # Collect events to delete
        events_to_delete = []
        for timestamp_key in list(self.events.keys()):
            if timestamp_key < before_key:
                events_to_delete.append((timestamp_key, self.events[timestamp_key]))

        # Delete from primary storage and indexes
        for timestamp_key, event in events_to_delete:
            # Remove from primary storage
            del self.events[timestamp_key]

            # Remove from user index
            user_ts_key = int(timestamp_key * 1000000)
            if event.user_id in self.by_user and user_ts_key in self.by_user[event.user_id]:
                del self.by_user[event.user_id][user_ts_key]
                if len(self.by_user[event.user_id]) == 0:
                    del self.by_user[event.user_id]

            # Remove from action index
            if event.action_type in self.by_action and user_ts_key in self.by_action[event.action_type]:
                del self.by_action[event.action_type][user_ts_key]
                if len(self.by_action[event.action_type]) == 0:
                    del self.by_action[event.action_type]

            # Remove from outcome index
            if event.outcome in self.by_outcome and user_ts_key in self.by_outcome[event.outcome]:
                del self.by_outcome[event.outcome][user_ts_key]
                if len(self.by_outcome[event.outcome]) == 0:
                    del self.by_outcome[event.outcome]

            deleted_count += 1

        # Update metadata
        self.metadata['total_events'] -= deleted_count
        self.metadata['last_cleaned'] = datetime.now(pytz.UTC)
        self._p_changed = True

        logger.info(f"Cleaned up {deleted_count} audit events older than {before_timestamp}")

        return deleted_count

    def get_stats(self):
        """
        Get container statistics.

        Returns:
            dict: Container statistics
        """
        return {
            'total_events': self.metadata['total_events'],
            'created': self.metadata['created'].isoformat(),
            'last_cleaned': self.metadata['last_cleaned'].isoformat() if self.metadata['last_cleaned'] else None,
            'retention_days': self.metadata['retention_days'],
            'users_count': len(self.by_user),
            'action_types_count': len(self.by_action),
        }


def get_audit_container(portal):
    """
    Retrieve or create the audit log container from portal annotations.

    Args:
        portal: Plone portal object

    Returns:
        AuditLogContainer: The audit log container

    This function is idempotent - it's safe to call multiple times.
    The container is created on first access and persists across restarts.
    """
    annotations = IAnnotations(portal)

    if AUDIT_LOG_KEY not in annotations:
        logger.info("Creating new audit log container")
        annotations[AUDIT_LOG_KEY] = AuditLogContainer()

    return annotations[AUDIT_LOG_KEY]


def log_audit_event(portal, user_id, action_type, outcome, ip_address, user_agent, metadata=None):
    """
    Log an audit event to persistent storage.

    This is the main entry point for logging audit events. It handles
    container creation, event validation, and error handling.

    Args:
        portal: Plone portal object
        user_id (str): User ID or 'anonymous'
        action_type (str): One of AUDIT_ACTION_TYPES
        outcome (str): 'success' or 'failure'
        ip_address (str): Source IP address
        user_agent (str): Browser User-Agent
        metadata (dict): Optional action-specific data

    Returns:
        str: Event ID if successful, None if failed

    Error Handling:
    - Validation errors are logged but don't raise exceptions
    - Storage errors are logged and return None (fail open)
    - This ensures audit failures don't break authentication flows
    """
    try:
        # Get or create container
        container = get_audit_container(portal)

        # Create event (validates action_type and outcome)
        event = AuditEvent(
            user_id=user_id,
            action_type=action_type,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )

        # Add to container
        event_id = container.add_event(event)

        # Commit happens automatically at transaction boundary
        return event_id

    except ValueError as e:
        # Validation error
        logger.error(f"Invalid audit event: {e}")
        return None
    except Exception as e:
        # Storage error - fail open (don't break authentication)
        logger.error(f"Failed to log audit event: {e}", exc_info=True)
        return None
