# -*- coding: utf-8 -*-
"""Pytest configuration and fixtures for c2.pas.aal2 tests.

This file provides common test fixtures and configuration for the test suite.
Future tests can add shared fixtures here for:
- Mock Plone environments
- Test users and credentials
- Sample content objects
- Mock HTTP requests
"""

import pytest


@pytest.fixture
def aal2_plugin():
    """Fixture providing an AAL2Plugin instance for testing.

    Returns:
        AAL2Plugin: A configured plugin instance with id 'test_plugin'

    Example usage:
        def test_something(aal2_plugin):
            result = aal2_plugin.get_aal_level('user123')
            assert result == 1
    """
    from c2.pas.aal2.plugin import AAL2Plugin
    return AAL2Plugin('test_plugin')


@pytest.fixture
def mock_request():
    """Fixture providing a mock HTTP request object.

    Returns:
        MockRequest: A simple mock request object for testing

    Example usage:
        def test_extraction(aal2_plugin, mock_request):
            creds = aal2_plugin.extractCredentials(mock_request)
            assert isinstance(creds, dict)
    """
    class MockRequest:
        """Mock HTTP request for testing credential extraction."""
        def __init__(self):
            self.form = {}
            self.cookies = {}
            self.headers = {}

    return MockRequest()


@pytest.fixture
def sample_credentials():
    """Fixture providing sample credential dictionaries for testing.

    Returns:
        dict: Sample credentials with login and password

    Example usage:
        def test_auth(aal2_plugin, sample_credentials):
            result = aal2_plugin.authenticateCredentials(sample_credentials)
            # Test the result
    """
    return {
        'login': 'testuser',
        'password': 'testpassword',
    }


# Additional fixtures can be added here as the implementation grows:
# - mock_plone_site: Mock Plone site object
# - mock_user: Mock user object with AAL level
# - mock_content: Mock content object with AAL2 policy
# - test_session: Mock session with authentication state
