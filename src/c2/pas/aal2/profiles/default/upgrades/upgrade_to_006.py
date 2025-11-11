# -*- coding: utf-8 -*-
"""Upgrade step to version 006 - Admin AAL2 Protection."""

import logging
from plone import api

logger = logging.getLogger('c2.pas.aal2.upgrades')


def upgrade_to_006(context):
    """Install AAL2 admin protection configuration.

    This upgrade step:
    - Imports registry.xml to create admin protection settings
    - No data migration needed (new feature, new configuration)
    """
    logger.info("Starting upgrade to version 006: Admin AAL2 Protection")

    # Import registry.xml to create settings
    setup = api.portal.get_tool('portal_setup')
    setup.runImportStepFromProfile(
        'profile-c2.pas.aal2:default',
        'plone.app.registry',
        run_dependencies=False,
    )

    logger.info("AAL2 admin protection settings installed successfully")
    logger.info("Upgrade to version 006 complete")
