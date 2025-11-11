# -*- coding: utf-8 -*-
"""Upgrade to version 1007 - Fix registry key names."""

import logging
from plone import api

logger = logging.getLogger('c2.pas.aal2.upgrades')


def upgrade_to_1007(context):
    """Upgrade to version 1007.

    This upgrade step fixes registry key naming inconsistency.
    It ensures the control panel and protection logic use the same keys.

    Steps:
    1. Re-import registry.xml to use unified keys
    2. Migrate old registry values if they exist
    """
    logger.info("Starting upgrade to version 1007")

    setup = api.portal.get_tool('portal_setup')
    registry = api.portal.get_tool('portal_registry')

    # Try to migrate old values to new keys
    try:
        old_enabled_key = 'c2.pas.aal2.admin.enabled'
        new_enabled_key = 'c2.pas.aal2.admin_protection_enabled'

        if old_enabled_key in registry.records:
            old_value = registry.records[old_enabled_key].value
            logger.info(f"Migrating {old_enabled_key} = {old_value} to {new_enabled_key}")
            if new_enabled_key in registry.records:
                registry.records[new_enabled_key].value = old_value
            # Remove old key
            del registry.records[old_enabled_key]
    except Exception as e:
        logger.warning(f"Could not migrate old enabled setting: {e}")

    try:
        old_patterns_key = 'c2.pas.aal2.admin.protected_patterns'
        new_patterns_key = 'c2.pas.aal2.admin_protected_patterns'

        if old_patterns_key in registry.records:
            old_value = registry.records[old_patterns_key].value
            logger.info(f"Migrating {old_patterns_key} to {new_patterns_key}")
            if new_patterns_key in registry.records:
                registry.records[new_patterns_key].value = old_value
            # Remove old key
            del registry.records[old_patterns_key]
    except Exception as e:
        logger.warning(f"Could not migrate old patterns setting: {e}")

    # Re-import registry settings to ensure new keys exist
    logger.info("Re-importing registry settings")
    setup.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'plone.app.registry',
        run_dependencies=False,
        purge_old=False
    )

    logger.info("Upgrade to version 1007 completed successfully")
