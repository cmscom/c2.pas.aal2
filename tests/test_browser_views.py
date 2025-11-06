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
