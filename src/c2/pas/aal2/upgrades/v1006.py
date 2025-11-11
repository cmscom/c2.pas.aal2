# -*- coding: utf-8 -*-
"""Upgrade to version 1006 - Add AAL2 Admin Protection control panel."""

import logging
from plone import api

logger = logging.getLogger('c2.pas.aal2.upgrades')


def upgrade_to_1006(context):
    """Upgrade to version 1006.

    This upgrade step ensures the AAL2 Admin Protection control panel
    is properly registered.

    Steps:
    1. Re-import controlpanel.xml
    2. Re-import registry.xml for AAL2 admin settings
    """
    logger.info("Starting upgrade to version 1006")

    setup = api.portal.get_tool('portal_setup')

    # Re-import control panel configuration
    logger.info("Re-importing control panel configuration")
    setup.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'controlpanel',
        run_dependencies=False,
        purge_old=False
    )

    # Re-import registry settings
    logger.info("Re-importing registry settings")
    setup.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'plone.app.registry',
        run_dependencies=False,
        purge_old=False
    )

    logger.info("Upgrade to version 1006 completed successfully")
