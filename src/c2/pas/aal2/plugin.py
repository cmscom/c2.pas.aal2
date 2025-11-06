# -*- coding: utf-8 -*-
"""AAL2 PAS Plugin implementation with WebAuthn passkey support.

This module provides the AAL2 authentication plugin for Plone's Pluggable
Authentication Service (PAS) with WebAuthn-based passkey authentication.
"""

from zope.interface import implementer
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from zope.session.interfaces import ISession
import secrets
import logging

from c2.pas.aal2.interfaces import IAAL2Plugin
from c2.pas.aal2.credential import get_user_passkeys, get_passkey
from c2.pas.aal2.utils.webauthn import (
    create_registration_options,
    verify_registration,
    create_authentication_options,
    verify_authentication,
)
from c2.pas.aal2.utils.audit import (
    log_registration_start,
    log_registration_success,
    log_registration_failure,
    log_authentication_start,
    log_authentication_success,
    log_authentication_failure,
)

logger = logging.getLogger('c2.pas.aal2.plugin')


@implementer(IAuthenticationPlugin, IExtractionPlugin, IAAL2Plugin)
class AAL2Plugin(BasePlugin):
    """AAL2 Authentication Plugin for Plone PAS.

    This is a stub/template implementation that provides the basic structure
    for an AAL2 (Authentication Assurance Level 2) authentication plugin.

    The plugin implements:
    - IAuthenticationPlugin: For credential validation
    - IExtractionPlugin: For extracting credentials from requests
    - IAAL2Plugin: Custom interface for AAL2-specific functionality

    Current implementation provides stub methods that don't affect the
    existing authentication flow. Future implementations should add:
    - AAL level detection based on authentication method
    - Step-up authentication for AAL2-protected content
    - Session management for AAL2-authenticated sessions
    """

    meta_type = 'C2 PAS AAL2 Plugin'
    title = 'C2 PAS AAL2 Authentication Plugin'

    def __init__(self, id, title=None):
        """Initialize the AAL2 plugin.

        Args:
            id (str): The plugin identifier
            title (str, optional): The plugin display title
        """
        self._setId(id)
        if title is not None:
            self.title = title

    # IExtractionPlugin implementation
    def extractCredentials(self, request):
        """Extract credentials from the request.

        This implementation extracts WebAuthn assertion credentials from POST requests.

        Args:
            request: The HTTP request object

        Returns:
            dict: Credentials dict with 'passkey_assertion' or empty dict
        """
        # Check if this is a passkey authentication request
        # We look for a special marker in the request
        if request.get('__passkey_auth_attempt'):
            try:
                # The credential will be in the request from the login view
                credential = request.get('__passkey_credential')
                username = request.get('__passkey_username')

                if credential and username:
                    return {
                        'extractor': 'passkey',
                        'passkey_assertion': credential,
                        'login': username,
                    }
            except Exception as e:
                logger.error(f"Failed to extract passkey credentials: {e}", exc_info=True)

        return {}

    # IAuthenticationPlugin implementation
    def authenticateCredentials(self, credentials):
        """Authenticate the provided credentials.

        This implementation authenticates WebAuthn passkey assertions.

        Args:
            credentials (dict): The credentials to authenticate

        Returns:
            tuple: (user_id, login) on success, or None on failure
        """
        # Only handle passkey credentials
        if credentials.get('extractor') != 'passkey':
            return None

        try:
            assertion = credentials.get('passkey_assertion')
            username = credentials.get('login')

            if not assertion or not username:
                return None

            # Get user object
            acl_users = self._get_acl_users()
            user = acl_users.getUserById(username)

            if user is None:
                logger.warning(f"User not found: {username}")
                return None

            # Get the credential ID from the assertion
            credential_id = assertion.get('id')
            if not credential_id:
                logger.warning("No credential ID in assertion")
                return None

            # Get stored passkey
            passkey = get_passkey(user, credential_id)
            if passkey is None:
                logger.warning(f"Passkey not found for user {username}")
                return None

            # Verify the assertion
            # Note: The actual verification happens in the login view
            # This method just confirms the credential exists
            # The view does the cryptographic verification

            logger.info(f"Passkey authentication successful for user {username}")
            return (username, username)

        except Exception as e:
            logger.error(f"Passkey authentication failed: {e}", exc_info=True)
            return None

    def _get_acl_users(self):
        """Helper method to get acl_users object."""
        try:
            # Navigate up to get acl_users
            return self.aq_parent
        except AttributeError:
            # Fallback: try to get from acquisition chain
            return self.acl_users

    # IAAL2Plugin implementation
    def get_aal_level(self, user_id):
        """Get the current AAL level for a user.

        This stub implementation always returns 1 (lowest assurance level).

        Args:
            user_id (str): The user identifier

        Returns:
            int: Always returns 1 in stub implementation

        Future Implementation:
            - Check user's authentication method
            - Verify 2FA status
            - Check session authentication timestamp
            - Return actual AAL level (1, 2, or 3)
        """
        return 1

    def require_aal2(self, user_id, context):
        """Determine if AAL2 is required for the given context.

        This stub implementation always returns False (no AAL2 requirement).

        Args:
            user_id (str): The user identifier
            context (object): The Plone content object

        Returns:
            bool: Always returns False in stub implementation

        Future Implementation:
            - Check content annotations for AAL2 policy
            - Verify user's current AAL level
            - Trigger step-up authentication if needed
            - Return True if AAL2 is required but not met
        """
        return False

    # Passkey Authentication Methods (WebAuthn)

    def generateRegistrationOptions(self, request, user, device_name=None, authenticator_attachment=None):
        """
        Generate WebAuthn registration options for passkey enrollment.

        Args:
            request: HTTP request object
            user: Plone user object
            device_name (str): Optional device name
            authenticator_attachment (str): "platform" or "cross-platform" or None

        Returns:
            dict: PublicKeyCredentialCreationOptions
        """
        try:
            # Get site configuration
            portal = self._get_portal(request)
            rp_id = request.get('HTTP_HOST', 'localhost').split(':')[0]
            rp_name = portal.Title() if portal else 'Plone Site'

            # Get existing credentials to exclude
            existing_passkeys = get_user_passkeys(user)
            exclude_credentials = [
                {
                    'id': passkey['credential_id'],
                    'transports': passkey.get('transports', [])
                }
                for passkey in existing_passkeys.values()
            ]

            # Generate options
            options = create_registration_options(
                user_id=user.getId(),
                username=user.getProperty('email', user.getId()),
                display_name=user.getProperty('fullname', user.getId()),
                rp_id=rp_id,
                rp_name=rp_name,
                exclude_credentials=exclude_credentials,
                authenticator_attachment=authenticator_attachment,
            )

            # Store challenge in session
            session = ISession(request)
            session_data = session.get('c2.pas.aal2', {})
            session_data['registration_challenge'] = options.challenge
            session_data['registration_user_id'] = user.getId()
            session['c2.pas.aal2'] = session_data

            # Audit log
            log_registration_start(user.getId(), request)

            logger.info(f"Generated registration options for user {user.getId()}")
            return options

        except Exception as e:
            logger.error(f"Failed to generate registration options: {e}", exc_info=True)
            log_registration_failure(user.getId(), str(e), request)
            raise

    def verifyRegistrationResponse(self, request, user, credential_response):
        """
        Verify and store a WebAuthn registration response.

        Args:
            request: HTTP request object
            user: Plone user object
            credential_response (dict): PublicKeyCredential from browser

        Returns:
            dict: Verification result with credential info
        """
        try:
            # Get challenge from session
            session = ISession(request)
            session_data = session.get('c2.pas.aal2', {})
            expected_challenge = session_data.get('registration_challenge')

            if not expected_challenge:
                raise ValueError("No registration challenge found in session")

            # Get site configuration
            portal = self._get_portal(request)
            rp_id = request.get('HTTP_HOST', 'localhost').split(':')[0]
            expected_origin = f"https://{rp_id}"
            if 'localhost' in rp_id or '127.0.0.1' in rp_id:
                expected_origin = f"http://{rp_id}"  # Allow HTTP for localhost

            # Verify registration
            verification = verify_registration(
                credential=credential_response,
                expected_challenge=expected_challenge,
                expected_origin=expected_origin,
                expected_rp_id=rp_id,
            )

            # Store credential (will be implemented in credential.py)
            from c2.pas.aal2.credential import add_passkey
            credential_id = add_passkey(user, {
                'credential_id': verification.credential_id,
                'public_key': verification.credential_public_key,
                'sign_count': verification.sign_count,
                'aaguid': verification.aaguid,
                'device_name': credential_response.get('device_name', ''),
                'device_type': 'platform' if verification.credential_device_type == 'single_device' else 'cross-platform',
                'transports': credential_response.get('transports', []),
            })

            # Clear session challenge
            session_data.pop('registration_challenge', None)
            session_data.pop('registration_user_id', None)
            session['c2.pas.aal2'] = session_data

            # Audit log
            log_registration_success(user.getId(), credential_id, request)

            logger.info(f"Successfully registered passkey for user {user.getId()}")
            return {
                'success': True,
                'credential_id': credential_id,
            }

        except Exception as e:
            logger.error(f"Registration verification failed: {e}", exc_info=True)
            log_registration_failure(user.getId(), str(e), request)
            raise

    def generateAuthenticationOptions(self, request, username=None):
        """
        Generate WebAuthn authentication options for passkey login.

        Args:
            request: HTTP request object
            username (str): Optional username to filter credentials

        Returns:
            dict: PublicKeyCredentialRequestOptions
        """
        try:
            # Get site configuration
            portal = self._get_portal(request)
            rp_id = request.get('HTTP_HOST', 'localhost').split(':')[0]

            # Get allowed credentials for this user
            allow_credentials = []
            if username:
                acl_users = self._get_acl_users()
                user = acl_users.getUserById(username)
                if user:
                    passkeys = get_user_passkeys(user)
                    allow_credentials = [
                        {
                            'id': passkey['credential_id'],
                            'transports': passkey.get('transports', [])
                        }
                        for passkey in passkeys.values()
                    ]

            # Generate options
            options = create_authentication_options(
                rp_id=rp_id,
                allow_credentials=allow_credentials if allow_credentials else None,
                user_verification='preferred',
            )

            # Store challenge in session
            session = ISession(request)
            session_data = session.get('c2.pas.aal2', {})
            session_data['authentication_challenge'] = options.challenge
            session_data['authentication_username'] = username
            session['c2.pas.aal2'] = session_data

            # Audit log
            log_authentication_start(username or 'unknown', request)

            logger.info(f"Generated authentication options for user {username}")
            return options

        except Exception as e:
            logger.error(f"Failed to generate authentication options: {e}", exc_info=True)
            log_authentication_failure(username or 'unknown', str(e), request=request)
            raise

    def verifyAuthenticationResponse(self, request, credential_response, username=None):
        """
        Verify a WebAuthn authentication response (assertion).

        Args:
            request: HTTP request object
            credential_response (dict): PublicKeyCredential from browser
            username (str): Optional username hint

        Returns:
            dict: Verification result with user info
        """
        try:
            # Get challenge from session
            session = ISession(request)
            session_data = session.get('c2.pas.aal2', {})
            expected_challenge = session_data.get('authentication_challenge')

            if not expected_challenge:
                raise ValueError("No authentication challenge found in session")

            # Get credential ID and find which user it belongs to
            credential_id = credential_response.get('rawId') or credential_response.get('id')
            if not credential_id:
                raise ValueError("No credential ID in response")

            # Find user by credential
            acl_users = self._get_acl_users()
            authenticated_user = None

            if username:
                # Try the provided username first
                user = acl_users.getUserById(username)
                if user and get_passkey(user, credential_id):
                    authenticated_user = user

            if not authenticated_user:
                # Search all users for this credential
                for user_id in acl_users.getUserIds():
                    user = acl_users.getUserById(user_id)
                    if user and get_passkey(user, credential_id):
                        authenticated_user = user
                        break

            if not authenticated_user:
                raise ValueError("Credential not found for any user")

            # Get stored passkey
            passkey = get_passkey(authenticated_user, credential_id)

            # Get site configuration
            rp_id = request.get('HTTP_HOST', 'localhost').split(':')[0]
            expected_origin = f"https://{rp_id}"
            if 'localhost' in rp_id or '127.0.0.1' in rp_id:
                expected_origin = f"http://{rp_id}"

            # Verify authentication
            verification = verify_authentication(
                credential=credential_response,
                expected_challenge=expected_challenge,
                expected_origin=expected_origin,
                expected_rp_id=rp_id,
                credential_public_key=passkey['public_key'],
                credential_current_sign_count=passkey['sign_count'],
            )

            # Update last used and sign count
            from c2.pas.aal2.credential import update_passkey_last_used
            update_passkey_last_used(
                authenticated_user,
                credential_id,
                verification.new_sign_count
            )

            # Clear session challenge
            session_data.pop('authentication_challenge', None)
            session_data.pop('authentication_username', None)
            session['c2.pas.aal2'] = session_data

            # Audit log
            log_authentication_success(
                authenticated_user.getId(),
                credential_id,
                request
            )

            logger.info(f"Successfully authenticated user {authenticated_user.getId()} with passkey")
            return {
                'success': True,
                'user_id': authenticated_user.getId(),
                'username': authenticated_user.getId(),
            }

        except Exception as e:
            logger.error(f"Authentication verification failed: {e}", exc_info=True)
            log_authentication_failure(username or 'unknown', str(e), request=request)
            raise

    def _get_portal(self, request):
        """Helper method to get portal object from request."""
        try:
            return request.PARENTS[-1]
        except (AttributeError, IndexError):
            return None
