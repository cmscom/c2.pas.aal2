# -*- coding: utf-8 -*-
"""
c2.pas.aal2 - Plone PAS AAL2 Authentication Plugin Template

This package provides a template for implementing AAL2 (Authenticator Assurance Level 2)
authentication support in Plone through the Pluggable Authentication Service (PAS).
"""

from c2.pas.aal2.plugin import AAL2Plugin
from c2.pas.aal2.interfaces import IAAL2Plugin

__all__ = [
    'AAL2Plugin',
    'IAAL2Plugin',
]
