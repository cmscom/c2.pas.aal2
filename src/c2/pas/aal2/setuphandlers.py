# -*- coding: utf-8 -*-
"""Setup handlers for c2.pas.aal2 installation and uninstallation."""

import logging
from Products.CMFCore.utils import getToolByName
from zope.interface import implementer
from Products.CMFPlone.interfaces import INonInstallable

logger = logging.getLogger('c2.pas.aal2.setuphandlers')


@implementer(INonInstallable)
class HiddenProfiles:
    """Hidden profiles that should not show up in the add-ons control panel."""

    def getNonInstallableProfiles(self):
        """Hide uninstall profile from being installed directly.

        Returns:
            list: Profile IDs that should not be installable
        """
        return [
            'c2.pas.aal2:uninstall',
        ]

    def getNonInstallableProducts(self):
        """Hide products that should not show up in quickinstaller.

        Returns:
            list: Product names
        """
        return []


def post_install(context):
    """Post install script.

    Args:
        context: Portal setup context
    """
    if context.readDataFile('c2.pas.aal2_default.txt') is None:
        return

    logger.info("c2.pas.aal2 installed successfully")


def uninstall(context):
    """Uninstall script.

    Args:
        context: Portal setup context
    """
    if context.readDataFile('c2.pas.aal2_uninstall.txt') is None:
        return

    portal = context.getSite()

    # Remove PAS plugin if it exists
    try:
        acl_users = getToolByName(portal, 'acl_users')
        if 'aal2_plugin' in acl_users.objectIds():
            acl_users.manage_delObjects(['aal2_plugin'])
            logger.info("Removed aal2_plugin from PAS")
    except Exception as e:
        logger.warning(f"Could not remove aal2_plugin: {e}")

    # Note: We intentionally do NOT delete audit logs on uninstall
    # to preserve audit trail. Admins can manually delete if needed.

    logger.info("c2.pas.aal2 uninstalled successfully")


def post_uninstall(context):
    """Post uninstall script.

    Args:
        context: Portal setup context
    """
    logger.info("c2.pas.aal2 post-uninstall completed")
