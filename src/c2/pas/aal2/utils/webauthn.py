# -*- coding: utf-8 -*-
"""WebAuthn ceremony wrapper functions using py_webauthn library."""

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorTransport,
)
import logging

logger = logging.getLogger('c2.pas.aal2.utils.webauthn')


def create_registration_options(user_id, username, display_name, rp_id, rp_name,
                                  exclude_credentials=None, authenticator_attachment=None):
    """
    Generate WebAuthn registration options (PublicKeyCredentialCreationOptions).

    Args:
        user_id (str): User ID (will be converted to bytes)
        username (str): Username/email
        display_name (str): User's display name
        rp_id (str): Relying Party ID (domain)
        rp_name (str): Relying Party name
        exclude_credentials (list): List of existing credentials to exclude
        authenticator_attachment (str): "platform", "cross-platform", or None

    Returns:
        dict: Registration options suitable for JSON serialization
    """
    try:
        # Convert user_id to bytes
        user_id_bytes = user_id.encode('utf-8') if isinstance(user_id, str) else user_id

        # Convert exclude_credentials to proper format
        exclude_creds = []
        if exclude_credentials:
            for cred in exclude_credentials:
                exclude_creds.append(
                    PublicKeyCredentialDescriptor(
                        id=cred.get('id', cred.get('credential_id')),
                        transports=cred.get('transports', [])
                    )
                )

        # Set authenticator selection criteria
        authenticator_selection = None
        if authenticator_attachment:
            authenticator_selection = AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment(authenticator_attachment),
                user_verification=UserVerificationRequirement.PREFERRED,
            )

        # Generate options
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=user_id_bytes,
            user_name=username,
            user_display_name=display_name,
            exclude_credentials=exclude_creds,
            authenticator_selection=authenticator_selection,
            attestation=AttestationConveyancePreference.NONE,  # Privacy-friendly
            timeout=60000,  # 60 seconds
        )

        logger.info(f"Generated registration options for user {username}")
        return options

    except Exception as e:
        logger.error(f"Failed to create registration options: {e}", exc_info=True)
        raise


def verify_registration(credential, expected_challenge, expected_origin, expected_rp_id):
    """
    Verify a WebAuthn registration response from the client.

    Args:
        credential (dict): PublicKeyCredential from browser
        expected_challenge (bytes): Challenge that was sent to client
        expected_origin (str): Expected origin (https://example.com)
        expected_rp_id (str): Expected RP ID (example.com)

    Returns:
        VerifiedRegistration: Verification result with credential data
    """
    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=expected_origin,
            expected_rp_id=expected_rp_id,
        )

        logger.info("Successfully verified registration")
        return verification

    except Exception as e:
        logger.error(f"Registration verification failed: {e}", exc_info=True)
        raise


def create_authentication_options(rp_id, allow_credentials=None, user_verification="preferred"):
    """
    Generate WebAuthn authentication options (PublicKeyCredentialRequestOptions).

    Args:
        rp_id (str): Relying Party ID (domain)
        allow_credentials (list): List of acceptable credentials (optional)
        user_verification (str): "required", "preferred", or "discouraged"

    Returns:
        dict: Authentication options suitable for JSON serialization
    """
    try:
        # Convert allow_credentials to proper format
        allowed_creds = []
        if allow_credentials:
            for cred in allow_credentials:
                # Convert transport strings to AuthenticatorTransport enums
                transports = []
                for transport in cred.get('transports', []):
                    try:
                        if isinstance(transport, str):
                            transports.append(AuthenticatorTransport(transport))
                        else:
                            transports.append(transport)
                    except ValueError:
                        # Skip invalid transport values
                        logger.warning(f"Invalid transport value: {transport}")
                        continue

                allowed_creds.append(
                    PublicKeyCredentialDescriptor(
                        id=cred.get('id', cred.get('credential_id')),
                        transports=transports if transports else None
                    )
                )

        # Generate options
        options = generate_authentication_options(
            rp_id=rp_id,
            allow_credentials=allowed_creds if allowed_creds else None,
            user_verification=UserVerificationRequirement(user_verification),
            timeout=60000,  # 60 seconds
        )

        logger.info(f"Generated authentication options for RP {rp_id}")
        return options

    except Exception as e:
        logger.error(f"Failed to create authentication options: {e}", exc_info=True)
        raise


def verify_authentication(credential, expected_challenge, expected_origin, expected_rp_id,
                           credential_public_key, credential_current_sign_count):
    """
    Verify a WebAuthn authentication response (assertion) from the client.

    Args:
        credential (dict): PublicKeyCredential from browser
        expected_challenge (bytes): Challenge that was sent to client
        expected_origin (str): Expected origin (https://example.com)
        expected_rp_id (str): Expected RP ID (example.com)
        credential_public_key (bytes): Stored public key for this credential
        credential_current_sign_count (int): Stored sign count for replay protection

    Returns:
        VerifiedAuthentication: Verification result with new sign count
    """
    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_origin=expected_origin,
            expected_rp_id=expected_rp_id,
            credential_public_key=credential_public_key,
            credential_current_sign_count=credential_current_sign_count,
        )

        logger.info("Successfully verified authentication")
        return verification

    except Exception as e:
        logger.error(f"Authentication verification failed: {e}", exc_info=True)
        raise


def validate_sign_count(old_count, new_count):
    """
    Validate sign_count increment for replay protection.

    Args:
        old_count (int): Previous sign count
        new_count (int): New sign count from authentication

    Returns:
        bool: True if valid, False if potential replay attack
    """
    # Handle counter wrap (very rare, after 2^32 authentications)
    if new_count == 0 and old_count > (2**32 - 1000):
        logger.warning(f"Sign count wrapped: old={old_count}, new={new_count}")
        return True  # Likely counter wrap

    # Normal case: new count must be greater
    if new_count > old_count:
        return True

    logger.error(f"Sign count validation failed: old={old_count}, new={new_count} (potential replay attack)")
    return False
