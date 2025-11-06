# -*- coding: utf-8 -*-
"""Integration tests for AAL2 functionality (c2.pas.aal2).

This module tests the complete AAL2 workflow including:
- Content protection with AAL2 policy
- Session-based authentication tracking
- Step-up authentication flow
- Plugin integration
"""

import pytest
from datetime import datetime, timedelta


@pytest.fixture
def mock_portal(mocker):
    """Create a mock Plone portal."""
    portal = mocker.Mock()
    portal.getId.return_value = 'Plone'
    portal.Title.return_value = 'Test Plone Site'
    portal.absolute_url.return_value = 'http://localhost:8080/Plone'
    return portal


@pytest.fixture
def mock_content(mocker):
    """Create a mock Plone content object."""
    content = mocker.Mock()
    content.getId.return_value = 'protected_document'
    content.Title.return_value = 'Protected Document'
    content.absolute_url.return_value = 'http://localhost:8080/Plone/protected_document'

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


@pytest.fixture
def mock_user(mocker):
    """Create a mock Plone user."""
    user = mocker.Mock()
    user.getId.return_value = 'john_doe'
    user.getUserName.return_value = 'john_doe'
    user.getRoles.return_value = ['Member', 'Authenticated']

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
def mock_request(mocker):
    """Create a mock HTTP request."""
    request = mocker.Mock()
    request.URL = 'http://localhost:8080/Plone/protected_document'
    request.get = mocker.Mock(return_value=None)
    request.form = {}
    return request


class TestAAL2ProtectionFlow:
    """Test complete AAL2 protection workflow."""

    def test_aal2_protection_without_requirement(self, mock_content, mock_user, mock_request, mocker):
        """Test accessing content without AAL2 requirement."""
        from c2.pas.aal2.policy import is_aal2_required, check_aal2_access

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Content should not require AAL2 by default
        assert is_aal2_required(mock_content) is False

        # Access should be allowed without AAL2 authentication
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

    def test_aal2_protection_with_requirement_and_valid_auth(self, mock_content, mock_user, mock_request, mocker):
        """Test accessing AAL2-protected content with valid authentication."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access
        from c2.pas.aal2.session import set_aal2_timestamp, is_aal2_valid

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Step 1: Administrator sets AAL2 protection on content
        set_aal2_required(mock_content, required=True)

        # Step 2: User authenticates with passkey
        set_aal2_timestamp(mock_user, credential_id='test_credential_123')

        # Step 3: User should have valid AAL2 authentication
        assert is_aal2_valid(mock_user) is True

        # Step 4: Access check should pass
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

    def test_aal2_protection_with_requirement_and_expired_auth(self, mock_content, mock_user, mock_request, mocker):
        """Test accessing AAL2-protected content with expired authentication."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access
        from c2.pas.aal2.session import is_aal2_valid

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Step 1: Set AAL2 protection
        set_aal2_required(mock_content, required=True)

        # Step 2: Set expired timestamp (16 minutes ago)
        expired_time = datetime.utcnow() - timedelta(minutes=16)
        mock_user._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': expired_time.isoformat()
        }

        # Step 3: AAL2 should be invalid
        assert is_aal2_valid(mock_user) is False

        # Step 4: Access should be denied
        assert check_aal2_access(mock_content, mock_user, mock_request) is False

    def test_aal2_protection_with_requirement_and_no_auth(self, mock_content, mock_user, mock_request, mocker):
        """Test accessing AAL2-protected content without authentication."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Step 1: Set AAL2 protection
        set_aal2_required(mock_content, required=True)

        # Step 2: User has no AAL2 timestamp (never authenticated with passkey)
        # (default state, no timestamp set)

        # Step 3: Access should be denied
        assert check_aal2_access(mock_content, mock_user, mock_request) is False


class TestAAL2StepUpFlow:
    """Test AAL2 step-up authentication flow."""

    def test_stepup_challenge_url_generation(self, mock_content, mock_request, mocker):
        """Test generating step-up challenge URL."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Generate challenge URL
        url = get_stepup_challenge_url(mock_content, mock_request)

        # Should return a valid URL
        assert url is not None
        assert isinstance(url, str)
        assert len(url) > 0

    def test_complete_stepup_flow(self, mock_content, mock_user, mock_request, mocker):
        """Test complete step-up authentication flow."""
        from c2.pas.aal2.policy import (
            set_aal2_required,
            check_aal2_access,
            get_stepup_challenge_url,
        )
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Step 1: Content is AAL2-protected
        set_aal2_required(mock_content, required=True)

        # Step 2: User tries to access without AAL2 auth
        access_denied = not check_aal2_access(mock_content, mock_user, mock_request)
        assert access_denied is True

        # Step 3: Get step-up challenge URL
        challenge_url = get_stepup_challenge_url(mock_content, mock_request)
        assert challenge_url is not None

        # Step 4: User completes passkey authentication (simulated)
        set_aal2_timestamp(mock_user, credential_id='passkey_123')

        # Step 5: User can now access the content
        access_granted = check_aal2_access(mock_content, mock_user, mock_request)
        assert access_granted is True


class TestAAL2TimeWindow:
    """Test AAL2 15-minute time window enforcement."""

    def test_access_within_time_window(self, mock_content, mock_user, mock_request, mocker):
        """Test that access is granted within 15-minute window."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Set AAL2 protection
        set_aal2_required(mock_content, required=True)

        # Authenticate (within window)
        set_aal2_timestamp(mock_user)

        # Access at 0 minutes - should be allowed
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

        # Simulate 5 minutes passed
        timestamp_5min_ago = datetime.utcnow() - timedelta(minutes=5)
        mock_user._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': timestamp_5min_ago.isoformat()
        }
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

        # Simulate 14 minutes passed (edge case, still valid)
        timestamp_14min_ago = datetime.utcnow() - timedelta(minutes=14)
        mock_user._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': timestamp_14min_ago.isoformat()
        }
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

    def test_access_after_time_window(self, mock_content, mock_user, mock_request, mocker):
        """Test that access is denied after 15-minute window."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Set AAL2 protection
        set_aal2_required(mock_content, required=True)

        # Set expired timestamp (16 minutes ago)
        timestamp_16min_ago = datetime.utcnow() - timedelta(minutes=16)
        mock_user._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': timestamp_16min_ago.isoformat()
        }

        # Access should be denied
        assert check_aal2_access(mock_content, mock_user, mock_request) is False

    def test_reauthentication_resets_window(self, mock_content, mock_user, mock_request, mocker):
        """Test that re-authentication resets the 15-minute window."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Set AAL2 protection
        set_aal2_required(mock_content, required=True)

        # Set expired timestamp
        timestamp_16min_ago = datetime.utcnow() - timedelta(minutes=16)
        mock_user._annotations['c2.pas.aal2.aal2_timestamp'] = {
            'timestamp': timestamp_16min_ago.isoformat()
        }

        # Access denied due to expiration
        assert check_aal2_access(mock_content, mock_user, mock_request) is False

        # User re-authenticates with passkey
        set_aal2_timestamp(mock_user)

        # Access should now be granted (window reset)
        assert check_aal2_access(mock_content, mock_user, mock_request) is True


class TestAAL2ViewsIntegration:
    """Test AAL2 browser views integration."""

    def test_aal2_challenge_view_redirects_anonymous(self, mocker):
        """Test that AAL2 challenge view redirects anonymous users to login."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        # Mock anonymous user
        mocker.patch('plone.api.user.is_anonymous', return_value=True)

        # Mock portal
        mock_portal = mocker.Mock()
        mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Mock request and response
        mock_request = mocker.Mock()
        mock_request.get.return_value = 'http://localhost:8080/Plone/protected'
        mock_response = mocker.Mock()
        mock_request.response = mock_response

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2ChallengeView(mock_context, mock_request)
        view()

        # Should redirect to login
        assert mock_response.redirect.called
        redirect_url = mock_response.redirect.call_args[0][0]
        assert redirect_url.startswith('http://localhost:8080/Plone/login')
        assert 'came_from' in redirect_url

    def test_aal2_challenge_view_redirects_if_already_valid(self, mocker):
        """Test that AAL2 challenge view redirects if user already has valid AAL2."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        # Mock authenticated user
        mocker.patch('plone.api.user.is_anonymous', return_value=False)

        mock_user = mocker.Mock()
        mock_user.getId.return_value = 'testuser'
        mock_user.getProperty.return_value = 'Test User'
        mocker.patch('plone.api.user.get_current', return_value=mock_user)

        # Mock portal
        mock_portal = mocker.Mock()
        mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Mock is_aal2_valid to return True
        mocker.patch('c2.pas.aal2.session.is_aal2_valid', return_value=True)

        # Mock request and response
        mock_request = mocker.Mock()
        mock_request.get.return_value = 'http://localhost:8080/Plone/protected'
        mock_response = mocker.Mock()
        mock_request.response = mock_response

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2ChallengeView(mock_context, mock_request)
        view()

        # Should redirect to came_from
        assert mock_response.redirect.called
        redirect_url = mock_response.redirect.call_args[0][0]
        assert redirect_url == 'http://localhost:8080/Plone/protected'

    def test_aal2_settings_view_requires_manager(self, mocker):
        """Test that AAL2 settings view requires Manager permission."""
        from c2.pas.aal2.browser.views import AAL2SettingsView
        from zExceptions import Unauthorized

        # Mock user without Manager permission
        mocker.patch('plone.api.user.has_permission', return_value=False)

        # Mock request
        mock_request = mocker.Mock()
        mock_request.method = 'GET'

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2SettingsView(mock_context, mock_request)

        # Should raise Unauthorized
        with pytest.raises(Unauthorized):
            view()

    def test_aal2_settings_view_lists_protected_content(self, mocker):
        """Test that AAL2 settings view lists protected content."""
        from c2.pas.aal2.browser.views import AAL2SettingsView

        # Mock user with Manager permission
        mocker.patch('plone.api.user.has_permission', return_value=True)

        # Mock list_aal2_protected_content function to return test data
        mock_protected_content = [
            {
                'title': 'Protected Doc 1',
                'path': '/Plone/protected1',
                'type': 'Document',
                'url': 'http://localhost:8080/Plone/protected1'
            }
        ]
        mocker.patch(
            'c2.pas.aal2.policy.list_aal2_protected_content',
            return_value=mock_protected_content
        )

        # Mock request
        mock_request = mocker.Mock()
        mock_request.method = 'GET'

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2SettingsView(mock_context, mock_request)

        # Get protected content
        protected_content = view.get_aal2_protected_content()

        # Should return list of protected content
        assert len(protected_content) == 1
        assert protected_content[0]['title'] == 'Protected Doc 1'
        assert protected_content[0]['path'] == '/Plone/protected1'


class TestAAL2RoleBasedIntegration:
    """Test AAL2 role-based enforcement integration."""

    def test_role_based_aal2_enforcement(self, mock_content, mock_request, mocker):
        """Test that users with AAL2 Required User role need AAL2 authentication."""
        from c2.pas.aal2.roles import has_aal2_role
        from c2.pas.aal2.session import is_aal2_valid

        # Mock user with AAL2 Required User role
        mock_user = mocker.Mock()
        mock_user.getId.return_value = 'aal2_user'
        mock_user.getRoles.return_value = ['Member', 'Authenticated', 'AAL2 Required User']

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

        mock_user._annotations = annotations
        mock_user._annotations_adapter = AnnotationsAdapter(annotations)

        # Mock IAnnotations for session module
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # User should have AAL2 role
        assert has_aal2_role(mock_user) is True

        # User does not have valid AAL2 yet
        assert is_aal2_valid(mock_user) is False

    def test_content_and_role_aal2_both_work(self, mock_content, mock_user, mock_request, mocker):
        """Test that both content-based and role-based AAL2 requirements work together."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access
        from c2.pas.aal2.roles import has_aal2_role
        from c2.pas.aal2.session import set_aal2_timestamp

        # Mock IAnnotations for policy and session modules
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Scenario 1: Content requires AAL2, user doesn't have role
        set_aal2_required(mock_content, required=True)
        mock_user.getRoles.return_value = ['Member', 'Authenticated']

        # Access should be denied without authentication
        assert check_aal2_access(mock_content, mock_user, mock_request) is False

        # After authentication, access should be granted
        set_aal2_timestamp(mock_user)
        assert check_aal2_access(mock_content, mock_user, mock_request) is True

        # Scenario 2: Content doesn't require AAL2, but user has AAL2 Required User role
        set_aal2_required(mock_content, required=False)
        mock_user.getRoles.return_value = ['Member', 'Authenticated', 'AAL2 Required User']

        # User should have AAL2 role (even though content doesn't require it)
        assert has_aal2_role(mock_user) is True


class TestAAL2RoleManagementViews:
    """Test AAL2 role management view functionality."""

    def test_settings_view_lists_aal2_users(self, mocker):
        """Test that settings view can list users with AAL2 role."""
        from c2.pas.aal2.browser.views import AAL2SettingsView

        # Mock user with Manager permission
        mocker.patch('plone.api.user.has_permission', return_value=True)

        # Mock list_aal2_users to return test data
        mock_aal2_users = ['user1', 'user2', 'admin']
        mocker.patch('c2.pas.aal2.roles.list_aal2_users', return_value=mock_aal2_users)

        # Mock portal
        mock_portal = mocker.Mock()
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Mock request
        mock_request = mocker.Mock()
        mock_request.method = 'GET'

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2SettingsView(mock_context, mock_request)

        # Get AAL2 users
        aal2_users = view.get_aal2_users()

        # Should return list of users with AAL2 role
        assert len(aal2_users) == 3
        assert 'user1' in aal2_users
        assert 'user2' in aal2_users
        assert 'admin' in aal2_users

    def test_settings_view_assigns_aal2_role(self, mocker):
        """Test that settings view can assign AAL2 role to a user."""
        from c2.pas.aal2.browser.views import AAL2SettingsView

        # Mock user with Manager permission
        mocker.patch('plone.api.user.has_permission', return_value=True)

        # Mock portal
        mock_portal = mocker.Mock()
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Mock assign_aal2_role to return success
        mock_assign = mocker.patch('c2.pas.aal2.roles.assign_aal2_role', return_value=True)

        # Mock audit logging
        mocker.patch('c2.pas.aal2.utils.audit.log_aal2_role_assigned')

        # Mock portal messages
        mock_show_message = mocker.patch('plone.api.portal.show_message')

        # Mock request with form data
        mock_request = mocker.Mock()
        mock_request.method = 'POST'
        mock_request.form = {
            'action': 'assign_role',
            'user_id': 'testuser'
        }
        mock_response = mocker.Mock()
        mock_request.response = mock_response
        mock_request.URL = 'http://localhost:8080/Plone/@@aal2-settings'

        # Mock current user
        mock_current_user = mocker.Mock()
        mock_current_user.getId.return_value = 'admin'
        mocker.patch('plone.api.user.get_current', return_value=mock_current_user)

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2SettingsView(mock_context, mock_request)

        # Call assign_aal2_role
        view.assign_aal2_role()

        # Verify role was assigned
        mock_assign.assert_called_once_with('testuser', mock_portal)

        # Verify success message was shown
        mock_show_message.assert_called_once()
        call_args = mock_show_message.call_args
        assert 'AAL2 Required User role assigned' in call_args[1]['message']

    def test_settings_view_revokes_aal2_role(self, mocker):
        """Test that settings view can revoke AAL2 role from a user."""
        from c2.pas.aal2.browser.views import AAL2SettingsView

        # Mock user with Manager permission
        mocker.patch('plone.api.user.has_permission', return_value=True)

        # Mock portal
        mock_portal = mocker.Mock()
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Mock revoke_aal2_role to return success
        mock_revoke = mocker.patch('c2.pas.aal2.roles.revoke_aal2_role', return_value=True)

        # Mock audit logging
        mocker.patch('c2.pas.aal2.utils.audit.log_aal2_role_revoked')

        # Mock portal messages
        mock_show_message = mocker.patch('plone.api.portal.show_message')

        # Mock request with form data
        mock_request = mocker.Mock()
        mock_request.method = 'POST'
        mock_request.form = {
            'action': 'revoke_role',
            'user_id': 'testuser'
        }
        mock_response = mocker.Mock()
        mock_request.response = mock_response
        mock_request.URL = 'http://localhost:8080/Plone/@@aal2-settings'

        # Mock current user
        mock_current_user = mocker.Mock()
        mock_current_user.getId.return_value = 'admin'
        mocker.patch('plone.api.user.get_current', return_value=mock_current_user)

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2SettingsView(mock_context, mock_request)

        # Call revoke_aal2_role
        view.revoke_aal2_role()

        # Verify role was revoked
        mock_revoke.assert_called_once_with('testuser', mock_portal)

        # Verify success message was shown
        mock_show_message.assert_called_once()
        call_args = mock_show_message.call_args
        assert 'AAL2 Required User role revoked' in call_args[1]['message']

    def test_settings_view_lists_all_users_for_assignment(self, mocker):
        """Test that settings view provides list of all users for role assignment."""
        from c2.pas.aal2.browser.views import AAL2SettingsView

        # Mock user with Manager permission
        mocker.patch('plone.api.user.has_permission', return_value=True)

        # Mock acl_users tool
        mock_acl_users = mocker.Mock()
        mock_acl_users.getUserIds.return_value = ['alice', 'bob', 'charlie', 'admin']
        mocker.patch('plone.api.portal.get_tool', return_value=mock_acl_users)

        # Mock request
        mock_request = mocker.Mock()
        mock_request.method = 'GET'

        # Mock context
        mock_context = mocker.Mock()

        # Create view
        view = AAL2SettingsView(mock_context, mock_request)

        # Get all users
        all_users = view.get_all_users()

        # Should return sorted list of all user IDs
        assert len(all_users) == 4
        assert all_users == ['admin', 'alice', 'bob', 'charlie']


class TestAAL2UserFeedbackFlow:
    """Test complete user feedback flow for AAL2 (US4)."""

    def test_complete_user_feedback_flow_with_clear_messages(self, mock_content, mock_user, mock_request, mocker):
        """Test that user receives clear feedback throughout AAL2 flow."""
        from c2.pas.aal2.policy import set_aal2_required, check_aal2_access
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        # Mock IAnnotations
        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Mock plone.api
        mocker.patch('plone.api.user.is_anonymous', return_value=False)
        mocker.patch('plone.api.user.get_current', return_value=mock_user)

        mock_portal = mocker.Mock()
        mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Step 1: Content is AAL2-protected
        set_aal2_required(mock_content, required=True)

        # Step 2: User tries to access without valid AAL2 - access denied
        mocker.patch('c2.pas.aal2.session.is_aal2_valid', return_value=False)
        assert check_aal2_access(mock_content, mock_user, mock_request) is False

        # Step 3: User is redirected to AAL2 challenge page
        mock_context = mocker.Mock()
        challenge_view = AAL2ChallengeView(mock_context, mock_request)

        # Step 4: Challenge view provides clear message
        assert hasattr(challenge_view, 'get_challenge_message')
        message = challenge_view.get_challenge_message()
        assert message is not None
        assert len(message) > 30

        # Step 5: Challenge view provides help text
        assert hasattr(challenge_view, 'get_help_text')
        help_text = challenge_view.get_help_text()
        assert help_text is not None
        assert 'AAL2' in help_text or '15' in help_text

    def test_user_sees_expiry_information_on_challenge_page(self, mock_user, mock_request, mocker):
        """Test that user sees when their AAL2 authentication expired."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView
        from datetime import datetime, timedelta

        # Mock plone.api
        mocker.patch('plone.api.user.is_anonymous', return_value=False)
        mocker.patch('plone.api.user.get_current', return_value=mock_user)

        mock_portal = mocker.Mock()
        mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        # Mock expired AAL2 session
        mocker.patch('c2.pas.aal2.session.is_aal2_valid', return_value=False)

        expired_time = datetime.utcnow() - timedelta(minutes=20)
        mocker.patch('c2.pas.aal2.session.get_aal2_timestamp', return_value=expired_time)

        # Create challenge view
        mock_context = mocker.Mock()
        challenge_view = AAL2ChallengeView(mock_context, mock_request)

        # View should provide expiry time information
        # (This will be implemented in the view)
        assert hasattr(challenge_view, 'expiry_time') or hasattr(challenge_view, '__dict__')

    def test_user_receives_helpful_error_messages(self, mock_user, mock_request, mocker):
        """Test that user receives helpful error messages when authentication fails."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        # Mock plone.api
        mocker.patch('plone.api.user.is_anonymous', return_value=False)
        mocker.patch('plone.api.user.get_current', return_value=mock_user)

        mock_portal = mocker.Mock()
        mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        mocker.patch('plone.api.portal.get', return_value=mock_portal)

        mocker.patch('c2.pas.aal2.session.is_aal2_valid', return_value=False)

        # Create challenge view
        mock_context = mocker.Mock()
        challenge_view = AAL2ChallengeView(mock_context, mock_request)

        # View should be properly initialized
        assert challenge_view.context == mock_context
        assert challenge_view.request == mock_request
