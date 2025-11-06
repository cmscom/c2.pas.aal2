# -*- coding: utf-8 -*-
"""Test stub methods of AAL2Plugin."""

import pytest


def test_authenticate_credentials_callable():
    """Verify that authenticateCredentials method exists and is callable."""
    from c2.pas.aal2.plugin import AAL2Plugin

    plugin = AAL2Plugin('test_plugin')

    # Verify method exists and is callable
    assert hasattr(plugin, 'authenticateCredentials')
    assert callable(plugin.authenticateCredentials)

    # Call stub method - should not raise exception
    try:
        result = plugin.authenticateCredentials({'login': 'test', 'password': 'test'})
        # Stub implementation should return None
        assert result is None
    except Exception as e:
        pytest.fail(f"authenticateCredentials raised an exception: {e}")


def test_extract_credentials_callable():
    """Verify that extractCredentials method exists and is callable."""
    from c2.pas.aal2.plugin import AAL2Plugin

    plugin = AAL2Plugin('test_plugin')

    # Verify method exists and is callable
    assert hasattr(plugin, 'extractCredentials')
    assert callable(plugin.extractCredentials)

    # Call stub method - should not raise exception
    try:
        # Create a mock request object
        class MockRequest:
            pass

        request = MockRequest()
        result = plugin.extractCredentials(request)

        # Stub implementation should return empty dict
        assert isinstance(result, dict)
        assert len(result) == 0
    except Exception as e:
        pytest.fail(f"extractCredentials raised an exception: {e}")


def test_stub_methods_dont_affect_authentication():
    """Verify that stub methods don't interfere with normal authentication flow."""
    from c2.pas.aal2.plugin import AAL2Plugin

    plugin = AAL2Plugin('test_plugin')

    # Stub methods should return neutral values
    assert plugin.authenticateCredentials({'login': 'user', 'password': 'pass'}) is None

    class MockRequest:
        pass

    assert plugin.extractCredentials(MockRequest()) == {}
