# -*- coding: utf-8 -*-
"""Control panel interfaces for c2.pas.aal2."""

from zope import schema
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class IC2PASAAL2Layer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IAAL2ControlPanel(Interface):
    """Control panel schema for AAL2 settings.

    This interface defines the configuration options available in the
    AAL2 Settings control panel, including admin protection settings.
    """

    # Admin Protection Settings (Feature 006: US2)

    admin_protection_enabled = schema.Bool(
        title="Enable Admin Protection",
        description=(
            "When enabled, administrative interfaces require AAL2 "
            "re-authentication within the configured time window. "
            "Disable this to allow admin access without recent passkey authentication."
        ),
        default=True,
        required=False,
    )

    admin_protected_patterns = schema.List(
        title="Protected URL Patterns",
        description=(
            "List of URL patterns (glob-style) that require AAL2 protection. "
            "Patterns use wildcards: * matches any characters, ? matches one character. "
            "Example: */@@overview-controlpanel protects the main control panel."
        ),
        value_type=schema.TextLine(),
        default=[
            '*/@@overview-controlpanel',
            '*/@@usergroup-userprefs',
            '*/@@usergroup-groupprefs',
            '*/@@security-controlpanel',
            '*/@@aal2-settings',
            '*/acl_users/manage*',
            '*/manage_main',
        ],
        required=False,
    )

    aal2_session_lifetime = schema.Int(
        title="AAL2 Session Lifetime (minutes)",
        description=(
            "Time window (in minutes) during which AAL2 authentication is valid. "
            "After this period expires, users must re-authenticate with their passkey "
            "to access protected administrative interfaces. Default: 15 minutes."
        ),
        default=15,
        min=1,
        max=120,
        required=True,
    )

    # Pattern Testing (for UI feedback)
    test_url = schema.TextLine(
        title="Test URL",
        description=(
            "Enter a URL to test if it matches any protected pattern. "
            "This helps verify your pattern configuration."
        ),
        required=False,
    )
