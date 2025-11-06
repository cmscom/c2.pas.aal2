# Tests for c2.pas.aal2

This directory contains the test suite for the c2.pas.aal2 Plone PAS AAL2 authentication plugin template.

## Test Structure

The tests are organized to validate different aspects of the plugin:

### Core Tests

- **test_import.py**: Package import and structure tests
  - Verifies that the package can be imported
  - Checks that key classes and interfaces are accessible
  - Ensures proper namespace package structure

- **test_plugin_registration.py**: PAS plugin registration tests
  - Validates that AAL2Plugin implements required PAS interfaces
  - Checks that plugin attributes are properly set
  - Verifies Zope interface compliance

- **test_stub_methods.py**: Stub method functionality tests
  - Tests that stub methods are callable without errors
  - Verifies that stubs return expected neutral values
  - Ensures stubs don't interfere with existing authentication

### Test Configuration

- **conftest.py**: Pytest fixtures and configuration
  - Provides reusable test fixtures (plugin instances, mock requests, etc.)
  - Can be extended with additional fixtures as implementation grows

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_import.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=c2.pas.aal2 --cov-report=term-missing
```

### Run with Coverage HTML Report

```bash
pytest tests/ --cov=c2.pas.aal2 --cov-report=html
open htmlcov/index.html
```

## Test Requirements

Tests require the following packages (automatically installed with `pip install -e ".[test]"`):

- pytest
- pytest-cov

## Writing New Tests

### Using Fixtures

The `conftest.py` file provides several useful fixtures:

```python
def test_example(aal2_plugin, mock_request):
    """Example test using fixtures."""
    credentials = aal2_plugin.extractCredentials(mock_request)
    assert isinstance(credentials, dict)
```

### Test Organization

When adding new tests:

1. **Group related tests** in the same file
2. **Use descriptive test names** that explain what is being tested
3. **Add docstrings** to explain test purpose and expected behavior
4. **Use fixtures** from conftest.py for common test objects
5. **Keep tests independent** - each test should be able to run in isolation

### Example Test Structure

```python
# -*- coding: utf-8 -*-
"""Test AAL2 level detection."""

import pytest


def test_basic_aal_level(aal2_plugin):
    """Test that get_aal_level returns an integer."""
    level = aal2_plugin.get_aal_level('test_user')
    assert isinstance(level, int)
    assert 1 <= level <= 3


def test_aal2_requirement_check(aal2_plugin):
    """Test that require_aal2 returns a boolean."""
    class MockContext:
        pass

    result = aal2_plugin.require_aal2('test_user', MockContext())
    assert isinstance(result, bool)
```

## Future Test Areas

As the implementation grows, consider adding tests for:

### AAL2 Authentication Logic
- **test_aal2_authentication.py**: Test actual AAL2 authentication flows
  - 2FA verification
  - Step-up authentication
  - Session AAL level tracking

### Policy Enforcement
- **test_aal2_policies.py**: Test AAL2 policy enforcement
  - Content-level AAL requirements
  - User AAL level validation
  - Access control integration

### Session Management
- **test_session_management.py**: Test AAL session handling
  - Session creation with AAL level
  - Session expiration
  - AAL level persistence

### Integration Tests
- **test_plone_integration.py**: Test integration with Plone
  - Plugin registration in acl_users
  - Interaction with other PAS plugins
  - GenericSetup profile installation

### Performance Tests
- **test_performance.py**: Test performance characteristics
  - Credential extraction speed
  - Authentication overhead
  - Caching effectiveness

## Test Coverage Goals

- **Current Coverage**: ~100% (stub implementation)
- **Target Coverage**: ≥90% for production implementation
- **Critical Paths**: 100% coverage for authentication and policy enforcement

## Continuous Integration

Tests should be run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -e ".[test]"
    pytest tests/ --cov=c2.pas.aal2 --cov-report=xml
```

## Debugging Tests

### Run with Verbose Output

```bash
pytest tests/ -vv
```

### Run with Print Statements

```bash
pytest tests/ -s
```

### Run Specific Test

```bash
pytest tests/test_import.py::test_import_package -v
```

### Drop into Debugger on Failure

```bash
pytest tests/ --pdb
```

## Test Best Practices

1. **Test one thing at a time** - Each test should validate a single behavior
2. **Use meaningful assertions** - Make it clear what is being validated
3. **Avoid test interdependencies** - Tests should not rely on execution order
4. **Clean up after tests** - Use fixtures and teardown to maintain clean state
5. **Mock external dependencies** - Don't rely on external services or databases
6. **Document test purpose** - Add docstrings explaining what and why

## Contributing Tests

When contributing new tests:

1. Ensure all existing tests still pass
2. Add tests for new functionality
3. Maintain or improve code coverage
4. Follow the existing test structure and naming conventions
5. Update this README if adding new test categories

## Questions or Issues

If you encounter issues with tests:

1. Check that dependencies are installed: `pip install -e ".[test]"`
2. Verify Python version: `python --version` (should be 3.11+)
3. Review test output for specific error messages
4. Check conftest.py for fixture definitions

For additional help, refer to:
- Pytest documentation: https://docs.pytest.org/
- Plone testing guide: https://docs.plone.org/develop/testing/
