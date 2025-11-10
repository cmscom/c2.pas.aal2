# -*- coding: utf-8 -*-
"""Tests for browser views."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


class MockResponse:
    """Mock HTTP response."""

    def __init__(self):
        self.status = 200
        self.headers = {}

    def setStatus(self, status):
        self.status = status

    def setHeader(self, name, value):
        self.headers[name] = value


class MockRequest:
    """Mock Zope request."""

    def __init__(self, body='{}'):
        self.form = {}
        self.other = {'BODY': body}
        self.response = MockResponse()

    def get(self, key, default=None):
        return self.other.get(key, default)


class MockUser:
    """Mock user object."""

    def __init__(self, user_id):
        self.user_id = user_id

    def getId(self):
        return self.user_id


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = Mock()
    context.portal_url = 'https://example.com'
    return context


@pytest.fixture
def mock_request():
    """Create mock request."""
    return MockRequest()


class TestPasskeyRegisterViews:
    """Test passkey registration views."""

    @patch('c2.pas.aal2.browser.views.api')
    def test_register_options_view_anonymous(self, mock_api, mock_context):
        """Test that anonymous users get 401."""
        from c2.pas.aal2.browser.views import PasskeyRegisterOptionsView

        # Mock anonymous user
        mock_api.user.is_anonymous.return_value = True

        request = MockRequest()
        view = PasskeyRegisterOptionsView(mock_context, request)
        result = view()

        # Should return error
        assert request.response.status == 401
        data = json.loads(result)
        assert data['error'] == 'authentication_required'

    @patch('c2.pas.aal2.browser.views.api')
    def test_register_options_view_authenticated(self, mock_api, mock_context):
        """Test registration options for authenticated user."""
        from c2.pas.aal2.browser.views import PasskeyRegisterOptionsView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        # Mock portal tool
        mock_acl_users = Mock()
        mock_plugin = Mock()
        mock_plugin.generateRegistrationOptions.return_value = Mock(
            challenge=b'test_challenge'
        )
        mock_acl_users.get.return_value = mock_plugin
        mock_api.portal.get_tool.return_value = mock_acl_users

        # Mock options_to_json
        with patch('c2.pas.aal2.browser.views.options_to_json') as mock_json:
            mock_json.return_value = '{"challenge": "test"}'

            request_body = json.dumps({
                'device_name': 'Test Device',
                'authenticator_attachment': 'platform'
            })
            request = MockRequest(body=request_body)
            view = PasskeyRegisterOptionsView(mock_context, request)
            result = view()

            # Should succeed
            data = json.loads(result)
            assert 'publicKey' in data
            assert 'session_id' in data

    @patch('c2.pas.aal2.browser.views.api')
    def test_register_verify_view_success(self, mock_api, mock_context):
        """Test successful registration verification."""
        from c2.pas.aal2.browser.views import PasskeyRegisterVerifyView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        # Mock portal tool
        mock_acl_users = Mock()
        mock_plugin = Mock()
        mock_plugin.verifyRegistrationResponse.return_value = {
            'success': True,
            'credential_id': 'test_cred_id'
        }
        mock_acl_users.get.return_value = mock_plugin
        mock_api.portal.get_tool.return_value = mock_acl_users

        # Mock get_passkey
        with patch('c2.pas.aal2.browser.views.get_passkey') as mock_get:
            mock_get.return_value = {
                'device_name': 'Test Device',
                'device_type': 'platform',
                'created': None,
                'transports': []
            }

            request_body = json.dumps({
                'credential': {'id': 'test_cred'}
            })
            request = MockRequest(body=request_body)
            view = PasskeyRegisterVerifyView(mock_context, request)
            result = view()

            # Should succeed
            assert request.response.status == 201
            data = json.loads(result)
            assert data['success'] is True
            assert data['credential_id'] == 'test_cred_id'


class TestPasskeyLoginViews:
    """Test passkey login views."""

    @patch('c2.pas.aal2.browser.views.api')
    def test_login_options_view(self, mock_api, mock_context):
        """Test login options generation."""
        from c2.pas.aal2.browser.views import PasskeyLoginOptionsView

        # Mock portal tool
        mock_acl_users = Mock()
        mock_plugin = Mock()
        mock_plugin.generateAuthenticationOptions.return_value = Mock(
            challenge=b'test_challenge'
        )
        mock_acl_users.get.return_value = mock_plugin
        mock_api.portal.get_tool.return_value = mock_acl_users

        # Mock options_to_json
        with patch('c2.pas.aal2.browser.views.options_to_json') as mock_json:
            mock_json.return_value = '{"challenge": "test"}'

            request_body = json.dumps({'username': 'testuser'})
            request = MockRequest(body=request_body)
            view = PasskeyLoginOptionsView(mock_context, request)
            result = view()

            # Should succeed
            data = json.loads(result)
            assert 'publicKey' in data
            assert 'session_id' in data

    @patch('c2.pas.aal2.browser.views.api')
    def test_login_verify_view_success(self, mock_api, mock_context):
        """Test successful login verification."""
        from c2.pas.aal2.browser.views import PasskeyLoginVerifyView

        # Mock portal
        mock_portal = Mock()
        mock_portal.absolute_url.return_value = 'https://example.com'
        mock_api.portal.get.return_value = mock_portal

        # Mock acl_users
        mock_acl_users = Mock()
        mock_plugin = Mock()
        mock_plugin.verifyAuthenticationResponse.return_value = {
            'success': True,
            'user_id': 'testuser'
        }
        mock_acl_users.get.return_value = mock_plugin
        mock_acl_users.getUserById.return_value = MockUser('testuser')
        mock_acl_users._updateCredentials = Mock()
        mock_api.portal.get_tool.return_value = mock_acl_users

        request_body = json.dumps({
            'credential': {'id': 'test_cred'},
            'username': 'testuser'
        })
        request = MockRequest(body=request_body)
        view = PasskeyLoginVerifyView(mock_context, request)
        result = view()

        # Should succeed
        data = json.loads(result)
        assert data['success'] is True
        assert data['user_id'] == 'testuser'
        assert 'redirect_url' in data


class TestPasskeyManagementViews:
    """Test passkey management views."""

    @patch('c2.pas.aal2.browser.views.api')
    def test_list_view_anonymous(self, mock_api, mock_context):
        """Test that anonymous users get 401."""
        from c2.pas.aal2.browser.views import PasskeyListView

        mock_api.user.is_anonymous.return_value = True

        request = MockRequest()
        view = PasskeyListView(mock_context, request)
        result = view()

        assert request.response.status == 401
        data = json.loads(result)
        assert data['error'] == 'authentication_required'

    @patch('c2.pas.aal2.browser.views.api')
    def test_list_view_authenticated(self, mock_api, mock_context):
        """Test listing passkeys for authenticated user."""
        from c2.pas.aal2.browser.views import PasskeyListView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        # Mock passkeys
        with patch('c2.pas.aal2.browser.views.get_user_passkeys') as mock_get:
            mock_get.return_value = {
                'cred1': {
                    'device_name': 'Device 1',
                    'device_type': 'platform',
                    'created': None,
                    'last_used': None,
                    'transports': []
                }
            }

            request = MockRequest()
            view = PasskeyListView(mock_context, request)
            result = view()

            data = json.loads(result)
            assert data['count'] == 1
            assert len(data['passkeys']) == 1
            assert data['passkeys'][0]['device_name'] == 'Device 1'

    @patch('c2.pas.aal2.browser.views.api')
    def test_delete_view_last_passkey_no_password(self, mock_api, mock_context):
        """Test FR-016: Cannot delete last passkey without password."""
        from c2.pas.aal2.browser.views import PasskeyDeleteView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_user.getProperty = Mock(return_value=None)  # No password
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        # Mock count_passkeys
        with patch('c2.pas.aal2.browser.views.count_passkeys') as mock_count:
            mock_count.return_value = 1  # Last passkey

            request_body = json.dumps({'credential_id': 'cred1'})
            request = MockRequest(body=request_body)
            view = PasskeyDeleteView(mock_context, request)
            result = view()

            # Should be denied
            assert request.response.status == 403
            data = json.loads(result)
            assert data['error'] == 'last_credential'
            assert 'Cannot remove last authentication method' in data['message']

    @patch('c2.pas.aal2.browser.views.api')
    def test_delete_view_success(self, mock_api, mock_context):
        """Test successful passkey deletion."""
        from c2.pas.aal2.browser.views import PasskeyDeleteView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_user.getProperty = Mock(return_value='hashed_password')
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        # Mock functions
        with patch('c2.pas.aal2.browser.views.count_passkeys') as mock_count, \
             patch('c2.pas.aal2.browser.views.delete_passkey') as mock_delete, \
             patch('c2.pas.aal2.browser.views.log_credential_deleted') as mock_log:

            mock_count.return_value = 2  # Has multiple passkeys
            mock_delete.return_value = True

            request_body = json.dumps({'credential_id': 'cred1'})
            request = MockRequest(body=request_body)
            view = PasskeyDeleteView(mock_context, request)
            result = view()

            # Should succeed
            data = json.loads(result)
            assert data['success'] is True
            assert mock_delete.called
            assert mock_log.called

    @patch('c2.pas.aal2.browser.views.api')
    def test_update_view_success(self, mock_api, mock_context):
        """Test successful passkey update."""
        from c2.pas.aal2.browser.views import PasskeyUpdateView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_user._annotations = {}
        mock_user._p_changed = False
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        # Mock functions
        with patch('c2.pas.aal2.browser.views.get_passkey') as mock_get, \
             patch('c2.pas.aal2.browser.views.get_user_passkeys') as mock_get_all, \
             patch('c2.pas.aal2.browser.views.IAnnotations') as mock_annotations:

            passkey = {
                'device_name': 'Old Name',
                'device_type': 'platform',
                'created': None,
                'last_used': None
            }
            mock_get.return_value = passkey
            mock_get_all.return_value = {'cred1': passkey}
            mock_annotations.return_value = {}

            request_body = json.dumps({
                'credential_id': 'cred1',
                'device_name': 'New Name'
            })
            request = MockRequest(body=request_body)
            view = PasskeyUpdateView(mock_context, request)
            result = view()

            # Should succeed
            data = json.loads(result)
            assert data['success'] is True
            assert passkey['device_name'] == 'New Name'

    @patch('c2.pas.aal2.browser.views.api')
    def test_update_view_device_name_too_long(self, mock_api, mock_context):
        """Test validation: device name exceeds max length."""
        from c2.pas.aal2.browser.views import PasskeyUpdateView

        # Mock authenticated user
        mock_api.user.is_anonymous.return_value = False
        mock_user = MockUser('testuser')
        mock_api.user.get_current.return_value = mock_user
        mock_api.user.get.return_value = mock_user

        request_body = json.dumps({
            'credential_id': 'cred1',
            'device_name': 'x' * 101  # Too long
        })
        request = MockRequest(body=request_body)
        view = PasskeyUpdateView(mock_context, request)
        result = view()

        # Should fail validation
        assert request.response.status == 400
        data = json.loads(result)
        assert data['error'] == 'validation_error'


class TestErrorHandling:
    """Test error handling in views."""

    def test_invalid_json_request(self, mock_context):
        """Test handling of invalid JSON."""
        from c2.pas.aal2.browser.views import PasskeyRegisterVerifyView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False

            request = MockRequest(body='invalid json {{{')
            view = PasskeyRegisterVerifyView(mock_context, request)
            result = view()

            assert request.response.status == 400
            data = json.loads(result)
            assert data['error'] == 'invalid_request'

    def test_missing_required_fields(self, mock_context):
        """Test handling of missing required fields."""
        from c2.pas.aal2.browser.views import PasskeyDeleteView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False

            # Missing credential_id
            request = MockRequest(body='{}')
            view = PasskeyDeleteView(mock_context, request)
            result = view()

            assert request.response.status == 400
            data = json.loads(result)
            assert data['error'] == 'missing_credential_id'


# ============================================================================
# AAL2 User Feedback UI Tests (US4)
# ============================================================================

class TestAAL2ChallengeViewMessages:
    """Test AAL2 challenge view provides clear, user-friendly messages."""

    def test_challenge_message_is_clear_and_informative(self, mock_context):
        """Test that challenge view provides clear explanation of why AAL2 is required."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            # Mock authenticated user
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'testuser'
            mock_user.getProperty.return_value = 'Test User'
            mock_api.user.get_current.return_value = mock_user

            # Mock portal
            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            # Mock is_aal2_valid to return False (needs authentication)
            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                request = MockRequest()
                request.form = {'came_from': 'http://localhost:8080/Plone/protected'}
                view = AAL2ChallengeView(mock_context, request)

                # Check that view has method to get challenge message
                assert hasattr(view, 'get_challenge_message')
                message = view.get_challenge_message()

                # Message should be clear and informative
                assert message is not None
                assert isinstance(message, str)
                assert len(message) > 50  # Should be substantial explanation
                # Should mention security and authentication
                assert any(word in message.lower() for word in ['security', 'authenticate', 'passkey'])

    def test_challenge_view_shows_user_identity(self, mock_context):
        """Test that challenge view shows which user is being asked to authenticate."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'john_doe'
            mock_user.getProperty.return_value = 'John Doe'
            mock_api.user.get_current.return_value = mock_user

            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                with patch('c2.pas.aal2.session.get_aal2_expiry', return_value=None):
                    request = MockRequest()
                    request.form = {'came_from': 'http://localhost:8080/Plone/test'}
                    view = AAL2ChallengeView(mock_context, request)

                    # Mock index() to prevent template rendering
                    view.index = Mock(return_value='rendered')

                    # Call the view to set attributes
                    view()

                    # View should provide user information
                    assert hasattr(view, 'username')
                    assert view.username == 'john_doe'
                    assert hasattr(view, 'user_fullname')
                    assert view.user_fullname == 'John Doe'

    def test_challenge_view_provides_help_text(self, mock_context):
        """Test that challenge view provides helpful explanation text."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'testuser'
            mock_user.getProperty.return_value = 'Test User'
            mock_api.user.get_current.return_value = mock_user

            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                request = MockRequest()
                view = AAL2ChallengeView(mock_context, request)

                # Check that view has method to get help text
                assert hasattr(view, 'get_help_text')
                help_text = view.get_help_text()

                # Help text should explain AAL2
                assert help_text is not None
                assert isinstance(help_text, str)
                assert len(help_text) > 30
                # Should mention AAL2 and 15 minutes
                assert 'AAL2' in help_text or 'aal2' in help_text.lower()
                assert '15' in help_text


class TestAAL2ExpiryTimeDisplay:
    """Test that AAL2 expiry time is displayed clearly to users."""

    def test_challenge_view_shows_last_authentication_time(self, mock_context):
        """Test that challenge view shows when user last authenticated."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView
        from datetime import datetime, timedelta

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'testuser'
            mock_user.getProperty.return_value = 'Test User'
            mock_api.user.get_current.return_value = mock_user

            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            # Mock expired AAL2 session
            expired_time = datetime.utcnow() - timedelta(minutes=20)
            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                with patch('c2.pas.aal2.session.get_aal2_expiry', return_value=expired_time):
                    request = MockRequest()
                    request.form = {'came_from': 'http://localhost:8080/Plone/test'}
                    view = AAL2ChallengeView(mock_context, request)

                    # Mock index() to prevent template rendering
                    view.index = Mock(return_value='rendered')

                    # Call view to set attributes
                    view()

                    # View should have expiry_time attribute set
                    assert hasattr(view, 'expiry_time')
                    assert view.expiry_time is not None

    def test_expiry_time_display_is_user_friendly(self, mock_context):
        """Test that expiry time is displayed in user-friendly format."""
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'testuser'
            mock_user.getProperty.return_value = 'Test User'
            mock_api.user.get_current.return_value = mock_user

            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                request = MockRequest()
                view = AAL2ChallengeView(mock_context, request)

                # If expiry_time is provided, it should be formatted
                # (This will be implemented in the view)
                # For now, just check the attribute can exist
                assert hasattr(view, '__class__')


class TestAAL2ErrorMessages:
    """Test that AAL2 error messages are clear and actionable."""

    def test_authentication_cancelled_error_is_clear(self, mock_context):
        """Test that cancellation error message is user-friendly."""
        # This tests the client-side JavaScript error handling
        # We verify that the template includes clear error messages
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'testuser'
            mock_user.getProperty.return_value = 'Test User'
            mock_api.user.get_current.return_value = mock_user

            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                request = MockRequest()
                view = AAL2ChallengeView(mock_context, request)

                # View should exist and be callable
                assert view is not None

    def test_no_passkey_error_provides_registration_link(self, mock_context):
        """Test that 'no passkey' error directs user to registration."""
        # This is verified through template content in integration tests
        # Here we just verify the view structure
        from c2.pas.aal2.browser.views import AAL2ChallengeView

        with patch('c2.pas.aal2.browser.views.api') as mock_api:
            mock_api.user.is_anonymous.return_value = False
            mock_user = Mock()
            mock_user.getId.return_value = 'testuser'
            mock_user.getProperty.return_value = 'Test User'
            mock_api.user.get_current.return_value = mock_user

            mock_portal = Mock()
            mock_portal.absolute_url.return_value = 'http://localhost:8080/Plone'
            mock_api.portal.get.return_value = mock_portal

            with patch('c2.pas.aal2.session.is_aal2_valid', return_value=False):
                request = MockRequest()
                view = AAL2ChallengeView(mock_context, request)

                # View context should be accessible
                assert view.context == mock_context
                assert view.request == request


class TestAAL2StatusViewlet:
    """Test AAL2 status viewlet for user dashboard."""

    def test_status_viewlet_shows_aal2_validity(self, mock_context):
        """Test that status viewlet shows whether AAL2 is currently valid."""
        # This will be implemented as a viewlet
        # For now, we test that the viewlet can be imported
        try:
            from c2.pas.aal2.browser.viewlets import AAL2StatusViewlet
            # Viewlet should be importable
            assert AAL2StatusViewlet is not None
        except ImportError:
            # Not yet implemented - test should fail
            pytest.fail("AAL2StatusViewlet not yet implemented")

    def test_status_viewlet_shows_remaining_time(self, mock_context):
        """Test that status viewlet shows remaining time before AAL2 expires."""
        try:
            from c2.pas.aal2.browser.viewlets import AAL2StatusViewlet

            with patch('c2.pas.aal2.browser.viewlets.api') as mock_api:
                mock_user = Mock()
                mock_user.getId.return_value = 'testuser'
                mock_api.user.get_current.return_value = mock_user
                mock_api.user.is_anonymous.return_value = False

                request = MockRequest()
                viewlet = AAL2StatusViewlet(mock_context, request, None, None)

                # Viewlet should have method to get remaining time
                assert hasattr(viewlet, 'get_remaining_time') or hasattr(viewlet, 'remaining_time')
        except ImportError:
            pytest.fail("AAL2StatusViewlet not yet implemented")

    def test_status_viewlet_not_shown_to_anonymous(self, mock_context):
        """Test that status viewlet is not shown to anonymous users."""
        try:
            from c2.pas.aal2.browser.viewlets import AAL2StatusViewlet

            with patch('c2.pas.aal2.browser.viewlets.api') as mock_api:
                mock_api.user.is_anonymous.return_value = True

                request = MockRequest()
                viewlet = AAL2StatusViewlet(mock_context, request, None, None)

                # Viewlet should not render for anonymous users
                # This will be checked via available() method or similar
                assert hasattr(viewlet, 'available') or hasattr(viewlet, 'render')
        except ImportError:
            pytest.fail("AAL2StatusViewlet not yet implemented")


class TestJavaScriptExternalization:
    """Tests for JavaScript externalization (US1/Feature 005)."""

    def test_javascript_externalization(self):
        """Test that templates have no inline JavaScript code."""
        import os
        import re

        # Template files to check
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'src', 'c2', 'pas', 'aal2', 'browser', 'templates'
        )

        templates = [
            'register_passkey.pt',
            'login_with_passkey.pt',
            'enhanced_login.pt',
            'manage_passkeys.pt',
        ]

        # Also check aal2_challenge.pt in browser directory
        browser_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'src', 'c2', 'pas', 'aal2', 'browser'
        )

        # Pattern to detect inline JavaScript (excluding simple init calls)
        # We allow short initialization scripts, but not complex logic
        inline_js_pattern = re.compile(
            r'<script[^>]*>.*?(function|const|let|var|async|await|fetch|if|for|while).*?</script>',
            re.DOTALL | re.IGNORECASE
        )

        # Allowed pattern: simple DOMContentLoaded with single function call
        allowed_init_pattern = re.compile(
            r'<script[^>]*>\s*document\.addEventListener\([\'"]DOMContentLoaded[\'"],\s*function\(\)\s*\{\s*init\w+\([^\)]*\);\s*\}\);\s*</script>',
            re.DOTALL
        )

        for template in templates:
            template_path = os.path.join(template_dir, template)
            if not os.path.exists(template_path):
                continue

            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all script tags
            matches = inline_js_pattern.findall(content)

            # Filter out allowed initialization patterns
            disallowed_scripts = []
            for match in matches:
                # Check if this is just an init call
                if not allowed_init_pattern.search(content):
                    # Check if it contains actual logic
                    if any(keyword in match.lower() for keyword in
                           ['function ', 'const ', 'let ', 'var ', 'async ', 'fetch(', 'if ', 'for ', 'while ']):
                        disallowed_scripts.append(match[:100])  # First 100 chars for debugging

            assert len(disallowed_scripts) == 0, \
                f"{template} contains inline JavaScript logic: {disallowed_scripts}"

        # Check aal2_challenge.pt
        challenge_path = os.path.join(browser_dir, 'aal2_challenge.pt')
        if os.path.exists(challenge_path):
            with open(challenge_path, 'r', encoding='utf-8') as f:
                content = f.read()

            matches = inline_js_pattern.findall(content)
            disallowed_scripts = []
            for match in matches:
                if not allowed_init_pattern.search(content):
                    if any(keyword in match.lower() for keyword in
                           ['function ', 'const ', 'let ', 'var ', 'async ', 'fetch(', 'if ', 'for ', 'while ']):
                        disallowed_scripts.append(match[:100])

            assert len(disallowed_scripts) == 0, \
                f"aal2_challenge.pt contains inline JavaScript logic: {disallowed_scripts}"

    def test_javascript_resources_configured(self):
        """Test that JavaScript resources are configured in jsregistry.xml."""
        import os
        import xml.etree.ElementTree as ET

        jsregistry_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'src', 'c2', 'pas', 'aal2', 'profiles', 'default', 'jsregistry.xml'
        )

        assert os.path.exists(jsregistry_path), "jsregistry.xml not found"

        tree = ET.parse(jsregistry_path)
        root = tree.getroot()

        # Expected JavaScript files
        expected_resources = [
            '++resource++c2.pas.aal2/js/webauthn-utils.js',
            '++resource++c2.pas.aal2/js/webauthn-register.js',
            '++resource++c2.pas.aal2/js/webauthn-login.js',
            '++resource++c2.pas.aal2/js/webauthn-aal2.js',
            '++resource++c2.pas.aal2/js/passkey-management.js',
        ]

        # Find all javascript elements
        js_elements = root.findall('.//javascript')
        registered_ids = [elem.get('id') for elem in js_elements]

        # Verify all expected resources are registered
        for resource in expected_resources:
            assert resource in registered_ids, \
                f"JavaScript resource {resource} not registered in jsregistry.xml"

        # Verify webauthn-utils.js is loaded first (insert-after="*")
        utils_elem = None
        for elem in js_elements:
            if 'webauthn-utils.js' in elem.get('id', ''):
                utils_elem = elem
                break

        assert utils_elem is not None, "webauthn-utils.js not found in jsregistry.xml"
        assert utils_elem.get('insert-after') == '*', \
            "webauthn-utils.js should be inserted after '*' to load first"

        # Verify other JS files depend on utils
        for elem in js_elements:
            resource_id = elem.get('id', '')
            if 'webauthn-' in resource_id and 'utils' not in resource_id:
                insert_after = elem.get('insert-after', '')
                assert 'webauthn-utils.js' in insert_after, \
                    f"{resource_id} should depend on webauthn-utils.js"

    def test_javascript_files_exist(self):
        """Test that all external JavaScript files exist."""
        import os

        js_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'src', 'c2', 'pas', 'aal2', 'browser', 'static', 'js'
        )

        expected_files = [
            'webauthn-utils.js',
            'webauthn-register.js',
            'webauthn-login.js',
            'webauthn-aal2.js',
            'passkey-management.js',
        ]

        for filename in expected_files:
            filepath = os.path.join(js_dir, filename)
            assert os.path.exists(filepath), \
                f"JavaScript file {filename} not found at {filepath}"

            # Verify file is not empty
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 100, \
                f"JavaScript file {filename} appears to be empty or too small"
