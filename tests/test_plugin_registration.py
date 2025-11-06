# -*- coding: utf-8 -*-
"""Test PAS plugin registration."""

import pytest
from zope.interface.verify import verifyClass
from Products.PluggableAuthService.interfaces.plugins import IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin


def test_plugin_implements_authentication_interface():
    """Verify that AAL2Plugin implements IAuthenticationPlugin."""
    from c2.pas.aal2.plugin import AAL2Plugin

    # Verify the class implements the interface correctly
    assert verifyClass(IAuthenticationPlugin, AAL2Plugin)


def test_plugin_implements_extraction_interface():
    """Verify that AAL2Plugin implements IExtractionPlugin."""
    from c2.pas.aal2.plugin import AAL2Plugin

    # Verify the class implements the interface correctly
    assert verifyClass(IExtractionPlugin, AAL2Plugin)


def test_plugin_has_required_attributes():
    """Verify that AAL2Plugin has required PAS plugin attributes."""
    from c2.pas.aal2.plugin import AAL2Plugin

    # Create an instance
    plugin = AAL2Plugin('test_plugin')

    # Check required attributes
    assert hasattr(plugin, 'id')
    assert hasattr(plugin, 'title')
    assert hasattr(plugin, 'meta_type')

    # Verify attribute values
    assert plugin.id == 'test_plugin'
    assert plugin.title is not None
    assert plugin.meta_type is not None
