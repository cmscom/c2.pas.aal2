# -*- coding: utf-8 -*-
"""Tests for PAS plugin integration."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


class MockSession:
    """Mock session storage."""

    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]


class MockRequest:
    """Mock Zope request."""

    def __init__(self):
        self.form = {}
        self.other = {}
        self.SESSION = MockSession()
        self.response = Mock()

    def get(self, key, default=None):
        return self.other.get(key, default)

    def set(self, key, value):
        self.other[key] = value


class MockPortal:
    """Mock Plone portal."""

    def __init__(self):
        self.portal_url = 'https://example.com'

    def absolute_url(self):
        return self.portal_url

    def getProperty(self, name, default=None):
        if name == 'title':
            return 'Test Site'
        return default


class MockACLUsers:
    """Mock acl_users."""

    def __init__(self):
        self.users = {}

    def getUserById(self, user_id):
        return self.users.get(user_id)

    def getUserIds(self):
        return list(self.users.keys())


@pytest.fixture
def mock_plugin():
    """Create a mock AAL2Plugin for testing."""
    from c2.pas.aal2.plugin import AAL2Plugin

    plugin = AAL2Plugin('test_plugin')
    plugin.id = 'test_plugin'

    # Mock dependencies
    plugin._get_portal = Mock(return_value=MockPortal())
    plugin._get_acl_users = Mock(return_value=MockACLUsers())

    return plugin


@pytest.fixture
def mock_request():
    """Create a mock request."""
    return MockRequest()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = Mock()
    user.getId = Mock(return_value='testuser')
    user.getProperty = Mock(side_effect=lambda k, d=None: {
        'fullname': 'Test User',
        'email': 'test@example.com'
    }.get(k, d))
    user._annotations = {}
    user._p_changed = False
    return user


class TestPASPluginInterfaces:
    """Test PAS plugin interface implementations."""

    def test_plugin_has_required_interfaces(self, mock_plugin):
        """Test that plugin implements required PAS interfaces."""
        from Products.PluggableAuthService.interfaces.plugins import (
            IExtractionPlugin,
            IAuthenticationPlugin
        )

        # Note: In real implementation, these would be registered via ZCML
        # Here we just verify the methods exist
        assert hasattr(mock_plugin, 'extractCredentials')
        assert hasattr(mock_plugin, 'authenticateCredentials')

    def test_extract_credentials_no_passkey(self, mock_plugin, mock_request):
        """Test credential extraction when no passkey attempt."""
        result = mock_plugin.extractCredentials(mock_request)

        # Should return None when no passkey markers
        assert result is None

    def test_extract_credentials_with_passkey(self, mock_plugin, mock_request):
        """Test credential extraction with passkey markers."""
        # Set passkey markers
        mock_request.set('__passkey_auth_attempt', True)
        mock_request.set('__passkey_username', 'testuser')
        mock_request.set('__passkey_credential', {'id': 'test_cred'})

        result = mock_plugin.extractCredentials(mock_request)

        assert result is not None
        assert result['login'] == 'testuser'
        assert 'passkey_credential' in result

    def test_authenticate_credentials_with_passkey(self, mock_plugin):
        """Test authentication with passkey credentials."""
        credentials = {
            'login': 'testuser',
            'password': '',
            'passkey_credential': {'id': 'test_cred'}
        }

        result = mock_plugin.authenticateCredentials(credentials)

        # Should return user tuple
        assert result is not None
        assert result[0] == 'testuser'
        assert result[1] == 'testuser'

    def test_authenticate_credentials_without_passkey(self, mock_plugin):
        """Test authentication without passkey credentials."""
        credentials = {
            'login': 'testuser',
            'password': 'secret'
        }

        result = mock_plugin.authenticateCredentials(credentials)

        # Should return None (not our responsibility)
        assert result is None


class TestRegistrationFlow:
    """Test passkey registration flow."""

    @patch('c2.pas.aal2.plugin.ISession')
    @patch('c2.pas.aal2.utils.webauthn.create_registration_options')
    @patch('c2.pas.aal2.utils.audit.log_registration_start')
    def test_generate_registration_options(
        self,
        mock_log,
        mock_create_options,
        mock_session,
        mock_plugin,
        mock_request,
        mock_user
    ):
        """Test generating registration options."""
        # Mock session
        session_data = {}
        mock_session.return_value.get.return_value = session_data

        # Mock webauthn options
        mock_options = Mock()
        mock_options.challenge = b'test_challenge'
        mock_create_options.return_value = mock_options

        # Call method
        result = mock_plugin.generateRegistrationOptions(
            request=mock_request,
            user=mock_user,
            device_name='Test Device',
            authenticator_attachment='platform'
        )

        # Verify
        assert result is not None
        assert mock_create_options.called
        assert mock_log.called

    @patch('c2.pas.aal2.plugin.ISession')
    @patch('c2.pas.aal2.utils.webauthn.verify_registration')
    @patch('c2.pas.aal2.credential.add_passkey')
    @patch('c2.pas.aal2.utils.audit.log_registration_success')
    def test_verify_registration_response(
        self,
        mock_log,
        mock_add,
        mock_verify,
        mock_session,
        mock_plugin,
        mock_request,
        mock_user
    ):
        """Test verifying registration response."""
        # Mock session with challenge
        session_data = {'registration_challenge': b'test_challenge'}
        mock_session.return_value.get.return_value = session_data

        # Mock verification result
        mock_verification = Mock()
        mock_verification.credential_id = b'test_cred_id'
        mock_verification.credential_public_key = b'test_public_key'
        mock_verification.sign_count = 0
        mock_verification.aaguid = b'test_aaguid'
        mock_verify.return_value = mock_verification

        # Mock add_passkey
        mock_add.return_value = 'test_cred_id_b64'

        # Call method
        credential_response = {
            'id': 'test_cred',
            'rawId': 'test_cred',
            'response': {
                'clientDataJSON': 'test_client_data',
                'attestationObject': 'test_attestation'
            },
            'type': 'public-key'
        }

        result = mock_plugin.verifyRegistrationResponse(
            request=mock_request,
            user=mock_user,
            credential_response=credential_response
        )

        # Verify
        assert result['success'] is True
        assert result['credential_id'] == 'test_cred_id_b64'
        assert mock_verify.called
        assert mock_add.called
        assert mock_log.called


class TestAuthenticationFlow:
    """Test passkey authentication flow."""

    @patch('c2.pas.aal2.plugin.ISession')
    @patch('c2.pas.aal2.utils.webauthn.create_authentication_options')
    @patch('c2.pas.aal2.credential.get_user_passkeys')
    @patch('c2.pas.aal2.utils.audit.log_authentication_start')
    def test_generate_authentication_options(
        self,
        mock_log,
        mock_get_passkeys,
        mock_create_options,
        mock_session,
        mock_plugin,
        mock_request
    ):
        """Test generating authentication options."""
        # Mock session
        session_data = {}
        mock_session.return_value.get.return_value = session_data

        # Mock passkeys
        mock_get_passkeys.return_value = {
            'cred1': {
                'credential_id': b'cred1',
                'transports': ['internal']
            }
        }

        # Mock webauthn options
        mock_options = Mock()
        mock_options.challenge = b'test_challenge'
        mock_create_options.return_value = mock_options

        # Call method
        result = mock_plugin.generateAuthenticationOptions(
            request=mock_request,
            username='testuser'
        )

        # Verify
        assert result is not None
        assert mock_create_options.called
        assert mock_log.called

    @patch('c2.pas.aal2.plugin.ISession')
    @patch('c2.pas.aal2.utils.webauthn.verify_authentication')
    @patch('c2.pas.aal2.credential.get_passkey')
    @patch('c2.pas.aal2.credential.update_passkey_last_used')
    @patch('c2.pas.aal2.utils.audit.log_authentication_success')
    def test_verify_authentication_response(
        self,
        mock_log,
        mock_update,
        mock_get_passkey,
        mock_verify,
        mock_session,
        mock_plugin,
        mock_request,
        mock_user
    ):
        """Test verifying authentication response."""
        # Setup
        acl_users = mock_plugin._get_acl_users()
        acl_users.users['testuser'] = mock_user

        # Mock session with challenge
        session_data = {'authentication_challenge': b'test_challenge'}
        mock_session.return_value.get.return_value = session_data

        # Mock passkey
        mock_get_passkey.return_value = {
            'credential_id': b'test_cred',
            'public_key': b'test_pub_key',
            'sign_count': 0
        }

        # Mock verification
        mock_verification = Mock()
        mock_verification.new_sign_count = 1
        mock_verify.return_value = mock_verification

        # Call method
        credential_response = {
            'id': 'test_cred',
            'rawId': 'test_cred',
            'response': {
                'clientDataJSON': 'test_client_data',
                'authenticatorData': 'test_auth_data',
                'signature': 'test_signature'
            }
        }

        result = mock_plugin.verifyAuthenticationResponse(
            request=mock_request,
            credential_response=credential_response,
            username='testuser'
        )

        # Verify
        assert result['success'] is True
        assert result['user_id'] == 'testuser'
        assert mock_verify.called
        assert mock_update.called
        assert mock_log.called


class TestErrorHandling:
    """Test error handling in plugin."""

    @patch('c2.pas.aal2.plugin.ISession')
    def test_verify_registration_no_challenge(
        self,
        mock_session,
        mock_plugin,
        mock_request,
        mock_user
    ):
        """Test registration verification fails without challenge."""
        # Mock session with no challenge
        mock_session.return_value.get.return_value = {}

        credential_response = {'id': 'test'}

        with pytest.raises(ValueError, match="No registration challenge"):
            mock_plugin.verifyRegistrationResponse(
                request=mock_request,
                user=mock_user,
                credential_response=credential_response
            )

    @patch('c2.pas.aal2.plugin.ISession')
    def test_verify_authentication_no_challenge(
        self,
        mock_session,
        mock_plugin,
        mock_request
    ):
        """Test authentication verification fails without challenge."""
        # Mock session with no challenge
        mock_session.return_value.get.return_value = {}

        credential_response = {'id': 'test'}

        with pytest.raises(ValueError, match="No authentication challenge"):
            mock_plugin.verifyAuthenticationResponse(
                request=mock_request,
                credential_response=credential_response
            )

    @patch('c2.pas.aal2.plugin.ISession')
    @patch('c2.pas.aal2.utils.webauthn.verify_authentication')
    @patch('c2.pas.aal2.credential.get_passkey')
    def test_verify_authentication_user_not_found(
        self,
        mock_get_passkey,
        mock_verify,
        mock_session,
        mock_plugin,
        mock_request
    ):
        """Test authentication fails when user not found."""
        # Mock session
        mock_session.return_value.get.return_value = {
            'authentication_challenge': b'test'
        }

        # Mock no passkey found
        mock_get_passkey.return_value = None

        credential_response = {
            'id': 'test_cred',
            'rawId': 'test_cred',
        }

        with pytest.raises(ValueError, match="No user found"):
            mock_plugin.verifyAuthenticationResponse(
                request=mock_request,
                credential_response=credential_response,
                username='nonexistent'
            )
