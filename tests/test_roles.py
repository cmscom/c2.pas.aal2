# -*- coding: utf-8 -*-
"""Tests for AAL2 role management (c2.pas.aal2 roles).

This module tests the AAL2 role-based policies including:
- Checking if user has AAL2 Required User role
- AAL2 requirement enforcement for role-based users
- Role assignment and management utilities
"""

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def mock_user_with_role(mocker):
    """Create a mock Plone user with AAL2 Required User role."""
    user = mocker.Mock()
    user.getId.return_value = 'privileged_user'
    user.getUserName.return_value = 'privileged_user'
    user.getRoles.return_value = ['Member', 'Authenticated', 'AAL2 Required User']

    # Mock annotations for AAL2 timestamp
    annotations = {}

    class AnnotationsAdapter:
        def __init__(self, storage):
            self.storage = storage
        def get(self, k, d=None):
            return self.storage.get(k, d)
        def __setitem__(self, k, v):
            self.storage[k] = v
        def __contains__(self, k):
            return k in self.storage
        def __delitem__(self, k):
            if k in self.storage:
                del self.storage[k]

    user._annotations = annotations
    user._annotations_adapter = AnnotationsAdapter(annotations)

    return user


@pytest.fixture
def mock_user_without_role(mocker):
    """Create a mock Plone user without AAL2 role."""
    user = mocker.Mock()
    user.getId.return_value = 'regular_user'
    user.getUserName.return_value = 'regular_user'
    user.getRoles.return_value = ['Member', 'Authenticated']

    # Mock annotations
    annotations = {}

    class AnnotationsAdapter:
        def __init__(self, storage):
            self.storage = storage
        def get(self, k, d=None):
            return self.storage.get(k, d)
        def __setitem__(self, k, v):
            self.storage[k] = v
        def __contains__(self, k):
            return k in self.storage
        def __delitem__(self, k):
            if k in self.storage:
                del self.storage[k]

    user._annotations = annotations
    user._annotations_adapter = AnnotationsAdapter(annotations)

    return user


@pytest.fixture
def mock_content(mocker):
    """Create a mock Plone content object."""
    content = mocker.Mock()
    content.getId.return_value = 'regular_content'
    content.absolute_url.return_value = 'http://localhost:8080/Plone/regular_content'

    # Mock annotations
    annotations = {}

    class AnnotationsAdapter:
        def __init__(self, storage):
            self.storage = storage
        def get(self, k, d=None):
            return self.storage.get(k, d)
        def __setitem__(self, k, v):
            self.storage[k] = v
        def __contains__(self, k):
            return k in self.storage

    content._annotations = annotations
    content._annotations_adapter = AnnotationsAdapter(annotations)

    return content


class TestAAL2RoleAssignment:
    """Test AAL2 role assignment and checking."""

    def test_user_has_aal2_role(self, mock_user_with_role):
        """Test checking if user has AAL2 Required User role."""
        roles = mock_user_with_role.getRoles()

        assert 'AAL2 Required User' in roles
        assert 'Member' in roles
        assert 'Authenticated' in roles

    def test_user_without_aal2_role(self, mock_user_without_role):
        """Test checking user without AAL2 role."""
        roles = mock_user_without_role.getRoles()

        assert 'AAL2 Required User' not in roles
        assert 'Member' in roles
        assert 'Authenticated' in roles


class TestAAL2RequirementWithRole:
    """Test AAL2 requirement checking with role-based policies."""

    def test_is_aal2_required_for_role_user(self, mock_content, mock_user_with_role, mocker):
        """Test that AAL2 is required for users with AAL2 role."""
        from c2.pas.aal2.policy import is_aal2_required

        # Mock IAnnotations
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        # Content itself doesn't require AAL2
        result_without_user = is_aal2_required(mock_content)
        assert result_without_user is False

        # But should be required for user with AAL2 role
        result_with_user = is_aal2_required(mock_content, mock_user_with_role)
        assert result_with_user is True

    def test_is_aal2_required_for_regular_user(self, mock_content, mock_user_without_role, mocker):
        """Test that AAL2 is not required for regular users."""
        from c2.pas.aal2.policy import is_aal2_required

        # Mock IAnnotations
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=mock_content._annotations_adapter)

        # Should not be required for regular user
        result = is_aal2_required(mock_content, mock_user_without_role)
        assert result is False


class TestAAL2AccessWithRole:
    """Test AAL2 access checking for role-based users."""

    def test_check_aal2_access_role_user_with_valid_auth(self, mock_content, mock_user_with_role, mocker):
        """Test access for AAL2 role user with valid authentication."""
        from c2.pas.aal2.policy import check_aal2_access
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Mock request
        request = mocker.Mock()

        # Set valid AAL2 timestamp
        set_aal2_timestamp(mock_user_with_role)

        # Access should be granted (has role AND valid timestamp)
        result = check_aal2_access(mock_content, mock_user_with_role, request)
        assert result is True

    def test_check_aal2_access_role_user_without_valid_auth(self, mock_content, mock_user_with_role, mocker):
        """Test access denied for AAL2 role user without valid authentication."""
        from c2.pas.aal2.policy import check_aal2_access

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Mock request
        request = mocker.Mock()

        # No AAL2 timestamp set (user has role but hasn't authenticated with passkey)
        result = check_aal2_access(mock_content, mock_user_with_role, request)

        # Access should be denied
        assert result is False

    def test_check_aal2_access_role_user_with_expired_auth(self, mock_content, mock_user_with_role, mocker):
        """Test access denied for AAL2 role user with expired authentication."""
        from c2.pas.aal2.policy import check_aal2_access

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Mock request
        request = mocker.Mock()

        # Set expired timestamp (16 minutes ago)
        expired_time = datetime.utcnow() - timedelta(minutes=16)
        mock_user_with_role._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': expired_time.isoformat()
        }

        # Access should be denied
        result = check_aal2_access(mock_content, mock_user_with_role, request)
        assert result is False

    def test_check_aal2_access_regular_user_on_regular_content(self, mock_content, mock_user_without_role, mocker):
        """Test that regular users can access regular content without AAL2."""
        from c2.pas.aal2.policy import check_aal2_access

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Mock request
        request = mocker.Mock()

        # Regular user on regular content - should be allowed
        result = check_aal2_access(mock_content, mock_user_without_role, request)
        assert result is True


class TestRoleBasedIntegration:
    """Integration tests for role-based AAL2 enforcement."""

    def test_role_overrides_content_policy(self, mock_content, mock_user_with_role, mock_user_without_role, mocker):
        """Test that AAL2 role requirement overrides content policy."""
        from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)

        # Content doesn't require AAL2
        set_aal2_required(mock_content, required=False)
        assert is_aal2_required(mock_content) is False

        # But is required for role user
        assert is_aal2_required(mock_content, mock_user_with_role) is True

        # Not required for regular user
        assert is_aal2_required(mock_content, mock_user_without_role) is False

    def test_content_policy_and_role_combined(self, mock_content, mock_user_without_role, mocker):
        """Test that content-level AAL2 policy works independently of roles."""
        from c2.pas.aal2.policy import is_aal2_required, set_aal2_required

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)

        # Set content-level AAL2 requirement
        set_aal2_required(mock_content, required=True)

        # Should be required even for regular user (content policy)
        assert is_aal2_required(mock_content, mock_user_without_role) is True

    def test_complete_role_based_workflow(self, mock_content, mock_user_with_role, mocker):
        """Test complete workflow for role-based AAL2 enforcement."""
        from c2.pas.aal2.policy import check_aal2_access
        from c2.pas.aal2.session import is_aal2_valid, set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Mock request
        request = mocker.Mock()

        # Step 1: User with AAL2 role tries to access content
        # Without authentication, access denied
        assert check_aal2_access(mock_content, mock_user_with_role, request) is False

        # Step 2: User authenticates with passkey
        set_aal2_timestamp(mock_user_with_role)
        assert is_aal2_valid(mock_user_with_role) is True

        # Step 3: Now access is granted
        assert check_aal2_access(mock_content, mock_user_with_role, request) is True

        # Step 4: After 15 minutes, access denied again
        expired_time = datetime.utcnow() - timedelta(minutes=16)
        mock_user_with_role._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': expired_time.isoformat()
        }
        assert is_aal2_valid(mock_user_with_role) is False
        assert check_aal2_access(mock_content, mock_user_with_role, request) is False
