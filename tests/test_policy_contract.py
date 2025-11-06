# -*- coding: utf-8 -*-
"""Contract tests for Policy API (c2.pas.aal2.policy).

Contract tests verify that the policy management module adheres to its
documented API contracts, including:
- Function signatures and return types
- Error handling behavior
- Content and role-based policy interaction
- Access control decision guarantees
- URL generation contracts

These tests complement unit tests by focusing on API contracts rather than
implementation details.
"""

import pytest


class TestPolicyAPIContract:
    """Test that Policy API functions follow their documented contracts."""

    def test_is_aal2_required_signature(self, mocker):
        """Test is_aal2_required function signature and return type."""
        from c2.pas.aal2.policy import is_aal2_required

        # Create mock content
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)

        content._annotations_adapter = AnnotationsAdapter(annotations)
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=content._annotations_adapter)

        # Test with required argument only (context)
        result = is_aal2_required(content)
        assert isinstance(result, bool)

        # Test with optional user argument
        user = mocker.Mock()
        user.getRoles.return_value = ['Member']
        result = is_aal2_required(content, user=user)
        assert isinstance(result, bool)

    def test_set_aal2_required_signature(self, mocker):
        """Test set_aal2_required function signature and return type."""
        from c2.pas.aal2.policy import set_aal2_required

        # Create mock content
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)
            def __setitem__(self, k, v):
                self.storage[k] = v

        content._annotations_adapter = AnnotationsAdapter(annotations)
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=content._annotations_adapter)

        # Test with required=True
        result = set_aal2_required(content, required=True)
        assert result is None  # Should return None

        # Test with required=False
        result = set_aal2_required(content, required=False)
        assert result is None  # Should return None

    def test_check_aal2_access_signature(self, mocker):
        """Test check_aal2_access function signature and return type."""
        from c2.pas.aal2.policy import check_aal2_access

        # Create mocks
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        user = mocker.Mock()
        user.getId.return_value = 'test_user'
        user.getRoles.return_value = ['Member']

        request = mocker.Mock()

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)
            def __contains__(self, k):
                return k in self.storage

        content._annotations_adapter = AnnotationsAdapter(annotations)
        user._annotations_adapter = AnnotationsAdapter({})

        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Test return type
        result = check_aal2_access(content, user, request)
        assert isinstance(result, bool)

    def test_get_stepup_challenge_url_signature(self, mocker):
        """Test get_stepup_challenge_url function signature and return type."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Create mocks
        content = mocker.Mock()
        content.absolute_url.return_value = 'http://localhost:8080/Plone/content'

        # Mock portal_url
        portal = mocker.Mock()
        portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        content.portal_url.getPortalObject.return_value = portal

        request = mocker.Mock()

        # Test return type
        result = get_stepup_challenge_url(content, request)
        assert isinstance(result, str)
        assert result.startswith('http')
        assert '@@aal2-challenge' in result


class TestPolicyAPIStateManagement:
    """Test state management guarantees of Policy API."""

    def test_set_then_check_consistency(self, mocker):
        """Test that set_aal2_required followed by is_aal2_required is consistent."""
        from c2.pas.aal2.policy import set_aal2_required, is_aal2_required

        # Create mock content
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)
            def __setitem__(self, k, v):
                self.storage[k] = v

        content._annotations_adapter = AnnotationsAdapter(annotations)
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=content._annotations_adapter)

        # Set to True, then check
        set_aal2_required(content, required=True)
        assert is_aal2_required(content) is True

        # Set to False, then check
        set_aal2_required(content, required=False)
        assert is_aal2_required(content) is False

    def test_role_based_requirement_overrides_content(self, mocker):
        """Test that user role requirement takes precedence."""
        from c2.pas.aal2.policy import set_aal2_required, is_aal2_required

        # Create mock content (no AAL2 requirement)
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)
            def __setitem__(self, k, v):
                self.storage[k] = v

        content._annotations_adapter = AnnotationsAdapter(annotations)
        mocker.patch('c2.pas.aal2.policy.IAnnotations', return_value=content._annotations_adapter)

        # User with AAL2 Required User role
        user = mocker.Mock()
        user.getId.return_value = 'privileged_user'
        user.getRoles.return_value = ['Member', 'AAL2 Required User']

        # Content doesn't require AAL2
        set_aal2_required(content, required=False)
        assert is_aal2_required(content) is False

        # But is required for role user
        assert is_aal2_required(content, user=user) is True


class TestPolicyAPIErrorHandling:
    """Test error handling contracts of Policy API."""

    def test_is_aal2_required_with_none_context_fails_gracefully(self, mocker):
        """Test that is_aal2_required handles None context gracefully."""
        from c2.pas.aal2.policy import is_aal2_required

        # Mock IAnnotations to handle None
        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=TypeError("None context"))

        # Should not crash with None
        try:
            result = is_aal2_required(None)
            # Should fail closed (return False for safety)
            assert result is False
        except (TypeError, AttributeError):
            # Acceptable if it requires a valid context
            pass

    def test_check_aal2_access_handles_errors_gracefully(self, mocker):
        """Test that check_aal2_access handles errors gracefully with proper logging."""
        from c2.pas.aal2.policy import check_aal2_access

        # Create mocks that work initially but fail during AAL2 validity check
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        user = mocker.Mock()
        user.getId.return_value = 'test_user'
        user.getRoles.return_value = ['Member', 'AAL2 Required User']  # AAL2 required

        request = mocker.Mock()

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)

        content._annotations_adapter = AnnotationsAdapter(annotations)
        user._annotations_adapter = AnnotationsAdapter({})

        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)

        # Make is_aal2_valid raise an exception
        mocker.patch('c2.pas.aal2.policy.is_aal2_valid', side_effect=Exception("Test error"))

        # Should deny access on error (fail closed per line 138-141 of policy.py)
        result = check_aal2_access(content, user, request)
        assert result is False

    def test_get_stepup_challenge_url_has_fallback(self, mocker):
        """Test that get_stepup_challenge_url provides fallback URL on error."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Create mock that will fail to get portal URL
        content = mocker.Mock()
        content.absolute_url.side_effect = Exception("Test error")
        content.portal_url.side_effect = AttributeError("No portal_url")

        request = mocker.Mock()

        # Should return a fallback URL
        result = get_stepup_challenge_url(content, request)
        assert isinstance(result, str)
        assert '@@aal2-challenge' in result


class TestPolicyAPIAccessControl:
    """Test access control decision contracts."""

    def test_check_aal2_access_grants_when_not_required(self, mocker):
        """Test that access is granted when AAL2 is not required."""
        from c2.pas.aal2.policy import check_aal2_access

        # Create mocks
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        user = mocker.Mock()
        user.getId.return_value = 'test_user'
        user.getRoles.return_value = ['Member']

        request = mocker.Mock()

        # Mock annotations (no AAL2 requirement)
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)
            def __contains__(self, k):
                return k in self.storage

        content._annotations_adapter = AnnotationsAdapter(annotations)
        user._annotations_adapter = AnnotationsAdapter({})

        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Access should be granted
        result = check_aal2_access(content, user, request)
        assert result is True

    def test_check_aal2_access_denies_when_required_and_invalid(self, mocker):
        """Test that access is denied when AAL2 required but not valid."""
        from c2.pas.aal2.policy import check_aal2_access

        # Create mocks
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        user = mocker.Mock()
        user.getId.return_value = 'test_user'
        user.getRoles.return_value = ['Member', 'AAL2 Required User']  # Role requires AAL2

        request = mocker.Mock()

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)
            def __contains__(self, k):
                return k in self.storage

        content._annotations_adapter = AnnotationsAdapter(annotations)
        user._annotations_adapter = AnnotationsAdapter({})  # No AAL2 timestamp

        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Access should be denied
        result = check_aal2_access(content, user, request)
        assert result is False


class TestPolicyAPIURLGeneration:
    """Test URL generation contracts."""

    def test_get_stepup_challenge_url_includes_came_from(self, mocker):
        """Test that challenge URL includes came_from parameter."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Create mocks
        content = mocker.Mock()
        content_url = 'http://localhost:8080/Plone/sensitive-doc'
        content.absolute_url.return_value = content_url

        portal = mocker.Mock()
        portal.absolute_url.return_value = 'http://localhost:8080/Plone'
        content.portal_url.getPortalObject.return_value = portal

        request = mocker.Mock()

        # Get challenge URL
        result = get_stepup_challenge_url(content, request)

        # Should include came_from parameter
        assert 'came_from=' in result
        assert content_url in result

    def test_get_stepup_challenge_url_format(self, mocker):
        """Test that challenge URL has correct format."""
        from c2.pas.aal2.policy import get_stepup_challenge_url

        # Create mocks
        content = mocker.Mock()
        content.absolute_url.return_value = 'http://localhost:8080/Plone/content'

        portal = mocker.Mock()
        portal_url = 'http://localhost:8080/Plone'
        portal.absolute_url.return_value = portal_url
        content.portal_url.getPortalObject.return_value = portal

        request = mocker.Mock()

        # Get challenge URL
        result = get_stepup_challenge_url(content, request)

        # Should be a valid URL format
        assert result.startswith(portal_url)
        assert '@@aal2-challenge' in result
        assert '?' in result  # Should have query parameters


class TestPolicyAPIDocumentation:
    """Test that Policy API functions have proper documentation."""

    def test_all_public_functions_have_docstrings(self):
        """Test that all public functions have docstrings."""
        import c2.pas.aal2.policy as policy_module

        public_functions = [
            'is_aal2_required',
            'set_aal2_required',
            'check_aal2_access',
            'get_stepup_challenge_url',
            'get_aal2_status',
        ]

        for func_name in public_functions:
            func = getattr(policy_module, func_name)
            assert func.__doc__ is not None, f"{func_name} missing docstring"
            assert len(func.__doc__.strip()) > 0, f"{func_name} has empty docstring"

    def test_module_has_docstring(self):
        """Test that policy module has module-level docstring."""
        import c2.pas.aal2.policy as policy_module

        assert policy_module.__doc__ is not None
        assert len(policy_module.__doc__.strip()) > 0


class TestPolicyAPIConstants:
    """Test that Policy API constants are properly defined."""

    def test_aal2_policy_key_exists(self):
        """Test that AAL2_POLICY_KEY constant is defined."""
        from c2.pas.aal2.policy import AAL2_POLICY_KEY

        assert AAL2_POLICY_KEY is not None
        assert isinstance(AAL2_POLICY_KEY, str)
        assert len(AAL2_POLICY_KEY) > 0

    def test_aal2_policy_key_format(self):
        """Test that AAL2_POLICY_KEY follows annotation key conventions."""
        from c2.pas.aal2.policy import AAL2_POLICY_KEY

        # Should be a namespaced key (package.module.attribute)
        assert 'c2.pas.aal2' in AAL2_POLICY_KEY


class TestPolicyAPIIntegration:
    """Test policy API integration contracts."""

    def test_get_aal2_status_comprehensive_info(self, mocker):
        """Test that get_aal2_status returns comprehensive status information."""
        from c2.pas.aal2.policy import get_aal2_status

        # Create mocks
        content = mocker.Mock()
        content.getId.return_value = 'test_content'

        user = mocker.Mock()
        user.getId.return_value = 'test_user'
        user.getRoles.return_value = ['Member']

        # Mock annotations
        annotations = {}
        class AnnotationsAdapter:
            def __init__(self, storage):
                self.storage = storage
            def get(self, k, d=None):
                return self.storage.get(k, d)

        content._annotations_adapter = AnnotationsAdapter(annotations)
        user._annotations_adapter = AnnotationsAdapter({})

        def annotations_factory(obj):
            if hasattr(obj, '_annotations_adapter'):
                return obj._annotations_adapter
            return mocker.Mock()

        mocker.patch('c2.pas.aal2.policy.IAnnotations', side_effect=annotations_factory)
        mocker.patch('c2.pas.aal2.session.IAnnotations', side_effect=annotations_factory)

        # Get status
        status = get_aal2_status(content, user)

        # Should return dict with required keys
        assert isinstance(status, dict)
        assert 'required' in status
        assert 'valid' in status
        assert 'needs_challenge' in status

        # Values should be correct types
        assert isinstance(status['required'], bool)
        assert isinstance(status['valid'], bool)
        assert isinstance(status['needs_challenge'], bool)
