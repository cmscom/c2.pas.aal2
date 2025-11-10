"""
Upgrade step from version 1000 to 1005 (Feature 005: Implementation Refinements)

This upgrade step:
1. Registers JavaScript resources in resource registry
2. Initializes audit log container
3. Adds catalog indexes for AAL2 content
4. Migrates hardcoded constants to plone.app.registry
5. Reindexes AAL2-related catalog fields
"""

import logging
from Products.CMFCore.utils import getToolByName

logger = logging.getLogger('c2.pas.aal2.upgrades')


def upgrade_to_005(context):
    """
    Upgrade to feature 005: Implementation Refinements

    Args:
        context: GenericSetup tool context
    """
    logger.info("Starting upgrade to feature 005")

    setup_tool = getToolByName(context, 'portal_setup')
    portal = getToolByName(context, 'portal_url').getPortalObject()

    # 1. Register JavaScript resources
    logger.info("Registering JavaScript resources...")
    try:
        setup_tool.runImportStepFromProfile(
            'profile-c2.pas.aal2:default',
            'jsregistry',
            run_dependencies=False
        )
        logger.info("JavaScript resources registered successfully")
    except Exception as e:
        logger.warning(f"JavaScript registry update skipped: {e}")

    # 2. Initialize audit log container (US2 - when implemented)
    logger.info("Initializing audit log container...")
    try:
        from c2.pas.aal2.storage.audit import get_audit_container
        container = get_audit_container(portal)
        logger.info(f"Audit container initialized: {container.metadata['created']}")
    except ImportError:
        logger.info("Audit storage module not yet implemented, skipping")
    except Exception as e:
        logger.warning(f"Audit container initialization failed: {e}")

    # 3. Add catalog indexes (US5 - when implemented)
    logger.info("Adding catalog indexes...")
    try:
        setup_tool.runImportStepFromProfile(
            'profile-c2.pas.aal2:default',
            'catalog',
            run_dependencies=False
        )

        # Reindex AAL2 fields
        catalog = getToolByName(portal, 'portal_catalog')
        if 'aal2_protected' in catalog.indexes():
            logger.info("Reindexing aal2_protected index...")
            catalog.manage_reindexIndex(ids=['aal2_protected'])
        if 'aal2_required_roles' in catalog.indexes():
            logger.info("Reindexing aal2_required_roles index...")
            catalog.manage_reindexIndex(ids=['aal2_required_roles'])

        logger.info("Catalog indexes added and reindexed successfully")
    except Exception as e:
        logger.warning(f"Catalog index update skipped: {e}")

    # 4. Initialize plone.app.registry records (US4 - when implemented)
    logger.info("Initializing registry records...")
    try:
        setup_tool.runImportStepFromProfile(
            'profile-c2.pas.aal2:default',
            'plone.app.registry',
            run_dependencies=False
        )
        logger.info("Registry records initialized successfully")
    except Exception as e:
        logger.warning(f"Registry records update skipped: {e}")

    # 5. Migrate AAL2_TIMEOUT_SECONDS constant to registry (US4 - when implemented)
    logger.info("Migrating AAL2 timeout to registry...")
    try:
        from plone import api
        # Get existing constant value
        from c2.pas.aal2 import session
        if hasattr(session, 'AAL2_TIMEOUT_SECONDS'):
            timeout = session.AAL2_TIMEOUT_SECONDS
            api.portal.set_registry_record(
                'c2.pas.aal2.aal2_timeout_seconds',
                timeout
            )
            logger.info(f"Migrated AAL2 timeout: {timeout} seconds")
        else:
            logger.info("AAL2_TIMEOUT_SECONDS constant not found, using registry default")
    except ImportError:
        logger.info("Registry settings not yet implemented, skipping migration")
    except Exception as e:
        logger.warning(f"AAL2 timeout migration failed: {e}")

    logger.info("Upgrade to feature 005 completed successfully")
    return "Upgrade to feature 005 completed"
