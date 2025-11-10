# -*- coding: utf-8 -*-
"""Browser views for passkey authentication."""

from Products.Five.browser import BrowserView
from plone import api
from plone.protect.interfaces import IDisableCSRFProtection
from webauthn.helpers import options_to_json
from AccessControl import Unauthorized
from zope.interface import alsoProvides
import json
import logging

logger = logging.getLogger('c2.pas.aal2.browser.views')


class PasskeyRegisterOptionsView(BrowserView):
    """Generate WebAuthn registration options for authenticated user."""

    def __call__(self):
        """Generate registration options.

        Returns:
            JSON response with PublicKeyCredentialCreationOptions
        """
        # Disable CSRF protection for WebAuthn API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Require authentication
        if api.user.is_anonymous():
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'authentication_required',
                'message': 'You must be logged in to register a passkey'
            })

        try:
            # Get current user
            current_user = api.user.get_current()
            member = api.user.get(username=current_user.getId())

            # Parse request body
            try:
                request_data = json.loads(self.request.get('BODY', '{}'))
            except json.JSONDecodeError:
                request_data = {}

            device_name = request_data.get('device_name')
            authenticator_attachment = request_data.get('authenticator_attachment')

            # Get plugin
            acl_users = api.portal.get_tool('acl_users')
            plugin = acl_users.get('aal2_plugin')

            if plugin is None:
                raise ValueError("AAL2 plugin not found")

            # Generate options
            options = plugin.generateRegistrationOptions(
                request=self.request,
                user=member,
                device_name=device_name,
                authenticator_attachment=authenticator_attachment,
            )

            # Convert to JSON-serializable format
            options_json = options_to_json(options)

            # Add session ID for tracking
            response_data = {
                'publicKey': json.loads(options_json),
                'session_id': 'reg_session_' + current_user.getId()
            }

            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(response_data)

        except Exception as e:
            logger.error(f"Failed to generate registration options: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'registration_options_failed',
                'message': 'Failed to generate registration options'
            })


class PasskeyRegisterVerifyView(BrowserView):
    """Verify and store WebAuthn registration response."""

    def __call__(self):
        """Verify registration response from browser.

        Returns:
            JSON response with verification result
        """
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Require authentication
        if api.user.is_anonymous():
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'authentication_required',
                'message': 'Session expired or not authenticated'
            })

        try:
            # Get current user
            current_user = api.user.get_current()
            member = api.user.get(username=current_user.getId())

            # Parse request body
            try:
                request_data = json.loads(self.request.get('BODY', '{}'))
            except json.JSONDecodeError:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'invalid_request',
                    'message': 'Invalid JSON in request body'
                })

            credential = request_data.get('credential')
            if not credential:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'missing_credential',
                    'message': 'Credential data is required'
                })

            # Get plugin
            acl_users = api.portal.get_tool('acl_users')
            plugin = acl_users.get('aal2_plugin')

            if plugin is None:
                raise ValueError("AAL2 plugin not found")

            # Verify registration
            result = plugin.verifyRegistrationResponse(
                request=self.request,
                user=member,
                credential_response=credential,
            )

            # Get stored credential details
            from c2.pas.aal2.credential import get_passkey
            passkey = get_passkey(member, result['credential_id'])

            self.request.response.setStatus(201)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({
                'success': True,
                'credential_id': result['credential_id'],
                'message': 'Passkey registered successfully',
                'credential': {
                    'credential_id': result['credential_id'],
                    'device_name': passkey.get('device_name', ''),
                    'device_type': passkey.get('device_type', ''),
                    'created': passkey.get('created').isoformat() if passkey.get('created') else None,
                    'transports': passkey.get('transports', []),
                }
            })

        except ValueError as e:
            logger.warning(f"Registration verification failed: {e}")
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'verification_failed',
                'message': str(e),
                'details': 'Challenge mismatch or expired'
            })
        except Exception as e:
            logger.error(f"Registration verification error: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'verification_failed',
                'message': 'Registration verification failed'
            })


class PasskeyRegisterFormView(BrowserView):
    """Display passkey registration form."""

    def __call__(self):
        """Render the registration form template."""
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        return self.index()


# ============================================================================
# Passkey Login Views (US2)
# ============================================================================

class PasskeyLoginOptionsView(BrowserView):
    """Generate WebAuthn authentication options for login."""

    def __call__(self):
        """Generate authentication options.

        Returns:
            JSON response with PublicKeyCredentialRequestOptions
        """
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        try:
            # Parse request body
            try:
                request_data = json.loads(self.request.get('BODY', '{}'))
            except json.JSONDecodeError:
                request_data = {}

            username = request_data.get('username')

            # Get plugin
            acl_users = api.portal.get_tool('acl_users')
            plugin = acl_users.get('aal2_plugin')

            if plugin is None:
                raise ValueError("AAL2 plugin not found")

            # Generate options
            options = plugin.generateAuthenticationOptions(
                request=self.request,
                username=username,
            )

            # Convert to JSON-serializable format
            options_json = options_to_json(options)

            # Add session ID for tracking
            response_data = {
                'publicKey': json.loads(options_json),
                'session_id': 'auth_session_' + (username or 'anonymous')
            }

            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps(response_data)

        except Exception as e:
            logger.error(f"Failed to generate authentication options: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'authentication_options_failed',
                'message': 'Failed to generate authentication options'
            })


class PasskeyLoginVerifyView(BrowserView):
    """Verify WebAuthn authentication response and create session."""

    def __call__(self):
        """Verify authentication response from browser.

        Returns:
            JSON response with verification result and session cookie
        """
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        try:
            # Parse request body
            try:
                request_data = json.loads(self.request.get('BODY', '{}'))
            except json.JSONDecodeError:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'invalid_request',
                    'message': 'Invalid JSON in request body'
                })

            credential = request_data.get('credential')
            if not credential:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'missing_credential',
                    'message': 'Credential data is required'
                })

            username = request_data.get('username')

            # Get plugin
            acl_users = api.portal.get_tool('acl_users')
            plugin = acl_users.get('aal2_plugin')

            if plugin is None:
                raise ValueError("AAL2 plugin not found")

            # Verify authentication
            result = plugin.verifyAuthenticationResponse(
                request=self.request,
                credential_response=credential,
                username=username,
            )

            # Create authenticated session
            # This is done by manually setting credentials in the request
            # and letting PAS handle the session creation
            user_id = result['user_id']

            # Mark the request with passkey credentials for PAS extraction
            self.request.set('__passkey_auth_attempt', True)
            self.request.set('__passkey_credential', credential)
            self.request.set('__passkey_username', user_id)

            # Get the authenticated user
            user = acl_users.getUserById(user_id)
            if user is None:
                raise ValueError("User not found after verification")

            # Create authenticated session using cookie_authentication plugin
            # We need to call the cookie_authentication plugin's updateCredentials
            # method to properly encrypt and set the __ac cookie
            #
            # TODO/REFACTORING: This cookie-setting logic should be moved to the
            # AAL2Plugin itself by implementing ICredentialsUpdatePlugin interface.
            # Current implementation violates separation of concerns - the view
            # should only handle HTTP request/response, while the PAS plugin should
            # handle authentication state management (including cookies).
            from Products.PluggableAuthService.interfaces.plugins import ICredentialsUpdatePlugin

            # Find and call cookie_authentication plugin
            cookie_auth_set = False
            try:
                for plugin_name in acl_users.plugins.listPluginIds(ICredentialsUpdatePlugin):
                    plugin = acl_users[plugin_name]
                    # Look for cookie_authentication or similar plugin
                    if 'cookie' in plugin_name.lower() or hasattr(plugin, 'getCookie'):
                        try:
                            # Call updateCredentials with username (password not needed for passkey)
                            plugin.updateCredentials(self.request, self.request.response, user_id, '')
                            logger.info(f"Set authentication cookie via plugin: {plugin_name}")
                            cookie_auth_set = True
                            break
                        except Exception as e:
                            logger.warning(f"Failed to set cookie via {plugin_name}: {e}")
            except Exception as e:
                logger.error(f"Error setting authentication cookie: {e}", exc_info=True)

            if not cookie_auth_set:
                logger.warning("No cookie authentication plugin found - session may not persist")

            # Also set the AUTHENTICATED_USER in current request context
            from AccessControl.SecurityManagement import newSecurityManager
            newSecurityManager(self.request, user)
            logger.info(f"Set security context for user {user_id}")

            # Get redirect URL (typically portal URL)
            portal = api.portal.get()
            redirect_url = portal.absolute_url()

            # Check if there's a came_from parameter
            came_from = self.request.get('came_from', redirect_url)

            # Return JSON with redirect URL
            # JavaScript will handle the redirect
            self.request.response.setHeader('Content-Type', 'application/json')
            logger.info(f"Authentication successful for user {user_id}, will redirect to {came_from}")
            return json.dumps({
                'success': True,
                'user_id': user_id,
                'message': 'Authentication successful',
                'redirect_url': came_from,
            })

        except ValueError as e:
            logger.warning(f"Authentication verification failed: {e}")
            self.request.response.setStatus(400)
            return json.dumps({
                'error': 'verification_failed',
                'message': str(e),
                'details': 'Invalid signature or challenge mismatch'
            })
        except Exception as e:
            logger.error(f"Authentication verification error: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'verification_failed',
                'message': 'Authentication failed'
            })


class PasskeyLoginFormView(BrowserView):
    """Display passkey login form."""

    def __call__(self):
        """Render the login form template."""
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        return self.index()


# ============================================================================
# Passkey Management Views (US3)
# ============================================================================

class PasskeyListView(BrowserView):
    """List all registered passkeys for the current user."""

    def __call__(self):
        """List user's passkeys.

        Returns:
            JSON response with list of passkeys
        """
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Require authentication
        if api.user.is_anonymous():
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'authentication_required',
                'message': 'You must be logged in'
            })

        try:
            # Get current user
            current_user = api.user.get_current()
            member = api.user.get(username=current_user.getId())

            # Get passkeys
            from c2.pas.aal2.credential import get_user_passkeys
            passkeys = get_user_passkeys(member)

            # Convert to list with metadata
            passkey_list = []
            for credential_id_b64, passkey in passkeys.items():
                passkey_list.append({
                    'credential_id': credential_id_b64,
                    'device_name': passkey.get('device_name', ''),
                    'device_type': passkey.get('device_type', 'cross-platform'),
                    'created': passkey.get('created').isoformat() if passkey.get('created') else None,
                    'last_used': passkey.get('last_used').isoformat() if passkey.get('last_used') else None,
                    'transports': passkey.get('transports', []),
                })

            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({
                'passkeys': passkey_list,
                'count': len(passkey_list)
            })

        except Exception as e:
            logger.error(f"Failed to list passkeys: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'list_failed',
                'message': 'Failed to list passkeys'
            })


class PasskeyDeleteView(BrowserView):
    """Delete a registered passkey."""

    def __call__(self):
        """Delete a passkey.

        Returns:
            JSON response with deletion result
        """
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Require authentication
        if api.user.is_anonymous():
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'authentication_required',
                'message': 'You must be logged in'
            })

        try:
            # Parse request body
            try:
                request_data = json.loads(self.request.get('BODY', '{}'))
            except json.JSONDecodeError:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'invalid_request',
                    'message': 'Invalid JSON in request body'
                })

            credential_id = request_data.get('credential_id')
            if not credential_id:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'missing_credential_id',
                    'message': 'credential_id is required'
                })

            # Get current user
            current_user = api.user.get_current()
            member = api.user.get(username=current_user.getId())

            # Check if this is the last authentication method (FR-016)
            from c2.pas.aal2.credential import count_passkeys, delete_passkey

            passkey_count = count_passkeys(member)

            # Check if user has a password
            has_password = member.getProperty('password', None) is not None

            if passkey_count == 1 and not has_password:
                self.request.response.setStatus(403)
                return json.dumps({
                    'error': 'last_credential',
                    'message': 'Cannot remove last authentication method. Please set a password first.',
                    'remaining_passkeys': 1,
                    'has_password': False
                })

            # Delete the passkey
            success = delete_passkey(member, credential_id)

            if not success:
                self.request.response.setStatus(404)
                return json.dumps({
                    'error': 'credential_not_found',
                    'message': 'Passkey not found'
                })

            # Audit log
            from c2.pas.aal2.utils.audit import log_credential_deleted
            log_credential_deleted(member.getId(), credential_id, self.request)

            # Return success
            remaining = count_passkeys(member)
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({
                'success': True,
                'message': 'Passkey removed successfully',
                'remaining_passkeys': remaining
            })

        except Exception as e:
            logger.error(f"Failed to delete passkey: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'delete_failed',
                'message': 'Failed to delete passkey'
            })


class PasskeyUpdateView(BrowserView):
    """Update passkey metadata (device name)."""

    def __call__(self):
        """Update passkey metadata.

        Returns:
            JSON response with update result
        """
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Require authentication
        if api.user.is_anonymous():
            self.request.response.setStatus(401)
            return json.dumps({
                'error': 'authentication_required',
                'message': 'You must be logged in'
            })

        try:
            # Parse request body
            try:
                request_data = json.loads(self.request.get('BODY', '{}'))
            except json.JSONDecodeError:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'invalid_request',
                    'message': 'Invalid JSON in request body'
                })

            credential_id = request_data.get('credential_id')
            device_name = request_data.get('device_name')

            if not credential_id:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'missing_credential_id',
                    'message': 'credential_id is required'
                })

            if not device_name:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'missing_device_name',
                    'message': 'device_name is required'
                })

            if len(device_name) > 100:
                self.request.response.setStatus(400)
                return json.dumps({
                    'error': 'validation_error',
                    'message': 'device_name exceeds maximum length'
                })

            # Get current user
            current_user = api.user.get_current()
            member = api.user.get(username=current_user.getId())

            # Get and update passkey
            from c2.pas.aal2.credential import get_passkey, get_user_passkeys
            from zope.annotation.interfaces import IAnnotations

            passkey = get_passkey(member, credential_id)
            if passkey is None:
                self.request.response.setStatus(404)
                return json.dumps({
                    'error': 'credential_not_found',
                    'message': 'Passkey not found'
                })

            # Update device name
            passkey['device_name'] = device_name

            # Save changes
            annotations = IAnnotations(member)
            passkeys = get_user_passkeys(member)
            annotations['c2.pas.aal2.passkeys'] = passkeys
            member._p_changed = True

            # Return updated credential
            self.request.response.setHeader('Content-Type', 'application/json')
            return json.dumps({
                'success': True,
                'message': 'Passkey updated successfully',
                'credential': {
                    'credential_id': credential_id,
                    'device_name': passkey.get('device_name', ''),
                    'device_type': passkey.get('device_type', ''),
                    'created': passkey.get('created').isoformat() if passkey.get('created') else None,
                    'last_used': passkey.get('last_used').isoformat() if passkey.get('last_used') else None,
                }
            })

        except Exception as e:
            logger.error(f"Failed to update passkey: {e}", exc_info=True)
            self.request.response.setStatus(500)
            return json.dumps({
                'error': 'update_failed',
                'message': 'Failed to update passkey'
            })


class PasskeyManageView(BrowserView):
    """Display passkey management interface."""

    def __call__(self):
        """Render the management template."""
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        return self.index()


# ============================================================================
# Enhanced Login View (US4)
# ============================================================================

class EnhancedLoginView(BrowserView):
    """Enhanced login view with passkey and password options."""

    def __call__(self):
        """Render the enhanced login template."""
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        return self.index()

    def standard_login_form(self):
        """Return the standard Plone login form HTML."""
        # Get the standard login form from Plone
        # This includes all the standard password login fields

        # Create a simple form that posts to acl_users/credentials_cookie_auth/login
        portal_url = api.portal.get().absolute_url()
        came_from = self.request.get('came_from', portal_url)

        return f"""
        <form action="{portal_url}/acl_users/credentials_cookie_auth/require_login" method="post">
          <input type="hidden" name="came_from" value="{came_from}" />

          <div class="field">
            <label for="__ac_name">Username</label>
            <input type="text"
                   id="__ac_name"
                   name="__ac_name"
                   class="form-control"
                   required />
          </div>

          <div class="field">
            <label for="__ac_password">Password</label>
            <input type="password"
                   id="__ac_password"
                   name="__ac_password"
                   class="form-control"
                   required />
          </div>

          <div class="field">
            <input type="checkbox"
                   id="__ac_persistent"
                   name="__ac_persistent:int"
                   value="1" />
            <label for="__ac_persistent">Remember me</label>
          </div>

          <div class="formControls">
            <button type="submit" class="btn btn-primary">Sign In</button>
          </div>
        </form>
        """


class AAL2ChallengeView(BrowserView):
    """AAL2 step-up authentication challenge view.

    This view is displayed when a user tries to access AAL2-protected content
    but their AAL2 authentication has expired (>15 minutes since last passkey auth).
    """

    def __call__(self):
        """Render the AAL2 challenge page."""
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Check if user is authenticated
        if api.user.is_anonymous():
            # Redirect to login page
            portal_url = api.portal.get().absolute_url()
            came_from = self.request.get('came_from', portal_url)
            login_url = f"{portal_url}/login?came_from={came_from}"
            return self.request.response.redirect(login_url)

        # Get came_from parameter (where to redirect after successful auth)
        self.came_from = self.request.get('came_from', api.portal.get().absolute_url())

        # Get current user info
        current_user = api.user.get_current()
        self.username = current_user.getId()
        self.user_fullname = current_user.getProperty('fullname', self.username)

        # Check AAL2 status
        from c2.pas.aal2.session import is_aal2_valid, get_aal2_expiry, get_remaining_time
        self.aal2_valid = is_aal2_valid(current_user)

        if self.aal2_valid:
            # Already authenticated, redirect to came_from
            logger.info(f"User {self.username} already has valid AAL2, redirecting to {self.came_from}")
            return self.request.response.redirect(self.came_from)

        # Get expiry info if exists
        expiry = get_aal2_expiry(current_user)
        if expiry:
            self.expiry_time = expiry.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.expiry_time = None

        return self.index()

    def get_challenge_message(self):
        """Get user-friendly challenge message."""
        return (
            "For your security, access to this resource requires recent authentication with your passkey. "
            "Please authenticate using your passkey to continue."
        )

    def get_help_text(self):
        """Get help text for the challenge."""
        return (
            "AAL2 (Authenticator Assurance Level 2) requires you to re-authenticate with your passkey "
            "every 15 minutes when accessing protected resources. This ensures the highest level of security "
            "for sensitive content."
        )


class AAL2SettingsView(BrowserView):
    """AAL2 settings and management view for administrators.

    Allows administrators to:
    - View AAL2 configuration
    - List AAL2-protected content
    - List users with AAL2 Required User role
    - Manage AAL2 policies
    """

    def __call__(self):
        """Render the AAL2 settings page."""
        # Disable CSRF protection for WebAuthn/API calls
        alsoProvides(self.request, IDisableCSRFProtection)

        # Require Manager role
        if not api.user.has_permission('Manage portal'):
            raise Unauthorized("You must be a Manager to access AAL2 settings")

        # Handle form submissions
        if self.request.method == 'POST':
            # Verify CSRF token
            from plone.protect import CheckAuthenticator
            CheckAuthenticator(self.request)

            action = self.request.form.get('action')

            if action == 'set_content_policy':
                return self.set_content_policy()
            elif action == 'assign_role':
                return self.assign_aal2_role()
            elif action == 'revoke_role':
                return self.revoke_aal2_role()

        return self.index()

    def get_aal2_protected_content(self):
        """Get list of AAL2-protected content items."""
        from c2.pas.aal2.policy import list_aal2_protected_content
        try:
            return list_aal2_protected_content()
        except Exception as e:
            logger.error(f"Failed to list AAL2 protected content: {e}", exc_info=True)
            return []

    def get_aal2_users(self):
        """Get list of users with AAL2 Required User role."""
        from c2.pas.aal2.roles import list_aal2_users
        try:
            portal = api.portal.get()
            return list_aal2_users(portal)
        except Exception as e:
            logger.error(f"Failed to list AAL2 users: {e}", exc_info=True)
            return []

    def get_all_users(self):
        """Get list of all users (for role assignment)."""
        try:
            acl_users = api.portal.get_tool('acl_users')
            user_ids = acl_users.getUserIds()
            return sorted(user_ids)
        except Exception as e:
            logger.error(f"Failed to list users: {e}", exc_info=True)
            return []

    def set_content_policy(self):
        """Set AAL2 policy on content item."""
        from c2.pas.aal2.policy import set_aal2_required
        from c2.pas.aal2.utils.audit import log_aal2_policy_set

        content_path = self.request.form.get('content_path')
        required = self.request.form.get('required') == 'true'

        if not content_path:
            api.portal.show_message(
                message="Content path is required",
                request=self.request,
                type='error'
            )
            return self.request.response.redirect(self.request.URL)

        try:
            # Get content object
            portal = api.portal.get()
            content = portal.unrestrictedTraverse(content_path)

            # Set policy
            set_aal2_required(content, required=required)

            # Log the change
            current_user = api.user.get_current()
            log_aal2_policy_set(
                content_path=content_path,
                required=required,
                admin_user_id=current_user.getId(),
                request=self.request
            )

            action_text = "enabled" if required else "disabled"
            api.portal.show_message(
                message=f"AAL2 protection {action_text} for {content_path}",
                request=self.request,
                type='info'
            )

        except Exception as e:
            logger.error(f"Failed to set AAL2 policy: {e}", exc_info=True)
            api.portal.show_message(
                message=f"Error setting AAL2 policy: {str(e)}",
                request=self.request,
                type='error'
            )

        return self.request.response.redirect(self.request.URL)

    def assign_aal2_role(self):
        """Assign AAL2 Required User role to a user."""
        from c2.pas.aal2.roles import assign_aal2_role
        from c2.pas.aal2.utils.audit import log_aal2_role_assigned

        user_id = self.request.form.get('user_id')

        if not user_id:
            api.portal.show_message(
                message="User ID is required",
                request=self.request,
                type='error'
            )
            return self.request.response.redirect(self.request.URL)

        try:
            portal = api.portal.get()
            success = assign_aal2_role(user_id, portal)

            if success:
                # Log the assignment
                current_user = api.user.get_current()
                log_aal2_role_assigned(
                    user_id=user_id,
                    admin_user_id=current_user.getId(),
                    request=self.request
                )

                api.portal.show_message(
                    message=f"AAL2 Required User role assigned to {user_id}",
                    request=self.request,
                    type='info'
                )
            else:
                api.portal.show_message(
                    message=f"Failed to assign AAL2 role to {user_id}",
                    request=self.request,
                    type='error'
                )

        except Exception as e:
            logger.error(f"Failed to assign AAL2 role: {e}", exc_info=True)
            api.portal.show_message(
                message=f"Error assigning AAL2 role: {str(e)}",
                request=self.request,
                type='error'
            )

        return self.request.response.redirect(self.request.URL)

    def revoke_aal2_role(self):
        """Revoke AAL2 Required User role from a user."""
        from c2.pas.aal2.roles import revoke_aal2_role
        from c2.pas.aal2.utils.audit import log_aal2_role_revoked

        user_id = self.request.form.get('user_id')

        if not user_id:
            api.portal.show_message(
                message="User ID is required",
                request=self.request,
                type='error'
            )
            return self.request.response.redirect(self.request.URL)

        try:
            portal = api.portal.get()
            success = revoke_aal2_role(user_id, portal)

            if success:
                # Log the revocation
                current_user = api.user.get_current()
                log_aal2_role_revoked(
                    user_id=user_id,
                    admin_user_id=current_user.getId(),
                    request=self.request
                )

                api.portal.show_message(
                    message=f"AAL2 Required User role revoked from {user_id}",
                    request=self.request,
                    type='info'
                )
            else:
                api.portal.show_message(
                    message=f"Failed to revoke AAL2 role from {user_id}",
                    request=self.request,
                    type='error'
                )

        except Exception as e:
            logger.error(f"Failed to revoke AAL2 role: {e}", exc_info=True)
            api.portal.show_message(
                message=f"Error revoking AAL2 role: {str(e)}",
                request=self.request,
                type='error'
            )

        return self.request.response.redirect(self.request.URL)
