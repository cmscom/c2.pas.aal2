# -*- coding: utf-8 -*-
"""Test package import functionality."""

import pytest


def test_import_package():
    """Verify that c2.pas.aal2 package can be imported successfully."""
    try:
        import c2.pas.aal2
        assert c2.pas.aal2 is not None
    except ImportError as e:
        pytest.fail(f"Failed to import c2.pas.aal2: {e}")


def test_import_plugin_class():
    """Verify that AAL2Plugin class can be imported."""
    try:
        from c2.pas.aal2.plugin import AAL2Plugin
        assert AAL2Plugin is not None
    except ImportError as e:
        pytest.fail(f"Failed to import AAL2Plugin: {e}")


def test_import_interfaces():
    """Verify that IAAL2Plugin interface can be imported."""
    try:
        from c2.pas.aal2.interfaces import IAAL2Plugin
        assert IAAL2Plugin is not None
    except ImportError as e:
        pytest.fail(f"Failed to import IAAL2Plugin: {e}")
