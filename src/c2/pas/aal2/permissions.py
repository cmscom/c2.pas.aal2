# -*- coding: utf-8 -*-
"""AAL2 Permission definitions for c2.pas.aal2.

This module defines the custom permission required for AAL2 authentication
in Plone's CMFCore permission system.
"""

from Products.CMFCore.permissions import setDefaultRoles

# AAL2 Permission constant
RequireAAL2Authentication = 'Require AAL2 Authentication'

# Set default roles for the permission
# By default, only Managers can require AAL2 authentication
setDefaultRoles(RequireAAL2Authentication, ('Manager',))
