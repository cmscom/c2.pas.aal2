# -*- coding: utf-8 -*-
"""Tests for AAL2 session management (c2.pas.aal2.session).

This module tests the AAL2 timestamp management functions including:
- Setting AAL2 authentication timestamps
- Getting AAL2 authentication timestamps
- Validating AAL2 session validity (15-minute window)
- Getting AAL2 expiry times
- Clearing AAL2 timestamps
"""

import pytest
from datetime import datetime, timedelta
from zope.annotation.interfaces import IAnnotations


@pytest.fixture
def mock_user(mocker):
    """Create a mock Plone user object with annotation support."""
    user = mocker.Mock()
    user.getId.return_value = 'test_user'

    # Mock annotations storage
    annotations = {}

    def get_annotation(key, default=None):
        return annotations.get(key, default)

    def set_annotation(key, value):
        annotations[key] = value

    def has_key(key):
        return key in annotations

    def del_annotation(key):
        if key in annotations:
            del annotations[key]

    # Create IAnnotations adapter mock
    annotations_adapter = mocker.Mock()
    annotations_adapter.get = mocker.Mock(side_effect=get_annotation)
    annotations_adapter.__setitem__ = mocker.Mock(side_effect=set_annotation)
    annotations_adapter.__getitem__ = mocker.Mock(side_effect=lambda k: annotations[k])
    annotations_adapter.__contains__ = mocker.Mock(side_effect=has_key)
    annotations_adapter.__delitem__ = mocker.Mock(side_effect=del_annotation)

    # Mock IAnnotations call to return the adapter
    mocker.patch('c2.pas.aal2.session.IAnnotations', return_value=annotations_adapter)

    return user


class TestSetAAL2Timestamp:
    """Test set_aal2_timestamp() function."""

    def test_set_aal2_timestamp_basic(self, mock_user, mocker):
        """Test setting AAL2 timestamp for a user."""
        from c2.pas.aal2.session import set_aal2_timestamp, get_aal2_timestamp

        # Set timestamp
        set_aal2_timestamp(mock_user)

        # Verify timestamp was set by reading it back
        timestamp = get_aal2_timestamp(mock_user)
        assert timestamp is not None
        assert isinstance(timestamp, datetime)

    def test_set_aal2_timestamp_with_credential_id(self, mock_user):
        """Test setting AAL2 timestamp with credential ID."""
        from c2.pas.aal2.session import set_aal2_timestamp, get_aal2_timestamp

        credential_id = 'AQIDBAUGBwgBAgMEBQYHCAECAwQFBgcI'
        set_aal2_timestamp(mock_user, credential_id=credential_id)

        # Should still set timestamp (credential_id stored for audit only)
        timestamp = get_aal2_timestamp(mock_user)
        assert timestamp is not None


class TestGetAAL2Timestamp:
    """Test get_aal2_timestamp() function."""

    def test_get_aal2_timestamp_exists(self, mock_user, mocker):
        """Test getting AAL2 timestamp when it exists."""
        from c2.pas.aal2.session import get_aal2_timestamp, set_aal2_timestamp

        # Set a known timestamp
        now = datetime.utcnow()
        set_aal2_timestamp(mock_user)

        # Get timestamp
        result = get_aal2_timestamp(mock_user)

        # Verify result
        assert result is not None
        assert isinstance(result, datetime)
        assert abs((result - now).total_seconds()) < 2  # Within 2 seconds

    def test_get_aal2_timestamp_not_exists(self, mock_user):
        """Test getting AAL2 timestamp when it doesn't exist."""
        from c2.pas.aal2.session import get_aal2_timestamp

        # Get timestamp (should not exist initially)
        result = get_aal2_timestamp(mock_user)

        # Should return None
        assert result is None


class TestIsAAL2Valid:
    """Test is_aal2_valid() function."""

    def test_is_aal2_valid_fresh_timestamp(self, mock_user, mocker):
        """Test AAL2 validity for fresh timestamp (within 15 minutes)."""
        from c2.pas.aal2.session import is_aal2_valid, get_aal2_timestamp

        # Mock fresh timestamp (5 minutes ago)
        fresh_timestamp = datetime.utcnow() - timedelta(minutes=5)
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=fresh_timestamp)

        # Check validity
        result = is_aal2_valid(mock_user)

        # Should be valid
        assert result is True

    def test_is_aal2_valid_expired_timestamp(self, mock_user, mocker):
        """Test AAL2 validity for expired timestamp (over 15 minutes)."""
        from c2.pas.aal2.session import is_aal2_valid

        # Mock expired timestamp (16 minutes ago)
        expired_timestamp = datetime.utcnow() - timedelta(minutes=16)
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=expired_timestamp)

        # Check validity
        result = is_aal2_valid(mock_user)

        # Should be invalid
        assert result is False

    def test_is_aal2_valid_no_timestamp(self, mock_user, mocker):
        """Test AAL2 validity when no timestamp exists."""
        from c2.pas.aal2.session import is_aal2_valid

        # Mock no timestamp
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=None)

        # Check validity
        result = is_aal2_valid(mock_user)

        # Should be invalid
        assert result is False

    def test_is_aal2_valid_future_timestamp(self, mock_user, mocker):
        """Test AAL2 validity for future timestamp (should be invalid)."""
        from c2.pas.aal2.session import is_aal2_valid

        # Mock future timestamp (5 minutes in future)
        future_timestamp = datetime.utcnow() + timedelta(minutes=5)
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=future_timestamp)

        # Check validity
        result = is_aal2_valid(mock_user)

        # Should be invalid (reject future timestamps)
        assert result is False

    def test_is_aal2_valid_edge_case_14_minutes(self, mock_user, mocker):
        """Test AAL2 validity at edge case (14 minutes, should be valid)."""
        from c2.pas.aal2.session import is_aal2_valid

        # Mock timestamp exactly 14 minutes ago
        edge_timestamp = datetime.utcnow() - timedelta(minutes=14)
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=edge_timestamp)

        # Check validity
        result = is_aal2_valid(mock_user)

        # Should still be valid
        assert result is True


class TestGetAAL2Expiry:
    """Test get_aal2_expiry() function."""

    def test_get_aal2_expiry_with_timestamp(self, mock_user, mocker):
        """Test getting AAL2 expiry time when timestamp exists."""
        from c2.pas.aal2.session import get_aal2_expiry, AAL2_TIMEOUT_SECONDS

        # Mock timestamp
        timestamp = datetime.utcnow() - timedelta(minutes=5)
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=timestamp)

        # Get expiry
        result = get_aal2_expiry(mock_user)

        # Should be timestamp + 15 minutes
        assert result is not None
        expected_expiry = timestamp + timedelta(seconds=AAL2_TIMEOUT_SECONDS)
        assert abs((result - expected_expiry).total_seconds()) < 1

    def test_get_aal2_expiry_no_timestamp(self, mock_user, mocker):
        """Test getting AAL2 expiry time when no timestamp exists."""
        from c2.pas.aal2.session import get_aal2_expiry

        # Mock no timestamp
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=None)

        # Get expiry
        result = get_aal2_expiry(mock_user)

        # Should return None
        assert result is None


class TestClearAAL2Timestamp:
    """Test clear_aal2_timestamp() function."""

    def test_clear_aal2_timestamp(self, mock_user, mocker):
        """Test clearing AAL2 timestamp."""
        from c2.pas.aal2.session import clear_aal2_timestamp, set_aal2_timestamp, get_aal2_timestamp

        # First set a timestamp
        set_aal2_timestamp(mock_user)
        assert get_aal2_timestamp(mock_user) is not None

        # Clear timestamp
        clear_aal2_timestamp(mock_user)

        # Verify annotation was removed
        assert get_aal2_timestamp(mock_user) is None


class TestSessionIntegration:
    """Integration tests for session management."""

    def test_full_session_lifecycle(self, mock_user, mocker):
        """Test complete AAL2 session lifecycle."""
        from c2.pas.aal2.session import (
            set_aal2_timestamp,
            get_aal2_timestamp,
            is_aal2_valid,
            clear_aal2_timestamp,
        )

        # Initial state: no timestamp
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=None)
        assert is_aal2_valid(mock_user) is False

        # Set timestamp
        set_aal2_timestamp(mock_user)

        # Mock fresh timestamp
        fresh_timestamp = datetime.utcnow()
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=fresh_timestamp)
        assert is_aal2_valid(mock_user) is True

        # Clear timestamp
        clear_aal2_timestamp(mock_user)

        # Should be invalid again
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=None)
        assert is_aal2_valid(mock_user) is False
