# -*- coding: utf-8 -*-
"""Browser views for passkey authentication."""

from Products.Five.browser import BrowserView
from plone import api
from webauthn.helpers import options_to_json
import json
import logging

logger = logging.getLogger('c2.pas.aal2.browser.views')


class PasskeyRegisterOptionsView(BrowserView):
    """Generate WebAuthn registration options for authenticated user."""

    def __call__(self):
        """
        Generate registration options.

        Returns:
            JSON response with PublicKeyCredentialCreationOptions
        """
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
        """
        Verify registration response from browser.

        Returns:
            JSON response with verification result
        """
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
        return self.index()


# ============================================================================
# Passkey Login Views (US2)
# ============================================================================

class PasskeyLoginOptionsView(BrowserView):
    """Generate WebAuthn authentication options for login."""

    def __call__(self):
        """
        Generate authentication options.

        Returns:
            JSON response with PublicKeyCredentialRequestOptions
        """
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
        """
        Verify authentication response from browser.

        Returns:
            JSON response with verification result and session cookie
        """
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

            # Trigger PAS authentication
            user = acl_users.getUserById(user_id)
            if user is None:
                raise ValueError("User not found after verification")

            # Create session by calling the updateCredentials hook
            # This will set the __ac cookie
            acl_users._updateCredentials(self.request, self.request.response, user_id, '')

            # Get redirect URL (typically portal URL)
            portal = api.portal.get()
            redirect_url = portal.absolute_url()

            # Check if there's a came_from parameter
            came_from = self.request.get('came_from', redirect_url)

            self.request.response.setHeader('Content-Type', 'application/json')
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
        return self.index()


# ============================================================================
# Passkey Management Views (US3)
# ============================================================================

class PasskeyListView(BrowserView):
    """List all registered passkeys for the current user."""

    def __call__(self):
        """
        List user's passkeys.

        Returns:
            JSON response with list of passkeys
        """
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
        """
        Delete a passkey.

        Returns:
            JSON response with deletion result
        """
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
        """
        Update passkey metadata.

        Returns:
            JSON response with update result
        """
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
        return self.index()


# ============================================================================
# Enhanced Login View (US4)
# ============================================================================

class EnhancedLoginView(BrowserView):
    """Enhanced login view with passkey and password options."""

    def __call__(self):
        """Render the enhanced login template."""
        return self.index()

    def standard_login_form(self):
        """Return the standard Plone login form HTML."""
        # Get the standard login form from Plone
        # This includes all the standard password login fields
        from Products.CMFPlone.browser.login.login import LoginForm

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
