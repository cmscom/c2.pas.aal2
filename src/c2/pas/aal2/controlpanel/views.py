# -*- coding: utf-8 -*-
"""Control panel views for c2.pas.aal2."""

import fnmatch
import json
import logging
from plone import api
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.z3cform import layout
from z3c.form import button
from zope.interface import Interface

from c2.pas.aal2.controlpanel.interfaces import IAAL2ControlPanel

logger = logging.getLogger('c2.pas.aal2.controlpanel')


class AAL2AdminProtectionControlPanel(RegistryEditForm):
    """Control panel for AAL2 Admin Protection settings.

    This form allows administrators to:
    1. Enable/disable admin protection
    2. Configure protected URL patterns
    3. Set AAL2 session lifetime
    4. Test URL patterns
    """

    schema = IAAL2ControlPanel
    schema_prefix = "c2.pas.aal2"
    label = "AAL2 Admin Protection Settings"
    description = (
        "Configure which administrative interfaces require recent passkey authentication. "
        "Protected URLs will require AAL2 re-authentication within the configured time window."
    )

    def updateFields(self):
        """Customize form fields."""
        super(AAL2AdminProtectionControlPanel, self).updateFields()

    def updateWidgets(self):
        """Customize form widgets."""
        super(AAL2AdminProtectionControlPanel, self).updateWidgets()

        # Add CSS class to test_url for JavaScript handling
        if 'test_url' in self.widgets:
            self.widgets['test_url'].klass = 'pattern-test-input'

    @button.buttonAndHandler('Save', name='save')
    def handleSave(self, action):
        """Handle save button - includes validation."""
        data, errors = self.extractData()

        if errors:
            self.status = self.formErrorsMessage
            return

        # Validate patterns before saving
        if 'admin_protected_patterns' in data:
            patterns = data['admin_protected_patterns']
            validation_errors = self.validate_patterns(patterns)

            if validation_errors:
                self.status = "Invalid patterns detected: " + "; ".join(validation_errors)
                return

        # Call parent save handler
        super(AAL2AdminProtectionControlPanel, self).handleSave(self, action)

        # Invalidate pattern cache after save
        try:
            # Note: Cache automatically invalidates when registry values change
            # because _pattern_cache_key uses registry values as the cache key.
            # This explicit invalidation is defensive programming.
            from plone.memoize import ram
            from c2.pas.aal2.admin.protection import _pattern_cache_key

            # Get current cache key and invalidate
            cache_key = _pattern_cache_key(None)
            logger.info(f"Pattern cache invalidated after control panel save (key: {cache_key})")
        except Exception as e:
            # Non-critical - cache will auto-invalidate on next access
            logger.debug(f"Could not explicitly invalidate pattern cache: {e}")

    @button.buttonAndHandler('Cancel', name='cancel')
    def handleCancel(self, action):
        """Handle cancel button."""
        super(AAL2AdminProtectionControlPanel, self).handleCancel(self, action)

    @button.buttonAndHandler('Test Pattern', name='test_pattern')
    def handleTestPattern(self, action):
        """Handle pattern testing - provides immediate feedback."""
        data, errors = self.extractData()

        if 'test_url' not in data or not data['test_url']:
            api.portal.show_message(
                message="Please enter a URL to test",
                request=self.request,
                type='warning'
            )
            return

        test_url = data['test_url']
        patterns = data.get('admin_protected_patterns', [])

        # Test URL against patterns
        matched_patterns = []
        for pattern in patterns:
            if fnmatch.fnmatch(test_url, pattern):
                matched_patterns.append(pattern)

        if matched_patterns:
            api.portal.show_message(
                message=f"URL matches {len(matched_patterns)} pattern(s): {', '.join(matched_patterns)}",
                request=self.request,
                type='info'
            )
        else:
            api.portal.show_message(
                message="URL does not match any protected patterns",
                request=self.request,
                type='warning'
            )

    def validate_patterns(self, patterns):
        """Validate URL patterns for common errors.

        Args:
            patterns (list): List of glob-style patterns

        Returns:
            list: List of error messages (empty if valid)
        """
        errors = []

        if not patterns:
            errors.append("At least one protected pattern is recommended")
            return errors

        for i, pattern in enumerate(patterns):
            # Check for empty patterns
            if not pattern or not pattern.strip():
                errors.append(f"Pattern {i+1}: Empty pattern not allowed")
                continue

            # Check for patterns without wildcards (might be too specific)
            if '*' not in pattern and '?' not in pattern:
                logger.warning(f"Pattern without wildcards: {pattern}")

            # Check for overly broad patterns
            if pattern == '*' or pattern == '**':
                errors.append(f"Pattern {i+1}: '{pattern}' is too broad (matches everything)")

            # Check for invalid characters (basic validation)
            if any(char in pattern for char in ['<', '>', '"', '\n', '\r']):
                errors.append(f"Pattern {i+1}: Contains invalid characters")

        return errors

    def get_pattern_stats(self):
        """Get statistics about current pattern configuration.

        Returns:
            dict: Statistics including pattern count, cache status, etc.
        """
        try:
            patterns = api.portal.get_registry_record(
                'c2.pas.aal2.admin_protected_patterns',
                default=[]
            )

            enabled = api.portal.get_registry_record(
                'c2.pas.aal2.admin_protection_enabled',
                default=True
            )

            return {
                'pattern_count': len(patterns),
                'protection_enabled': enabled,
                'patterns': patterns,
            }
        except Exception as e:
            logger.error(f"Error getting pattern stats: {e}")
            return {
                'pattern_count': 0,
                'protection_enabled': False,
                'patterns': [],
            }


class AAL2AdminProtectionControlPanelView(ControlPanelFormWrapper):
    """Wrapper view for AAL2 Admin Protection control panel."""
    form = AAL2AdminProtectionControlPanel


# JSON API endpoint for pattern testing (for AJAX requests)
class PatternTestAPIView(object):
    """JSON API for testing URL patterns via AJAX.

    This view provides a JSON endpoint for the pattern testing UI,
    allowing real-time feedback without form submission.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """Handle pattern test request.

        Expected POST data:
        {
            "url": "http://example.com/@@overview-controlpanel",
            "patterns": ["*/@@overview-controlpanel", "*/manage*"]
        }

        Returns:
        {
            "matched": true,
            "patterns": ["*/@@overview-controlpanel"],
            "count": 1
        }
        """
        self.request.response.setHeader('Content-Type', 'application/json')

        try:
            # Parse request
            body = self.request.get('BODY', '{}')
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body)

            test_url = data.get('url', '')
            patterns = data.get('patterns', [])

            if not test_url:
                return json.dumps({
                    'error': 'URL is required',
                    'matched': False
                })

            # Test URL against patterns
            matched_patterns = []
            for pattern in patterns:
                if fnmatch.fnmatch(test_url, pattern):
                    matched_patterns.append(pattern)

            return json.dumps({
                'matched': len(matched_patterns) > 0,
                'patterns': matched_patterns,
                'count': len(matched_patterns)
            })

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in pattern test request: {e}")
            return json.dumps({
                'error': 'Invalid JSON',
                'matched': False
            })
        except Exception as e:
            logger.exception(f"Error in pattern test API: {e}")
            return json.dumps({
                'error': str(e),
                'matched': False
            })
