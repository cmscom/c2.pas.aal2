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

    portal = context.getSite()

    # Install PAS plugin
    install_pas_plugin(portal)

    logger.info("c2.pas.aal2 installed successfully")


def install_pas_plugin(portal):
    """Install and activate the AAL2 PAS plugin.

    Args:
        portal: Plone site object
    """
    from c2.pas.aal2.plugin import AAL2Plugin
    from Products.PluggableAuthService.interfaces.plugins import (
        IAuthenticationPlugin,
        IExtractionPlugin,
        IChallengePlugin,
        ICredentialsResetPlugin,
    )

    acl_users = portal.acl_users
    plugin_id = 'aal2_plugin'

    # Check if plugin already exists
    if plugin_id in acl_users.objectIds():
        logger.info(f"PAS plugin '{plugin_id}' already exists")
        return

    # Create plugin
    plugin = AAL2Plugin(plugin_id, 'AAL2 Authentication Plugin')
    acl_users._setObject(plugin_id, plugin)
    plugin = acl_users[plugin_id]

    # Activate plugin for required interfaces
    plugins = acl_users.plugins

    interfaces_to_activate = [
        IAuthenticationPlugin,
        IExtractionPlugin,
        IChallengePlugin,
        ICredentialsResetPlugin,
    ]

    for interface in interfaces_to_activate:
        if plugin_id not in plugins.listPluginIds(interface):
            plugins.activatePlugin(interface, plugin_id)
            logger.info(f"Activated '{plugin_id}' for {interface.__name__}")

    logger.info(f"PAS plugin '{plugin_id}' installed and activated")


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
