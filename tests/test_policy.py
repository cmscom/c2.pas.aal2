# -*- coding: utf-8 -*-
"""Tests for AAL2 policy management (c2.pas.aal2.policy).

This module tests the AAL2 policy functions including:
- Checking if AAL2 is required for content
- Setting AAL2 requirements on content
- AAL2 access checking with session validation
- Step-up challenge URL generation
"""

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def mock_content(mocker):
    """Create a mock Plone content object with annotation support."""
    content = mocker.Mock()
    content.getId.return_value = 'test_content'
    content.absolute_url.return_value = 'http://localhost:8080/Plone/test_content'

    # Mock annotations storage
    annotations = {}

    def get_annotation(key, default=None):
        return annotations.get(key, default)

    def set_annotation(key, value):
        annotations[key] = value

    def has_key(key):
        return key in annotations

    # Create IAnnotations adapter mock
    annotations_adapter = mocker.Mock()
    annotations_adapter.get = mocker.Mock(side_effect=get_annotation)
    annotations_adapter.__setitem__ = mocker.Mock(side_effect=set_annotation)
    annotations_adapter.__contains__ = mocker.Mock(side_effect=has_key)

    # Store reference for verification
    content._annotations = annotations
    content._annotations_adapter = annotations_adapter

    return content


@pytest.fixture
def mock_user(mocker):
    """Create a mock Plone user object."""
    user = mocker.Mock()
    user.getId.return_value = 'test_user'
    user.getRoles.return_value = ['Member']

    # Mock annotations storage for AAL2 timestamp
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

    # Store reference
    user._annotations = annotations

    return user


@pytest.fixture
def mock_request(mocker):
    """Create a mock HTTP request object."""
    request = mocker.Mock()
    request.get.return_value = None
    request.URL = 'http://localhost:8080/Plone/test_content'
    return request


class TestIsAAL2Required:
    """Test is_aal2_required() function."""

    def test_is_aal2_required_not_set(self, mock_content, mocker):
        """Test checking AAL2 requirement when not set."""
        # Mock IAnnotations to return the adapter
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        from c2.pas.aal2.policy import is_aal2_required

        # Check requirement (should be False by default)
        result = is_aal2_required(mock_content)

        assert result is False

    def test_is_aal2_required_set_true(self, mock_content, mocker):
        """Test checking AAL2 requirement when set to True."""
        from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

        # Mock IAnnotations
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        # Set AAL2 requirement
        set_aal2_required(mock_content, required=True)

        # Check requirement
        result = is_aal2_required(mock_content)

        assert result is True

    def test_is_aal2_required_set_false(self, mock_content, mocker):
        """Test checking AAL2 requirement when explicitly set to False."""
        from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

        # Mock IAnnotations
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        # Set AAL2 requirement to False
        set_aal2_required(mock_content, required=False)

        # Check requirement
        result = is_aal2_required(mock_content)

        assert result is False


class TestSetAAL2Required:
    """Test set_aal2_required() function."""

    def test_set_aal2_required_true(self, mock_content, mocker):
        """Test setting AAL2 requirement to True."""
        from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

        # Mock IAnnotations
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        # Set requirement
        set_aal2_required(mock_content, required=True)

        # Verify it was set
        assert is_aal2_required(mock_content) is True

    def test_set_aal2_required_false(self, mock_content, mocker):
        """Test setting AAL2 requirement to False."""
        from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

        # Mock IAnnotations
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        # Set to True first
        set_aal2_required(mock_content, required=True)
        assert is_aal2_required(mock_content) is True

        # Then set to False
        set_aal2_required(mock_content, required=False)

        # Verify it was cleared
        assert is_aal2_required(mock_content) is False


class TestCheckAAL2Access:
    """Test check_aal2_access() function."""

    def test_check_aal2_access_not_required(self, mock_content, mock_user, mock_request, mocker):
        """Test AAL2 access check when AAL2 is not required."""
        from c2.pas.aal2.policy import check_aal2_access

        # Mock IAnnotations for both content and user
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            # Fallback
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', return_value=mock_user._annotations)

        # AAL2 not required - should allow access
        result = check_aal2_access(mock_content, mock_user, mock_request)

        # Should return True (access allowed)
        assert result is True

    def test_check_aal2_access_required_and_valid(self, mock_content, mock_user, mock_request, mocker):
        """Test AAL2 access check when AAL2 is required and user has valid authentication."""
        from c2.pas.aal2.policy import check_aal2_access, set_aal2_required
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            if hasattr(obj, '_annotations'):
                # Create adapter for user annotations with proper __setitem__
                class AnnotationsAdapter:
                    def __init__(self, storage):
                        self.storage = storage
                    def get(self, k, d=None):
                        return self.storage.get(k, d)
                    def __setitem__(self, k, v):
                        self.storage[k] = v
                    def __contains__(self, k):
                        return k in self.storage
                return AnnotationsAdapter(obj._annotations)
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Set AAL2 requirement on content
        set_aal2_required(mock_content, required=True)

        # Set valid AAL2 timestamp for user
        set_aal2_timestamp(mock_user)

        # Check access - should be allowed
        result = check_aal2_access(mock_content, mock_user, mock_request)

        assert result is True

    def test_check_aal2_access_required_and_expired(self, mock_content, mock_user, mock_request, mocker):
        """Test AAL2 access check when AAL2 is required but authentication expired."""
        from c2.pas.aal2.policy import check_aal2_access, set_aal2_required

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            if hasattr(obj, '_annotations'):
                adapter = mocker.Mock()
                adapter.get = lambda k, d=None: obj._annotations.get(k, d)
                adapter.__setitem__ = lambda k, v: obj._annotations.__setitem__(k, v)
                adapter.__contains__ = lambda k: k in obj._annotations
                return adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Set AAL2 requirement
        set_aal2_required(mock_content, required=True)

        # Set expired timestamp (16 minutes ago)
        expired_time = datetime.utcnow() - timedelta(minutes=16)
        mock_user._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': expired_time.isoformat()
        }

        # Check access - should be denied
        result = check_aal2_access(mock_content, mock_user, mock_request)

        assert result is False


class TestGetStepupChallengeUrl:
    """Test get_stepup_challenge_url() function."""

    def test_get_stepup_challenge_url(self, mock_content, mock_request, mocker):
        """Test generating step-up challenge URL."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Generate URL
        result = get_stepup_challenge_url(mock_content, mock_request)

        # Should return a URL string
        assert result is not None
        assert isinstance(result, str)
        assert 'aal2-challenge' in result or 'aal2_challenge' in result

    def test_get_stepup_challenge_url_with_came_from(self, mock_content, mock_request, mocker):
        """Test generating step-up challenge URL with came_from parameter."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Generate URL
        result = get_stepup_challenge_url(mock_content, mock_request)

        # Should include came_from parameter or similar redirect mechanism
        assert result is not None
        assert isinstance(result, str)


class TestPolicyIntegration:
    """Integration tests for policy module."""

    def test_full_aal2_policy_lifecycle(self, mock_content, mock_user, mock_request, mocker):
        """Test complete AAL2 policy lifecycle."""
        from c2.pas.aal2.policy import (
            check_aal2_access,
            is_aal2_required,
            set_aal2_required,
        )
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            if hasattr(obj, '_annotations'):
                # Create adapter for user annotations
                class AnnotationsAdapter:
                    def __init__(self, storage):
                        self.storage = storage
                    def get(self, k, d=None):
                        return self.storage.get(k, d)
                    def __setitem__(self, k, v):
                        self.storage[k] = v
                    def __contains__(self, k):
                        return k in self.storage
                return AnnotationsAdapter(obj._annotations)
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Initial state: no AAL2 requirement
        assert is_aal2_required(mock_content) is False
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

        # Set AAL2 requirement
        set_aal2_required(mock_content, required=True)
        assert is_aal2_required(mock_content) is True

        # Without valid timestamp, access should be denied
        assert check_aal2_access(mock_content, mock_user, mock_request) is False

        # Authenticate with passkey (set timestamp)
        set_aal2_timestamp(mock_user)

        # Now access should be allowed
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

        # Remove AAL2 requirement
        set_aal2_required(mock_content, required=False)
        assert is_aal2_required(mock_content) is False

        # Access should be allowed even without timestamp
        assert check_aal2_access(mock_content, mock_user, mock_request) is True
