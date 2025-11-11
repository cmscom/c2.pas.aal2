# -*- coding: utf-8 -*-
"""Registry schema interfaces for admin AAL2 protection."""

from zope.interface import Interface
from zope import schema


class IAAL2AdminSettings(Interface):
    """AAL2 admin protection settings registry schema."""

    protected_patterns = schema.List(
        title=u"Protected Admin URL Patterns",
        description=u"URL patterns requiring AAL2 authentication (glob syntax: */pattern)",
        value_type=schema.TextLine(),
        default=[
            '*/@@overview-controlpanel',
            '*/@@usergroup-userprefs',
            '*/@@usergroup-groupprefs',
            '*/@@member-registration',
            '*/prefs_install_products_form',
            '*/@@installer',
            '*/@@security-controlpanel',
        ],
        required=False,
    )

    enabled = schema.Bool(
        title=u"Enable Admin AAL2 Protection",
        description=u"Require AAL2 re-authentication for admin interfaces",
        default=True,
    )
