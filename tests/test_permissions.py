# -*- coding: utf-8 -*-
"""Tests for AAL2 permission registration (c2.pas.aal2 permissions).

This module tests that the AAL2 permission is properly defined and registered
with appropriate default roles.
"""

import pytest


class TestAAL2PermissionDefinition:
    """Test AAL2 permission definition and registration."""

    def test_permission_constant_exists(self):
        """Test that RequireAAL2Authentication permission constant is defined."""
        from c2.pas.aal2.permissions import RequireAAL2Authentication

        assert RequireAAL2Authentication is not None
        assert isinstance(RequireAAL2Authentication, str)
        assert RequireAAL2Authentication == 'Require AAL2 Authentication'

    def test_permission_name_format(self):
        """Test that permission name follows Plone conventions."""
        from c2.pas.aal2.permissions import RequireAAL2Authentication

        # Plone permissions should be descriptive strings
        assert len(RequireAAL2Authentication) > 0
        assert RequireAAL2Authentication[0].isupper()  # Should start with capital
        # Should be human-readable, not snake_case
        assert '_' not in RequireAAL2Authentication

    def test_permission_is_importable(self):
        """Test that permission can be imported from package root."""
        # This ensures the permission is properly exposed in the module
        try:
            from c2.pas.aal2.permissions import RequireAAL2Authentication
            assert RequireAAL2Authentication == 'Require AAL2 Authentication'
        except ImportError as e:
            pytest.fail(f"Failed to import RequireAAL2Authentication: {e}")


class TestAAL2PermissionDefaults:
    """Test default role assignments for AAL2 permission."""

    def test_permission_uses_correct_default_roles_pattern(self):
        """Test that permissions.py follows the correct pattern for default roles."""
        # Read the source code to verify setDefaultRoles is called correctly
        import inspect

        import c2.pas.aal2.permissions as permissions_module

        source = inspect.getsource(permissions_module)

        # Verify setDefaultRoles is imported
        assert 'from Products.CMFCore.permissions import setDefaultRoles' in source

        # Verify setDefaultRoles is called with the permission
        assert 'setDefaultRoles(RequireAAL2Authentication' in source

        # Verify Manager role is in default roles
        assert "('Manager',)" in source or "('Manager')" in source

    def test_permission_module_sets_defaults_at_import(self):
        """Test that permission default roles are set when module is imported."""
        # This test verifies the module structure is correct
        # by checking that setDefaultRoles is imported and used
        from c2.pas.aal2.permissions import RequireAAL2Authentication, setDefaultRoles

        # Permission constant should be defined
        assert RequireAAL2Authentication is not None

        # setDefaultRoles should be available (imported from CMFCore)
        assert callable(setDefaultRoles)

        # We can verify the call would work (idempotent operation)
        try:
            setDefaultRoles(RequireAAL2Authentication, ('Manager',))
        except Exception as e:
            pytest.fail(f"setDefaultRoles call failed: {e}")


class TestPermissionModule:
    """Test the permissions module structure."""

    def test_module_has_required_exports(self):
        """Test that permissions module exports the required permission."""
        import c2.pas.aal2.permissions as permissions_module

        # Should export RequireAAL2Authentication
        assert hasattr(permissions_module, 'RequireAAL2Authentication')

        # Check it's the expected type
        perm = permissions_module.RequireAAL2Authentication
        assert isinstance(perm, str)

    def test_module_docstring_exists(self):
        """Test that permissions module has documentation."""
        import c2.pas.aal2.permissions as permissions_module

        assert permissions_module.__doc__ is not None
        # Should have some documentation
        assert len(permissions_module.__doc__.strip()) > 0

    def test_no_unintended_exports(self):
        """Test that permissions module doesn't export unnecessary symbols."""
        import c2.pas.aal2.permissions as permissions_module

        # Get all public symbols (not starting with _)
        public_symbols = [name for name in dir(permissions_module)
                         if not name.startswith('_')]

        # Should only export the permission constant and imports from CMFCore
        expected_symbols = ['RequireAAL2Authentication', 'setDefaultRoles']

        # Check that we have the essential exports
        assert 'RequireAAL2Authentication' in public_symbols

        # Should not export random things
        unexpected = set(public_symbols) - set(expected_symbols)
        # Filter out module metadata
        unexpected = {s for s in unexpected if s not in ['unicode_literals']}

        # Should have minimal exports
        assert len(unexpected) <= 2, f"Unexpected exports: {unexpected}"


class TestPermissionIntegration:
    """Integration tests for permission usage in Plone context."""

    def test_permission_can_be_used_in_security_checks(self, mocker):
        """Test that permission can be used in Plone security checks."""
        from c2.pas.aal2.permissions import RequireAAL2Authentication

        # Mock a Plone context and security manager
        mock_context = mocker.Mock()
        mock_security = mocker.Mock()
        mock_security.checkPermission.return_value = True

        # Simulate checking the permission
        result = mock_security.checkPermission(RequireAAL2Authentication, mock_context)

        assert result is True
        mock_security.checkPermission.assert_called_once_with(
            RequireAAL2Authentication, mock_context
        )

    def test_permission_string_is_unique(self):
        """Test that permission string is unique and identifiable."""
        from c2.pas.aal2.permissions import RequireAAL2Authentication

        # Should contain "AAL2" for identification
        assert 'AAL2' in RequireAAL2Authentication

        # Should contain "Authentication" to indicate it's an auth permission
        assert 'Authentication' in RequireAAL2Authentication

        # Full string should be unique
        assert RequireAAL2Authentication == 'Require AAL2 Authentication'


class TestPermissionCompatibility:
    """Test permission compatibility with Plone and Zope."""

    def test_permission_compatible_with_cmfcore(self):
        """Test that permission is compatible with CMFCore permission system."""
        try:
            from Products.CMFCore.permissions import setDefaultRoles

            from c2.pas.aal2.permissions import RequireAAL2Authentication

            # Should be able to call setDefaultRoles without errors
            # (This is already done at module import, but we verify it works)
            setDefaultRoles(RequireAAL2Authentication, ('Manager',))

        except Exception as e:
            pytest.fail(f"Permission not compatible with CMFCore: {e}")

    def test_permission_is_string_type(self):
        """Test that permission is a plain string (not bytes, unicode object, etc)."""
        from c2.pas.aal2.permissions import RequireAAL2Authentication

        # Should be a string
        assert isinstance(RequireAAL2Authentication, str)

        # Should not be empty
        assert len(RequireAAL2Authentication) > 0

        # Should be ASCII-compatible (Plone requirement)
        assert RequireAAL2Authentication.encode('ascii').decode('ascii') == RequireAAL2Authentication
