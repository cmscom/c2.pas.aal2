# Research: Implementation Refinements and Production Readiness

**Feature**: 005-implementation-refinements
**Date**: 2025-11-10
**Status**: Completed

## Overview

This document consolidates research findings for implementing production readiness refinements to the c2.pas.aal2 package. The research covers five main areas: JavaScript externalization, persistent audit logging, internationalization, control panel integration, and performance optimization.

---

## 1. JavaScript Externalization (P1)

### Decision: Use Plone Resource Registry with Manual Dependency Management

**Rationale**:
- Plone 5.2's resource registry provides built-in JavaScript bundling, minification, and caching
- Manual dependency management (load order) is simple for our 5-file structure
- Avoids complexity of external build tools (webpack, rollup) which Plone 5.2 doesn't natively support
- Cache busting handled automatically via resource registry versioning

**Implementation Approach**:
1. Create 5 separate .js files in `browser/static/js/`:
   - `webauthn-utils.js` (base utilities, loaded first)
   - `webauthn-register.js` (depends on utils)
   - `webauthn-login.js` (depends on utils)
   - `webauthn-aal2.js` (depends on utils)
   - `passkey-management.js` (depends on utils)

2. Register in `profiles/default/jsregistry.xml`:
```xml
<javascript id="++resource++c2.pas.aal2/js/webauthn-utils.js"
           cacheable="True" compression="safe" cookable="True"
           enabled="True" inline="False"/>
<!-- Repeat for each file with correct dependency order -->
```

3. Update templates to reference resources via `portal_javascripts` instead of inline `<script>` tags

**Alternatives Considered**:
- **Webpack/Rollup bundling**: Rejected - adds build complexity, Plone 5.2 doesn't integrate well with modern JS tooling
- **Single monolithic .js file**: Rejected - harder to maintain, all pages would load unnecessary code
- **AMD/RequireJS**: Rejected - outdated pattern, adds dependency management overhead

**Best Practices**:
- Keep utilities pure functions with no side effects
- Use initialization functions (init*) that templates call on DOMContentLoaded
- Add JSDoc comments for documentation
- Include error handling with friendly user messages

---

## 2. Persistent Audit Logging (P2)

### Decision: ZODB-based Storage with BTrees for Queries

**Rationale**:
- ZODB is already available and well-integrated with Plone
- No additional database setup required (lowers deployment complexity)
- BTrees provide O(log n) lookups for indexed queries
- Transactional consistency with ZODB's ACID guarantees
- Can migrate to SQL later if needed (abstraction layer in `storage/audit.py`)

**Implementation Approach**:
1. Create `AuditLogContainer` stored in portal annotations:
   - Uses `OOBTree` for timestamp-based index
   - Uses `IIBTree` for user_id-based index
   - Uses `OOBTree` for action_type-based index

2. Each `AuditEvent` object stores:
```python
{
    'timestamp': datetime (UTC),
    'user_id': str,
    'action_type': str (enum: registration_start, authentication_success, etc.),
    'outcome': str (success/failure),
    'ip_address': str,
    'user_agent': str,
    'metadata': dict (JSON-serializable action-specific data)
}
```

3. Query interface in `storage/query.py`:
   - `query_audit_logs(user_id=None, action_type=None, start_date=None, end_date=None, outcome=None)`
   - `export_audit_logs(format='csv' or 'json', filters={...})`
   - `cleanup_old_logs(retention_days=90)`

4. Update existing `utils/audit.py` to write to both Python logger AND persistent storage

**Alternatives Considered**:
- **PostgreSQL with SQLAlchemy**: Rejected for initial implementation - requires separate database setup, adds deployment complexity. Can be added later as optional enhancement.
- **Elasticsearch**: Rejected - overkill for audit logging, expensive to run
- **File-based logging**: Rejected - no structured querying, rotation/retention is manual

**Best Practices**:
- Never log sensitive data (passwords, tokens)
- Always use UTC timestamps
- Include correlation IDs for multi-step flows
- Graceful degradation: if audit storage fails, don't block auth operations
- Implement retention policy with automated cleanup

**ZODB Performance Considerations**:
- BTree indexes scale to millions of entries
- Queries limited to indexed fields for performance
- Batch queries return iterators, not full result sets
- Pack ZODB database periodically to reclaim space from deleted logs

---

## 3. Internationalization (P2)

### Decision: Plone's lingua + gettext Standard .po Files

**Rationale**:
- Plone has built-in i18n infrastructure (plone.i18n, plone.app.locales)
- lingua tool extracts translatable strings from Python and templates automatically
- .po files are industry standard (translators familiar with tools like Poedit)
- gettext provides runtime translation lookup with zero performance impact

**Implementation Approach**:
1. Create locale structure:
```
src/c2/pas/aal2/locales/
├── c2.pas.aal2.pot        # Template (generated by lingua)
├── en/LC_MESSAGES/c2.pas.aal2.po  # English (baseline)
├── ja/LC_MESSAGES/c2.pas.aal2.po  # Japanese
├── es/LC_MESSAGES/c2.pas.aal2.po  # Spanish
├── fr/LC_MESSAGES/c2.pas.aal2.po  # French
└── de/LC_MESSAGES/c2.pas.aal2.po  # German
```

2. Mark translatable strings:
   - Templates: `i18n:translate=""` attribute (already present)
   - Python: `from zope.i18nmessageid import MessageFactory; _ = MessageFactory('c2.pas.aal2')`
   - JavaScript: Use template-rendered strings or separate JS i18n mechanism

3. Extract strings: `bin/i18ndude rebuild-pot --pot src/c2/pas/aal2/locales/c2.pas.aal2.pot --create c2.pas.aal2 src/c2/pas/aal2`

4. Compile .po to .mo: `bin/i18ndude sync --pot src/c2/pas/aal2/locales/c2.pas.aal2.pot src/c2/pas/aal2/locales/*/LC_MESSAGES/*.po`

**Alternatives Considered**:
- **JSON-based i18n**: Rejected - not Plone standard, would bypass built-in i18n infrastructure
- **Hardcoded translations in Python**: Rejected - not maintainable, no translator tools
- **Machine translation only**: Rejected - requires human review for security-critical UI

**Best Practices**:
- Always provide context for translators (comments in .po files)
- Avoid string concatenation (use placeholders: "Hello {name}")
- Keep strings short and simple
- Test with pseudo-localization (extra-long strings) to catch UI layout issues

**Translation Strategy**:
- **English (en)**: Baseline, already written
- **Japanese (ja)**: Priority for this project (user requested Japanese UI)
- **Spanish (es)**: Large user base, common second language
- **French (fr)**: EU requirement for some deployments
- **German (de)**: EU requirement, large Plone community

---

## 4. Plone Control Panel Integration (P3)

### Decision: plone.app.registry with z3c.form Schema

**Rationale**:
- Standard Plone pattern for configuration UI
- Automatic form generation from zope.schema interface
- Registry storage is persistent and accessible globally
- Integrates with Plone's control panel UI automatically

**Implementation Approach**:
1. Define settings schema in `controlpanel/interfaces.py`:
```python
from zope.interface import Interface
from zope import schema

class IAAL2Settings(Interface):
    """AAL2 Security Settings"""

    aal2_timeout_seconds = schema.Int(
        title="AAL2 Session Timeout",
        description="Seconds before AAL2 re-authentication required",
        default=900,  # 15 minutes
        min=300,      # 5 minutes minimum
        max=3600      # 1 hour maximum
    )

    aal2_enabled = schema.Bool(
        title="Enable AAL2 Protection",
        description="Turn AAL2 enforcement on/off globally",
        default=True
    )

    audit_retention_days = schema.Int(
        title="Audit Log Retention",
        description="Days to retain audit logs before cleanup",
        default=90,
        min=30,
        max=365
    )
```

2. Create control panel view in `controlpanel/views.py`:
```python
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper

class AAL2SettingsEditForm(RegistryEditForm):
    schema = IAAL2Settings
    label = "AAL2 Security Settings"
```

3. Register in `profiles/default/controlpanel.xml`:
```xml
<object name="portal_controlpanel">
  <configlet title="AAL2 Settings" action_id="aal2settings"
             appId="c2.pas.aal2" category="Products"
             url_expr="string:${portal_url}/@@aal2-settings"
             icon_expr="string:$portal_url/++resource++c2.pas.aal2/icon.png">
    <permission>Manage portal</permission>
  </configlet>
</object>
```

**Alternatives Considered**:
- **Custom browser views only**: Rejected - doesn't integrate with Plone control panel, inconsistent UX
- **portal_properties**: Rejected - deprecated in Plone 5.x, use plone.app.registry instead
- **Environment variables**: Rejected - not user-friendly, requires restart to change

**Best Practices**:
- Validate all inputs (min/max for integers, regex for patterns)
- Provide helpful descriptions for each setting
- Group related settings together
- Add "Apply" button to preview changes before saving
- Show current effective settings (not just stored values)

---

## 5. Performance Optimization (P3)

### Decision: Catalog Indexes with FieldIndex and KeywordIndex

**Rationale**:
- Plone's ZCatalog provides O(log n) lookups vs. O(n) iteration
- FieldIndex for single-value fields (is_aal2_protected: True/False)
- KeywordIndex for multi-value fields (aal2_required_roles: list)
- Automatic indexing on content add/modify via event subscribers

**Implementation Approach**:
1. Define indexes in `catalog/indexes.py`:
```python
from plone.indexer import indexer
from Products.CMFCore.interfaces import IContentish

@indexer(IContentish)
def aal2_protected(object):
    """Index whether content requires AAL2 authentication"""
    from c2.pas.aal2.policy import is_aal2_required
    return is_aal2_required(object)

@indexer(IContentish)
def aal2_required_roles(object):
    """Index which roles require AAL2 for this content"""
    # Return list of role names
    return getattr(object, '__aal2_roles__', [])
```

2. Register indexes in `profiles/default/catalog.xml`:
```xml
<index name="aal2_protected" meta_type="FieldIndex">
  <indexed_attr value="aal2_protected"/>
</index>
<index name="aal2_required_roles" meta_type="KeywordIndex">
  <indexed_attr value="aal2_required_roles"/>
</index>
```

3. Update `policy.py` to use catalog queries:
```python
def list_aal2_protected_content():
    """List all AAL2-protected content using catalog"""
    catalog = getToolByName(portal, 'portal_catalog')
    brains = catalog(aal2_protected=True)
    return [brain.getObject() for brain in brains]
```

4. Add event subscribers to reindex on policy changes:
```python
@subscriber(IObjectModifiedEvent)
def reindex_aal2_on_change(obj, event):
    """Reindex AAL2 fields when policy changes"""
    obj.reindexObject(idxs=['aal2_protected', 'aal2_required_roles'])
```

**Alternatives Considered**:
- **External search (Solr, Elasticsearch)**: Rejected - overkill for this use case, adds infrastructure
- **SQL database**: Rejected - duplicates Plone catalog functionality
- **In-memory caching only**: Rejected - doesn't scale across Zope processes, lost on restart

**Best Practices**:
- Index only what you need to query
- Keep indexed values simple (booleans, integers, strings)
- Use indexers (@indexer decorator) for computed values
- Batch catalog queries for large result sets
- Clear catalog on uninstall to avoid orphaned indexes

**Caching Strategy**:
In addition to catalog indexes, implement:
- **RAM cache for policy lookups**: Cache `is_aal2_required(content)` for 60 seconds
- **Request-level cache**: Store AAL2 check results in request annotations to avoid redundant checks
- **Invalidation**: Clear cache on policy changes via event subscribers

---

## Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | Python | 3.11+ | Core implementation |
| Framework | Plone | 5.2+ | CMS platform |
| Auth | Products.PluggableAuthService | Included | Authentication framework |
| Storage | ZODB | Included | Primary data store |
| JavaScript | Vanilla JS + Plone Registry | ES6+ | Client-side WebAuthn |
| I18n | plone.i18n + gettext | Included | Translations |
| Testing | pytest + plone.app.testing | Latest | Test framework |
| Catalog | Products.ZCatalog | Included | Content indexing |
| Config | plone.app.registry | Included | Control panel settings |

---

## Risk Mitigation

### JavaScript Externalization
- **Risk**: Breaking WebAuthn flow during migration
- **Mitigation**: Test all flows (registration, login, AAL2 challenge) after each file extraction; keep templates as canary tests

### Audit Logging
- **Risk**: ZODB bloat from large log volumes
- **Mitigation**: Implement retention policy, pack database regularly, document migration path to SQL

### Internationalization
- **Risk**: Poor translation quality
- **Mitigation**: Start with machine translation + human review, prioritize high-traffic UI strings

### Control Panel
- **Risk**: Settings conflicts with programmatic configuration
- **Mitigation**: Document precedence order, validate settings before applying

### Performance
- **Risk**: Catalog reindexing slow on large sites
- **Mitigation**: Batch reindexing during upgrade, run in background thread

---

## Dependencies and Versions

All dependencies are already present in Plone 5.2+ installation:
- `Products.PluggableAuthService`
- `Products.GenericSetup`
- `plone.app.registry`
- `plone.i18n`
- `z3c.form`
- `zope.annotation`
- `ZODB` (via Zope)
- `Products.ZCatalog`

New external dependencies:
- None (all features use Plone built-ins)

---

## Conclusion

All research questions resolved. No "NEEDS CLARIFICATION" markers remain. Proceeding to Phase 1: Design & Contracts.
