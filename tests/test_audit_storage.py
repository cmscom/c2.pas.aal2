# -*- coding: utf-8 -*-
"""Tests for audit log storage (Feature 005: US2)."""

import pytest
from datetime import datetime, timedelta
import pytz
from unittest.mock import Mock, MagicMock

from c2.pas.aal2.storage.audit import (
    AuditEvent,
    AuditLogContainer,
    get_audit_container,
    log_audit_event,
    AUDIT_ACTION_TYPES
)


class TestAuditEvent:
    """Tests for AuditEvent class."""

    def test_audit_event_creation(self):
        """Test creating a valid audit event."""
        event = AuditEvent(
            user_id='testuser',
            action_type='authentication_success',
            outcome='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            metadata={'credential_id': 'cred123'}
        )

        assert event.user_id == 'testuser'
        assert event.action_type == 'authentication_success'
        assert event.outcome == 'success'
        assert event.ip_address == '192.168.1.1'
        assert event.user_agent == 'Mozilla/5.0'
        assert event.metadata['credential_id'] == 'cred123'
        assert event.event_id is not None
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == pytz.UTC

    def test_audit_event_invalid_action_type(self):
        """Test that invalid action type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid action_type"):
            AuditEvent(
                user_id='testuser',
                action_type='invalid_action',
                outcome='success',
                ip_address='192.168.1.1',
                user_agent='Mozilla/5.0'
            )

    def test_audit_event_invalid_outcome(self):
        """Test that invalid outcome raises ValueError."""
        with pytest.raises(ValueError, match="Invalid outcome"):
            AuditEvent(
                user_id='testuser',
                action_type='authentication_success',
                outcome='maybe',  # Invalid
                ip_address='192.168.1.1',
                user_agent='Mozilla/5.0'
            )

    def test_audit_event_to_dict(self):
        """Test converting event to dictionary."""
        event = AuditEvent(
            user_id='testuser',
            action_type='registration_success',
            outcome='success',
            ip_address='10.0.0.1',
            user_agent='Chrome',
            metadata={'device_name': 'My Device'}
        )

        event_dict = event.to_dict()

        assert event_dict['user_id'] == 'testuser'
        assert event_dict['action_type'] == 'registration_success'
        assert event_dict['outcome'] == 'success'
        assert isinstance(event_dict['timestamp'], str)  # ISO format
        assert event_dict['metadata']['device_name'] == 'My Device'


class TestAuditLogContainer:
    """Tests for AuditLogContainer class."""

    @pytest.fixture
    def container(self):
        """Create a fresh audit log container for each test."""
        return AuditLogContainer()

    @pytest.fixture
    def sample_events(self, container):
        """Create sample events for testing."""
        events = []
        base_time = datetime.now(pytz.UTC) - timedelta(days=10)

        for i in range(50):
            event = AuditEvent(
                user_id=f'user{i % 5}',  # 5 different users
                action_type=AUDIT_ACTION_TYPES[i % len(AUDIT_ACTION_TYPES)],
                outcome='success' if i % 3 != 0 else 'failure',
                ip_address=f'192.168.1.{i}',
                user_agent='TestAgent',
                metadata={'test_id': i}
            )
            # Set timestamp to past dates
            event.timestamp = base_time + timedelta(hours=i)
            events.append(event)
            container.add_event(event)

        return events

    def test_container_initialization(self, container):
        """Test that container initializes with correct structure."""
        assert hasattr(container, 'events')
        assert hasattr(container, 'by_user')
        assert hasattr(container, 'by_action')
        assert hasattr(container, 'by_outcome')
        assert hasattr(container, 'metadata')
        assert container.metadata['total_events'] == 0
        assert container.metadata['retention_days'] == 90

    def test_add_event(self, container):
        """Test adding an event to the container."""
        event = AuditEvent(
            user_id='testuser',
            action_type='authentication_success',
            outcome='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla'
        )

        event_id = container.add_event(event)

        assert event_id == event.event_id
        assert container.metadata['total_events'] == 1
        assert len(container.events) == 1
        assert 'testuser' in container.by_user
        assert 'authentication_success' in container.by_action
        assert 'success' in container.by_outcome

    def test_query_by_timestamp(self, container, sample_events):
        """Test querying events by timestamp range."""
        # Query middle 20 events
        start_time = sample_events[15].timestamp
        end_time = sample_events[35].timestamp

        results = container.query_by_timestamp(start_time, end_time)

        assert len(results) == 21  # Inclusive range
        assert all(start_time <= e.timestamp <= end_time for e in results)

    def test_query_by_user(self, container, sample_events):
        """Test querying events for a specific user."""
        results = container.query_by_user('user0')

        assert len(results) == 10  # 50 events / 5 users
        assert all(e.user_id == 'user0' for e in results)

    def test_query_by_action(self, container, sample_events):
        """Test querying events by action type."""
        results = container.query_by_action('authentication_success')

        assert len(results) > 0
        assert all(e.action_type == 'authentication_success' for e in results)

    def test_query_by_outcome(self, container, sample_events):
        """Test querying events by outcome."""
        success_results = container.query_by_outcome('success')
        failure_results = container.query_by_outcome('failure')

        assert len(success_results) > 0
        assert len(failure_results) > 0
        assert all(e.outcome == 'success' for e in success_results)
        assert all(e.outcome == 'failure' for e in failure_results)
        assert len(success_results) + len(failure_results) == 50

    def test_cleanup_old_events(self, container, sample_events):
        """Test cleaning up old events."""
        # Clean up events older than 5 days from the end
        cutoff = sample_events[-1].timestamp - timedelta(days=5)
        initial_count = container.metadata['total_events']

        deleted_count = container.cleanup_old_events(cutoff)

        assert deleted_count > 0
        assert container.metadata['total_events'] == initial_count - deleted_count
        assert container.metadata['last_cleaned'] is not None

        # Verify old events are gone
        remaining_events = container.query_by_timestamp()
        assert all(e.timestamp >= cutoff for e in remaining_events)

    def test_get_stats(self, container, sample_events):
        """Test getting container statistics."""
        stats = container.get_stats()

        assert stats['total_events'] == 50
        assert stats['users_count'] == 5
        assert stats['retention_days'] == 90
        assert 'created' in stats


class TestAuditLoggingIntegration:
    """Integration tests for audit logging functions."""

    @pytest.fixture
    def mock_portal(self):
        """Create a mock portal object with annotations."""
        portal = Mock()
        # Mock annotations as a dict
        portal._annotations = {}

        # Mock IAnnotations to return the dict
        from zope.annotation.interfaces import IAnnotations

        def mock_annotations(obj):
            return obj._annotations

        # This would normally be done via adapter, but for testing we mock it
        import c2.pas.aal2.storage.audit as audit_module
        original_IAnnotations = audit_module.IAnnotations

        def patched_IAnnotations(obj):
            if hasattr(obj, '_annotations'):
                return obj._annotations
            return original_IAnnotations(obj)

        audit_module.IAnnotations = patched_IAnnotations

        yield portal

        # Restore original
        audit_module.IAnnotations = original_IAnnotations

    def test_get_audit_container_creates_container(self, mock_portal):
        """Test that get_audit_container creates container on first call."""
        container = get_audit_container(mock_portal)

        assert container is not None
        assert isinstance(container, AuditLogContainer)
        assert container.metadata['total_events'] == 0

    def test_get_audit_container_returns_existing(self, mock_portal):
        """Test that get_audit_container returns same container on subsequent calls."""
        container1 = get_audit_container(mock_portal)
        container2 = get_audit_container(mock_portal)

        assert container1 is container2

    def test_log_audit_event(self, mock_portal):
        """Test logging an audit event via helper function."""
        event_id = log_audit_event(
            portal=mock_portal,
            user_id='testuser',
            action_type='authentication_success',
            outcome='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla',
            metadata={'credential_id': 'cred123'}
        )

        assert event_id is not None

        # Verify event was stored
        container = get_audit_container(mock_portal)
        assert container.metadata['total_events'] == 1

    def test_log_audit_event_fail_open_on_error(self, mock_portal):
        """Test that audit logging fails open (returns None on error)."""
        # Pass invalid action_type
        event_id = log_audit_event(
            portal=mock_portal,
            user_id='testuser',
            action_type='invalid_action_type',
            outcome='success',
            ip_address='192.168.1.1',
            user_agent='Mozilla'
        )

        # Should return None and not raise exception
        assert event_id is None


class TestAuditActionTypes:
    """Test that all action types are valid."""

    def test_all_action_types_valid(self):
        """Test creating events with all valid action types."""
        for action_type in AUDIT_ACTION_TYPES:
            event = AuditEvent(
                user_id='testuser',
                action_type=action_type,
                outcome='success',
                ip_address='192.168.1.1',
                user_agent='Test'
            )
            assert event.action_type == action_type

    def test_action_types_count(self):
        """Test that we have the expected number of action types."""
        # From data-model.md: 14 action types
        assert len(AUDIT_ACTION_TYPES) == 14
