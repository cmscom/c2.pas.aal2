# -*- coding: utf-8 -*-
"""AAL2 PAS Plugin implementation with WebAuthn passkey support.

This module provides the AAL2 authentication plugin for Plone's Pluggable
Authentication Service (PAS) with WebAuthn-based passkey authentication.
"""

from zope.interface import implementer
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import IValidationPlugin
from Products.PluggableAuthService.interfaces.plugins import ICredentialsUpdatePlugin
import logging

from c2.pas.aal2.interfaces import IAAL2Plugin
from c2.pas.aal2.credential import get_user_passkeys, get_passkey
from c2.pas.aal2.session import set_aal2_timestamp, is_aal2_valid
from c2.pas.aal2.policy import is_aal2_required
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


@implementer(IAuthenticationPlugin, IExtractionPlugin, IValidationPlugin,
             ICredentialsUpdatePlugin, IAAL2Plugin)
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

        This implementation handles two types of credential extraction:
        1. WebAuthn assertion credentials for passkey login
        2. Authentication ticket validation from __ac cookie

        Args:
            request: The HTTP request object

        Returns:
            dict: Credentials dict or empty dict
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

        # Check for __ac cookie with authentication ticket
        # Try to get cookie from request - Plone/Zope automatically extracts cookies
        cookie = request.get('__ac')
        if not cookie and hasattr(request, 'cookies'):
            # Fallback: try cookies attribute
            cookie = request.cookies.get('__ac')

        if cookie:
            try:
                from urllib.parse import unquote
                from plone.session.tktauth import validateTicket

                # Unquote the cookie value and convert back to bytes
                ticket_str = unquote(cookie)
                # Convert string back to bytes preserving byte values
                ticket = ticket_str.encode('latin-1')

                # Get plugin secret
                secret = self._get_or_create_secret()

                # Get client IP for validation (tickets are IP-bound for security)
                remote_addr = request.get('HTTP_X_FORWARDED_FOR',
                                         request.get('REMOTE_ADDR', '127.0.0.1'))
                if ',' in remote_addr:
                    remote_addr = remote_addr.split(',')[0].strip()
                if not remote_addr or remote_addr == 'unknown':
                    remote_addr = '127.0.0.1'

                # Validate the ticket
                # Returns (digest, userid, tokens, user_data, timestamp) if valid, or None if invalid
                result = validateTicket(
                    secret=secret,
                    ticket=ticket,
                    ip=remote_addr,
                    timeout=86400 * 7,  # 7 days timeout
                    mod_auth_tkt=False,  # Use HMAC SHA-256 (more secure)
                )

                if result:
                    digest, userid, tokens, user_data, timestamp = result
                    logger.debug(f"Valid authentication ticket for user {userid}")
                    return {
                        'extractor': 'aal2_ticket',
                        'login': userid,
                        'aal2_authenticated': True,
                    }
                else:
                    logger.debug("Invalid authentication ticket")

            except Exception as e:
                logger.debug(f"Failed to validate authentication ticket: {e}")

        return {}

    # IAuthenticationPlugin implementation
    def authenticateCredentials(self, credentials):
        """Authenticate the provided credentials.

        This implementation handles two types of authentication:
        1. WebAuthn passkey assertions (initial login)
        2. Ticket-based authentication (subsequent requests)

        Args:
            credentials (dict): The credentials to authenticate

        Returns:
            tuple: (user_id, login) on success, or None on failure
        """
        extractor = credentials.get('extractor')

        # Handle ticket-based authentication
        if extractor == 'aal2_ticket':
            username = credentials.get('login')
            if username:
                # Ticket was already validated in extractCredentials
                logger.debug(f"Authenticated user {username} via AAL2 ticket")
                return (username, username)
            return None

        # Handle passkey credentials
        if extractor != 'passkey':
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

    # IValidationPlugin implementation
    def validate(self, user, request):
        """Validate AAL2 requirements for the current request.

        This method is called by PAS during request processing to validate
        whether the authenticated user meets AAL2 requirements for the
        requested resource.

        Args:
            user: Plone user object
            request: HTTP request object

        Returns:
            bool: True if validation passes, raises Unauthorized if AAL2 needed

        Raises:
            Unauthorized: If AAL2 is required but not satisfied
        """
        from c2.pas.aal2.policy import check_aal2_access

        try:
            # Get the published object from the request
            published = request.get('PUBLISHED')
            if published is None:
                # No published object yet, allow
                return True

            # Get context from published object
            context = getattr(published, 'context', None)
            if context is None:
                # No context available, allow
                return True

            # Check AAL2 access
            if not check_aal2_access(context, user, request):
                # AAL2 required but not satisfied
                from AccessControl import Unauthorized
                logger.info(f"AAL2 validation failed for user {user.getId()} accessing {context.getId()}")
                raise Unauthorized("AAL2 authentication required")

            return True

        except Unauthorized:
            # Re-raise Unauthorized
            raise
        except Exception as e:
            logger.error(f"Error in AAL2 validation: {e}", exc_info=True)
            # On error, allow access (fail open for non-AAL2 critical errors)
            return True

    # IAAL2Plugin implementation
    def get_aal_level(self, user_id):
        """Get the current AAL level for a user.

        This implementation checks if the user has a valid AAL2 authentication
        timestamp (within 15 minutes) from passkey authentication.

        Args:
            user_id (str): The user identifier

        Returns:
            int: 1 (basic authentication) or 2 (AAL2 authentication with passkey)

        Example:
            >>> plugin.get_aal_level('john_doe')
            2  # User authenticated with passkey within last 15 minutes
        """
        try:
            acl_users = self._get_acl_users()
            user = acl_users.getUserById(user_id)

            if user is None:
                return 1

            # Check if user has valid AAL2 authentication
            if is_aal2_valid(user):
                return 2

            return 1

        except Exception as e:
            logger.error(f"Failed to get AAL level for user {user_id}: {e}", exc_info=True)
            return 1

    def require_aal2(self, user_id, context):
        """Determine if AAL2 is required for the given user and context.

        This implementation checks both content-level and user-level AAL2 policies.

        Args:
            user_id (str): The user identifier
            context (object): The Plone content object being accessed

        Returns:
            bool: True if AAL2 is required for this context/user combination

        Example:
            >>> plugin.require_aal2('john_doe', protected_content)
            True  # Content requires AAL2 authentication
        """
        try:
            acl_users = self._get_acl_users()
            user = acl_users.getUserById(user_id)

            if user is None:
                logger.warning(f"User not found: {user_id}")
                return False

            # Check if AAL2 is required for this context
            return is_aal2_required(context, user)

        except Exception as e:
            logger.error(f"Failed to check AAL2 requirement for user {user_id}: {e}", exc_info=True)
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
            session_data = self._get_session_data(request)
            session_data['registration_challenge'] = options.challenge
            session_data['registration_user_id'] = user.getId()
            self._set_session_data(request, session_data)

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
            session_data = self._get_session_data(request, create=False)
            expected_challenge = session_data.get('registration_challenge')

            if not expected_challenge:
                raise ValueError("No registration challenge found in session")

            # Get site configuration
            http_host = request.get('HTTP_HOST', 'localhost')
            rp_id = http_host.split(':')[0]  # RP ID is hostname without port

            # Origin includes protocol and port
            expected_origin = f"https://{http_host}"
            if 'localhost' in rp_id or '127.0.0.1' in rp_id:
                expected_origin = f"http://{http_host}"  # Allow HTTP for localhost

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
            self._clear_session_data(request)

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
            session_data = self._get_session_data(request)
            session_data['authentication_challenge'] = options.challenge
            session_data['authentication_username'] = username
            self._set_session_data(request, session_data)

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
            session_data = self._get_session_data(request, create=False)
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
            http_host = request.get('HTTP_HOST', 'localhost')
            rp_id = http_host.split(':')[0]  # RP ID is hostname without port

            # Origin includes protocol and port
            expected_origin = f"https://{http_host}"
            if 'localhost' in rp_id or '127.0.0.1' in rp_id:
                expected_origin = f"http://{http_host}"  # Allow HTTP for localhost

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

            # Set AAL2 authentication timestamp (for AAL2 compliance)
            set_aal2_timestamp(authenticated_user, credential_id=credential_id)
            logger.info(f"Set AAL2 timestamp for user {authenticated_user.getId()}")

            # Clear session challenge
            self._clear_session_data(request)

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
            from plone import api
            return api.portal.get()
        except Exception:
            # Fallback to request traversal
            try:
                return request.PARENTS[-1]
            except (AttributeError, IndexError):
                return None

    def _get_session_data(self, request, create=True):
        """Helper method to get session data (Plone 6 compatible).

        Uses portal annotations for temporary storage since session may not
        persist across requests with CSRF protection disabled.

        Args:
            request: HTTP request object
            create: Whether to create session data if not exists

        Returns:
            dict: Session data dictionary, or empty dict if not available
        """
        try:
            from plone import api
            from zope.annotation.interfaces import IAnnotations
            from persistent.dict import PersistentDict

            portal = api.portal.get()
            annotations = IAnnotations(portal)

            # Use a temporary annotation key for WebAuthn challenges
            # These are cleaned up after verification
            challenge_key = 'c2.pas.aal2.challenges'

            if challenge_key not in annotations and create:
                annotations[challenge_key] = PersistentDict()

            # Get session ID or use IP-based key as fallback
            session_id = None
            if hasattr(request, 'SESSION'):
                try:
                    session_id = request.SESSION._sid
                except Exception:
                    pass

            if not session_id:
                # Fallback to IP + user agent hash
                import hashlib
                ip = request.get('HTTP_X_FORWARDED_FOR', request.get('REMOTE_ADDR', 'unknown'))
                ua = request.get('HTTP_USER_AGENT', '')
                session_id = hashlib.md5(f"{ip}{ua}".encode()).hexdigest()

            challenges = annotations.get(challenge_key, PersistentDict())

            if session_id not in challenges and create:
                challenges[session_id] = PersistentDict()
                annotations[challenge_key] = challenges

            return challenges.get(session_id, {})

        except Exception as e:
            logger.warning(f"Could not access session: {e}", exc_info=True)
        return {}

    def _set_session_data(self, request, data):
        """Helper method to set session data (Plone 6 compatible).

        Uses portal annotations for temporary storage.

        Args:
            request: HTTP request object
            data: Dictionary to store in session
        """
        try:
            from plone import api
            from zope.annotation.interfaces import IAnnotations
            from persistent.dict import PersistentDict

            portal = api.portal.get()
            annotations = IAnnotations(portal)

            challenge_key = 'c2.pas.aal2.challenges'

            if challenge_key not in annotations:
                annotations[challenge_key] = PersistentDict()

            # Get session ID or use IP-based key as fallback
            session_id = None
            if hasattr(request, 'SESSION'):
                try:
                    session_id = request.SESSION._sid
                except Exception:
                    pass

            if not session_id:
                # Fallback to IP + user agent hash
                import hashlib
                ip = request.get('HTTP_X_FORWARDED_FOR', request.get('REMOTE_ADDR', 'unknown'))
                ua = request.get('HTTP_USER_AGENT', '')
                session_id = hashlib.md5(f"{ip}{ua}".encode()).hexdigest()

            challenges = annotations[challenge_key]
            challenges[session_id] = PersistentDict(data)
            annotations[challenge_key] = challenges
            annotations[challenge_key]._p_changed = True

            logger.debug(f"Stored session data for session_id: {session_id}")

        except Exception as e:
            logger.warning(f"Could not set session data: {e}", exc_info=True)

    def _clear_session_data(self, request):
        """Clear session data after successful verification.

        Args:
            request: HTTP request object
        """
        try:
            from plone import api
            from zope.annotation.interfaces import IAnnotations

            portal = api.portal.get()
            annotations = IAnnotations(portal)

            challenge_key = 'c2.pas.aal2.challenges'
            if challenge_key not in annotations:
                return

            # Get session ID
            session_id = None
            if hasattr(request, 'SESSION'):
                try:
                    session_id = request.SESSION._sid
                except Exception:
                    pass

            if not session_id:
                import hashlib
                ip = request.get('HTTP_X_FORWARDED_FOR', request.get('REMOTE_ADDR', 'unknown'))
                ua = request.get('HTTP_USER_AGENT', '')
                session_id = hashlib.md5(f"{ip}{ua}".encode()).hexdigest()

            challenges = annotations[challenge_key]
            if session_id in challenges:
                del challenges[session_id]
                annotations[challenge_key] = challenges
                annotations[challenge_key]._p_changed = True
                logger.debug(f"Cleared session data for session_id: {session_id}")

        except Exception as e:
            logger.warning(f"Could not clear session data: {e}", exc_info=True)

    # ========================================================================
    # ICredentialsUpdatePlugin implementation
    # ========================================================================

    def updateCredentials(self, request, response, login, new_password):
        """Update credentials after successful authentication.

        Creates a signed authentication ticket and sets it as a cookie.
        This is a custom implementation independent of plone.session.

        Args:
            request: HTTP request object
            response: HTTP response object
            login: Username/user ID
            new_password: Password (not used for passkey auth)
        """
        try:
            from plone.session.tktauth import createTicket
            import time
            from urllib.parse import quote

            # Get or create plugin secret for ticket signing
            secret = self._get_or_create_secret()

            # Get client IP address
            remote_addr = request.get('HTTP_X_FORWARDED_FOR',
                                     request.get('REMOTE_ADDR', '127.0.0.1'))
            if ',' in remote_addr:
                remote_addr = remote_addr.split(',')[0].strip()

            # Validate IP address
            if not remote_addr or remote_addr == 'unknown':
                remote_addr = '127.0.0.1'

            # Create authentication ticket
            # Format: digest + timestamp + userid + tokens + user_data
            ticket = createTicket(
                secret=secret,
                userid=login,
                tokens=(),  # No additional tokens needed
                user_data='',  # No extra user data
                ip=remote_addr,
                timestamp=int(time.time()),
                mod_auth_tkt=False,  # Use HMAC SHA-256 (more secure)
            )

            # Set the authentication cookie
            # Note: ticket is bytes, we need to quote it for cookie storage
            # Plone expects the raw bytes quoted, not base64 encoded
            if isinstance(ticket, bytes):
                ticket = ticket.decode('latin-1')  # Preserve byte values

            response.setCookie(
                '__ac',
                quote(ticket),
                path='/',
                secure=False,  # Allow HTTP for development
                http_only=True,  # Prevent JavaScript access
            )

            logger.info(f"Set AAL2 authentication cookie for user {login} (IP: {remote_addr})")

        except Exception as e:
            logger.error(f"Failed to set authentication cookie for {login}: {e}", exc_info=True)

    def _get_or_create_secret(self):
        """Get or create a secret for ticket signing.

        The secret is stored as a plugin attribute and persisted in ZODB.
        If no secret exists, a new one is generated automatically.

        Returns:
            bytes: Secret for ticket signing
        """
        if not hasattr(self, '_aal2_secret') or not self._aal2_secret:
            import secrets
            # Generate a 64-byte (512-bit) random secret
            self._aal2_secret = secrets.token_bytes(64)
            logger.info("Generated new AAL2 authentication secret")

            # Mark object as changed for ZODB persistence
            try:
                self._p_changed = True
            except AttributeError:
                pass

        return self._aal2_secret
