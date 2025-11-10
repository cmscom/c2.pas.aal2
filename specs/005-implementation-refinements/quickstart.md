# Quickstart Guide: Implementation Refinements (Feature 005)

**Target Audience**: Developers implementing or maintaining c2.pas.aal2
**Prerequisites**: Features 001-003 completed and working
**Estimated Time**: 4-6 hours for P1, 6-8 hours for P2, 4-6 hours for P3

---

## Overview

This guide walks through implementing the five refinement user stories:

1. **P1**: JavaScript Externalization (~2-3 hours)
2. **P2**: Persistent Audit Logging (~3-4 hours)
3. **P2**: Internationalization (~3-4 hours)
4. **P3**: Control Panel Integration (~2-3 hours)
5. **P3**: Performance Optimization (~2-3 hours)

Total estimated time: **16-22 hours**

---

## Development Environment Setup

### Prerequisites

```bash
# Verify Python version
python --version  # Should be 3.11+

# Verify Plone installation
cd /path/to/plone/instance
bin/instance --version  # Should be 5.2+

# Check existing c2.pas.aal2 installation
bin/instance debug
>>> portal = app.Plone
>>> 'c2.pas.aal2' in portal.acl_users.objectIds()
True  # Should be True if features 001-003 installed
```

### Branch Setup

```bash
cd /path/to/workspace
git checkout 005-implementation-refinements

# Verify branch
git branch --show-current
# Output: 005-implementation-refinements
```

### Test Environment

```bash
# Run existing tests to ensure baseline
pytest tests/

# Should see output like:
# ===== 45 passed in 12.34s =====
```

---

## P1: JavaScript Externalization (2-3 hours)

**Goal**: Move inline JavaScript from .pt templates to external .js files

### Step 1: Create JavaScript Files (30 min)

Files already created in `src/c2/pas/aal2/browser/static/js/`:
- `webauthn-utils.js` (utilities)
- `webauthn-register.js` (registration flow)
- `webauthn-login.js` (login flow)
- `webauthn-aal2.js` (AAL2 challenge)
- `passkey-management.js` (management UI)

**Verification**:
```bash
ls -1 src/c2/pas/aal2/browser/static/js/
# Expected output:
# webauthn-utils.js
# webauthn-register.js
# webauthn-login.js
# webauthn-aal2.js
# passkey-management.js
```

### Step 2: Register Resources in Plone (15 min)

Create `src/c2/pas/aal2/profiles/default/jsregistry.xml`:

```xml
<?xml version="1.0"?>
<object name="portal_javascripts">

  <!-- Base utilities - load first -->
  <javascript id="++resource++c2.pas.aal2/js/webauthn-utils.js"
              cacheable="True"
              compression="safe"
              cookable="True"
              enabled="True"
              inline="False"/>

  <!-- Registration flow -->
  <javascript id="++resource++c2.pas.aal2/js/webauthn-register.js"
              cacheable="True"
              compression="safe"
              cookable="True"
              enabled="True"
              inline="False"/>

  <!-- Login flow -->
  <javascript id="++resource++c2.pas.aal2/js/webauthn-login.js"
              cacheable="True"
              compression="safe"
              cookable="True"
              enabled="True"
              inline="False"/>

  <!-- AAL2 challenge -->
  <javascript id="++resource++c2.pas.aal2/js/webauthn-aal2.js"
              cacheable="True"
              compression="safe"
              cookable="True"
              enabled="True"
              inline="False"/>

  <!-- Management UI -->
  <javascript id="++resource++c2.pas.aal2/js/passkey-management.js"
              cacheable="True"
              compression="safe"
              cookable="True"
              enabled="True"
              inline="False"/>

</object>
```

### Step 3: Update Templates (1 hour)

For each template, replace inline `<script>` tags with initialization calls.

**Example: `register_passkey.pt`**

Before (lines 79-219):
```xml
<metal:javascript fill-slot="javascript_head_slot">
  <script type="text/javascript" tal:content="structure string:
    // [140 lines of inline JavaScript]
  ">
  </script>
</metal:javascript>
```

After:
```xml
<metal:javascript fill-slot="javascript_head_slot">
  <script tal:replace="structure context/@@webauthn-resources-register"></script>
  <script type="text/javascript">
    document.addEventListener('DOMContentLoaded', function() {
      initPasskeyRegistration();
    });
  </script>
</metal:javascript>
```

**Repeat for**:
- `login_with_passkey.pt` → use `initPasskeyLogin()`
- `enhanced_login.pt` → use `initEnhancedLogin()`
- `aal2_challenge.pt` → use `initAAL2Challenge({...})`
- `manage_passkeys.pt` → use `initPasskeyManagement()`

### Step 4: Create Resource View (15 min)

Add to `src/c2/pas/aal2/browser/views.py`:

```python
from Products.Five import BrowserView

class WebAuthnResourcesRegister(BrowserView):
    """Include WebAuthn resources for registration page"""

    def __call__(self):
        portal_url = self.context.portal_url()
        return """
        <script src="{}/++resource++c2.pas.aal2/js/webauthn-utils.js"></script>
        <script src="{}/++resource++c2.pas.aal2/js/webauthn-register.js"></script>
        """.format(portal_url, portal_url)

# Add similar views for login, aal2, management
```

Register in `src/c2/pas/aal2/browser/configure.zcml`:

```xml
<browser:page
    name="webauthn-resources-register"
    for="*"
    class=".views.WebAuthnResourcesRegister"
    permission="zope2.View"
    />
```

### Step 5: Test (30 min)

```bash
# Restart Plone
bin/instance restart

# Run tests
pytest tests/test_browser_views.py -k javascript

# Manual browser test
# 1. Visit http://localhost:8080/Plone/@@register-passkey
# 2. Open DevTools → Sources tab
# 3. Verify external .js files are loaded
# 4. Click "Register Passkey" and verify flow works
```

**Success Criteria**:
- ✅ No inline JavaScript in .pt files
- ✅ External .js files visible in DevTools Sources
- ✅ All WebAuthn flows (register, login, AAL2) work identically
- ✅ Tests pass

---

## P2: Persistent Audit Logging (3-4 hours)

**Goal**: Store audit events in ZODB with query interface

### Step 1: Create Storage Module (1 hour)

Create `src/c2/pas/aal2/storage/__init__.py`:

```python
"""Persistent audit log storage"""
```

Create `src/c2/pas/aal2/storage/audit.py`:

```python
"""
Audit log storage implementation using ZODB.
See specs/005-implementation-refinements/data-model.md for schema.
"""

import uuid
from datetime import datetime, timezone
from persistent import Persistent
from persistent.mapping import PersistentMapping
from BTrees.OOBTree import OOBTree
from zope.annotation.interfaces import IAnnotations

AUDIT_CONTAINER_KEY = 'c2.pas.aal2.audit_logs'

class AuditEvent(Persistent):
    """Single audit log event"""

    def __init__(self, user_id, action_type, outcome, ip_address, user_agent, metadata=None):
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)
        self.user_id = user_id
        self.action_type = action_type
        self.outcome = outcome
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.metadata = metadata or {}

class AuditLogContainer(Persistent):
    """Container for audit events with indexes"""

    def __init__(self):
        self.events = OOBTree()  # timestamp -> event
        self.by_user = OOBTree()  # user_id -> [event_ids]
        self.by_action = OOBTree()  # action_type -> [event_ids]
        self.by_outcome = OOBTree()  # outcome -> [event_ids]
        self.metadata = PersistentMapping({
            'created': datetime.now(timezone.utc),
            'last_cleaned': None,
            'total_events': 0,
            'retention_days': 90
        })

    def add_event(self, event):
        """Add event and update indexes"""
        # Primary index
        self.events[event.timestamp.timestamp()] = event

        # Secondary indexes
        self._add_to_index(self.by_user, event.user_id, event.event_id)
        self._add_to_index(self.by_action, event.action_type, event.event_id)
        self._add_to_index(self.by_outcome, event.outcome, event.event_id)

        self.metadata['total_events'] = len(self.events)
        self._p_changed = True

    def _add_to_index(self, index, key, event_id):
        """Helper to add event ID to index"""
        if key not in index:
            index[key] = PersistentList()
        index[key].append(event_id)

def get_audit_container(portal):
    """Get or create audit log container"""
    annotations = IAnnotations(portal)
    if AUDIT_CONTAINER_KEY not in annotations:
        annotations[AUDIT_CONTAINER_KEY] = AuditLogContainer()
    return annotations[AUDIT_CONTAINER_KEY]

def log_audit_event(portal, user_id, action_type, outcome, request, metadata=None):
    """Log an audit event"""
    try:
        container = get_audit_container(portal)
        event = AuditEvent(
            user_id=user_id,
            action_type=action_type,
            outcome=outcome,
            ip_address=request.get('REMOTE_ADDR', 'unknown'),
            user_agent=request.get('HTTP_USER_AGENT', 'unknown'),
            metadata=metadata
        )
        container.add_event(event)
        return event.event_id
    except Exception as e:
        # Fail open: log error but don't break operation
        import logging
        logging.error(f"Failed to log audit event: {e}")
        return None
```

### Step 2: Create Query Interface (1 hour)

Create `src/c2/pas/aal2/storage/query.py`:

```python
"""Audit log query interface"""

from datetime import datetime, timezone, timedelta
from .audit import get_audit_container

def query_audit_logs(portal, user_id=None, action_type=None, outcome=None,
                     start_date=None, end_date=None, limit=100, offset=0):
    """
    Query audit logs with filters.

    Returns:
        dict: {
            'items': [AuditEvent, ...],
            'total': int,
            'limit': int,
            'offset': int
        }
    """
    container = get_audit_container(portal)

    # Get candidate events from indexes
    candidates = set()

    if user_id:
        candidates = set(container.by_user.get(user_id, []))
    elif action_type:
        candidates = set(container.by_action.get(action_type, []))
    elif outcome:
        candidates = set(container.by_outcome.get(outcome, []))
    else:
        # No index filter, use timestamp range
        candidates = None

    # Filter by timestamp if specified
    results = []
    for timestamp, event in container.events.items():
        if candidates is not None and event.event_id not in candidates:
            continue

        if start_date and event.timestamp < start_date:
            continue
        if end_date and event.timestamp > end_date:
            continue

        results.append(event)

    total = len(results)

    # Pagination
    results = results[offset:offset + limit]

    return {
        'items': results,
        'total': total,
        'limit': limit,
        'offset': offset
    }

def export_audit_logs(portal, format='csv', **filters):
    """Export audit logs in CSV or JSON format"""
    results = query_audit_logs(portal, limit=10000, **filters)

    if format == 'csv':
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'event_id', 'timestamp', 'user_id', 'action_type',
            'outcome', 'ip_address', 'user_agent', 'metadata'
        ])
        writer.writeheader()
        for event in results['items']:
            writer.writerow({
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'user_id': event.user_id,
                'action_type': event.action_type,
                'outcome': event.outcome,
                'ip_address': event.ip_address,
                'user_agent': event.user_agent,
                'metadata': str(event.metadata)
            })
        return output.getvalue()

    elif format == 'json':
        import json
        return json.dumps([{
            'event_id': e.event_id,
            'timestamp': e.timestamp.isoformat(),
            'user_id': e.user_id,
            'action_type': e.action_type,
            'outcome': e.outcome,
            'ip_address': e.ip_address,
            'user_agent': e.user_agent,
            'metadata': e.metadata
        } for e in results['items']], indent=2)
```

### Step 3: Update Existing Audit Calls (1 hour)

Update `src/c2/pas/aal2/utils/audit.py`:

```python
# Keep existing Python logger calls
# Add persistent storage calls

def log_registration_success(user_id, credential_id, device_name, request):
    """Log successful passkey registration"""
    # Existing logger call
    logger.info(f"Passkey registered: user={user_id}, credential={credential_id}")

    # NEW: Persistent storage
    from c2.pas.aal2.storage.audit import log_audit_event
    portal = getSite()
    log_audit_event(
        portal=portal,
        user_id=user_id,
        action_type='registration_success',
        outcome='success',
        request=request,
        metadata={
            'credential_id': credential_id,
            'device_name': device_name
        }
    )

# Repeat for all audit functions
```

### Step 4: Test (1 hour)

```bash
pytest tests/test_audit_storage.py

# Manual test:
# 1. Register a passkey
# 2. Check audit log:
bin/instance debug
>>> from c2.pas.aal2.storage.query import query_audit_logs
>>> results = query_audit_logs(app.Plone, limit=10)
>>> len(results['items'])
1
>>> results['items'][0].action_type
'registration_success'
```

---

## P2: Internationalization (3-4 hours)

**Goal**: Add translation catalogs for 5 languages

### Step 1: Setup Locales Directory (15 min)

```bash
mkdir -p src/c2/pas/aal2/locales/{en,ja,es,fr,de}/LC_MESSAGES
```

### Step 2: Extract Translatable Strings (30 min)

```bash
# Install i18ndude if not present
pip install i18ndude

# Create POT template
bin/i18ndude rebuild-pot \
    --pot src/c2/pas/aal2/locales/c2.pas.aal2.pot \
    --create c2.pas.aal2 \
    src/c2/pas/aal2

# Create .po files for each language
for lang in en ja es fr de; do
    bin/i18ndude sync \
        --pot src/c2/pas/aal2/locales/c2.pas.aal2.pot \
        src/c2/pas/aal2/locales/$lang/LC_MESSAGES/c2.pas.aal2.po
done
```

### Step 3: Translate Strings (2 hours)

Edit `src/c2/pas/aal2/locales/ja/LC_MESSAGES/c2.pas.aal2.po`:

```po
msgid "Register a Passkey"
msgstr "パスキーを登録"

msgid "Touch your security key or use your device's biometric sensor"
msgstr "セキュリティキーにタッチするか、デバイスの生体認証センサーを使用してください"

# ... (continue for ~50-60 strings)
```

**Translation Options**:
1. Use machine translation (DeepL, Google Translate) + human review
2. Hire professional translator
3. Community contributions

### Step 4: Compile Translations (15 min)

```bash
for lang in ja es fr de; do
    msgfmt -o src/c2/pas/aal2/locales/$lang/LC_MESSAGES/c2.pas.aal2.mo \
        src/c2/pas/aal2/locales/$lang/LC_MESSAGES/c2.pas.aal2.po
done
```

### Step 5: Test (30 min)

```bash
# Restart Plone
bin/instance restart

# Test in browser:
# 1. Change browser language to Japanese
# 2. Visit passkey registration page
# 3. Verify UI is in Japanese
```

---

## P3: Control Panel Integration (2-3 hours)

**Goal**: Add AAL2 settings to Plone control panel

### Step 1: Create Control Panel Module (1 hour)

Create `src/c2/pas/aal2/controlpanel/__init__.py`:

```python
"""Control panel integration"""
```

Create `src/c2/pas/aal2/controlpanel/interfaces.py`:

```python
from zope.interface import Interface
from zope import schema

class IAAL2Settings(Interface):
    """AAL2 Security Settings"""

    aal2_timeout_seconds = schema.Int(
        title="AAL2 Session Timeout (seconds)",
        description="Time before AAL2 re-authentication required",
        default=900,
        min=300,
        max=3600,
        required=True
    )

    aal2_enabled = schema.Bool(
        title="Enable AAL2 Protection",
        description="Turn AAL2 enforcement on/off globally",
        default=True,
        required=True
    )

    audit_retention_days = schema.Int(
        title="Audit Log Retention (days)",
        description="Days to retain audit logs",
        default=90,
        min=30,
        max=365,
        required=True
    )
```

Create `src/c2/pas/aal2/controlpanel/views.py`:

```python
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from .interfaces import IAAL2Settings

class AAL2SettingsEditForm(RegistryEditForm):
    schema = IAAL2Settings
    label = "AAL2 Security Settings"
    description = "Configure AAL2 authentication and audit logging"
```

### Step 2: Register Control Panel (30 min)

Create `src/c2/pas/aal2/profiles/default/controlpanel.xml`:

```xml
<?xml version="1.0"?>
<object name="portal_controlpanel">
  <configlet
      title="AAL2 Settings"
      action_id="aal2settings"
      appId="c2.pas.aal2"
      category="Products"
      condition_expr=""
      url_expr="string:${portal_url}/@@aal2-settings"
      icon_expr="string:${portal_url}/++resource++plone-logo.svg"
      visible="True">
    <permission>Manage portal</permission>
  </configlet>
</object>
```

Create `src/c2/pas/aal2/profiles/default/registry.xml`:

```xml
<?xml version="1.0"?>
<registry>
  <records interface="c2.pas.aal2.controlpanel.interfaces.IAAL2Settings" />
</registry>
```

### Step 3: Update Code to Use Registry (30 min)

Update `src/c2/pas/aal2/session.py`:

```python
# OLD: Hardcoded constant
AAL2_TIMEOUT_SECONDS = 900

# NEW: Read from registry
from plone import api

def get_aal2_timeout():
    """Get AAL2 timeout from registry"""
    try:
        return api.portal.get_registry_record(
            'c2.pas.aal2.aal2_timeout_seconds'
        )
    except:
        return 900  # Fallback

def is_aal2_valid(user):
    """Check if AAL2 timestamp is still valid"""
    timestamp = get_aal2_timestamp(user)
    if not timestamp:
        return False

    timeout = get_aal2_timeout()  # Use registry value
    now = datetime.now(timezone.utc)
    return (now - timestamp).total_seconds() < timeout
```

### Step 4: Test (30 min)

```bash
bin/instance restart

# Visit control panel:
# http://localhost:8080/Plone/@@overview-controlpanel
# Look for "AAL2 Settings" under Products

# Change timeout to 600 seconds
# Verify change takes effect
```

---

## P3: Performance Optimization (2-3 hours)

**Goal**: Add catalog indexes for fast AAL2 content queries

### Step 1: Create Catalog Module (1 hour)

Create `src/c2/pas/aal2/catalog/__init__.py`:

```python
"""Catalog indexing for AAL2 content"""
```

Create `src/c2/pas/aal2/catalog/indexes.py`:

```python
from plone.indexer import indexer
from Products.CMFCore.interfaces import IContentish
from c2.pas.aal2.policy import is_aal2_required

@indexer(IContentish)
def aal2_protected(object):
    """Index whether content requires AAL2"""
    try:
        return is_aal2_required(object)
    except:
        return False

@indexer(IContentish)
def aal2_required_roles(object):
    """Index which roles require AAL2"""
    try:
        from zope.annotation.interfaces import IAnnotations
        annotations = IAnnotations(object, {})
        return annotations.get('__aal2_required_roles__', [])
    except:
        return []
```

### Step 2: Register Indexes (30 min)

Create `src/c2/pas/aal2/profiles/default/catalog.xml`:

```xml
<?xml version="1.0"?>
<object name="portal_catalog">
  <index name="aal2_protected" meta_type="FieldIndex">
    <indexed_attr value="aal2_protected"/>
  </index>
  <index name="aal2_required_roles" meta_type="KeywordIndex">
    <indexed_attr value="aal2_required_roles"/>
  </index>
</object>
```

Register indexers in `src/c2/pas/aal2/configure.zcml`:

```xml
<adapter factory=".catalog.indexes.aal2_protected" name="aal2_protected" />
<adapter factory=".catalog.indexes.aal2_required_roles" name="aal2_required_roles" />
```

### Step 3: Update Query Code (30 min)

Update `src/c2/pas/aal2/policy.py`:

```python
def list_aal2_protected_content():
    """List all AAL2-protected content using catalog"""
    portal = getSite()
    catalog = getToolByName(portal, 'portal_catalog')

    # OLD: Iterate all content (O(n))
    # for brain in catalog():
    #     if is_aal2_required(brain.getObject()):
    #         yield brain

    # NEW: Use index (O(log n))
    brains = catalog(aal2_protected=True)
    return [brain.getObject() for brain in brains]
```

### Step 4: Test Performance (30 min)

```bash
# Create test content
bin/instance debug
>>> from Testing.makerequest import makerequest
>>> app = makerequest(app)
>>> portal = app.Plone

# Create 1000 test items
>>> for i in range(1000):
...     portal.invokeFactory('Document', f'doc-{i}')

# Benchmark OLD way (iterate all)
>>> import time
>>> start = time.time()
>>> items = [b for b in catalog() if is_aal2_required(b.getObject())]
>>> print(f"Old: {time.time() - start:.2f}s, {len(items)} items")

# Benchmark NEW way (catalog query)
>>> start = time.time()
>>> items = catalog(aal2_protected=True)
>>> print(f"New: {time.time() - start:.2f}s, {len(items)} items")

# Should see 10-100x speedup
```

---

## Integration Testing

After implementing all features, run full test suite:

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/test_integration_aal2.py -v

# Browser tests (if available)
pytest tests/test_browser_views.py -v

# Expected: All tests pass, no regressions
```

---

## Deployment Checklist

Before deploying to production:

- [ ] All tests pass
- [ ] Manual testing completed for each user story
- [ ] Documentation updated (README.md, docs/)
- [ ] Upgrade step tested on copy of production database
- [ ] Backup of production database taken
- [ ] Plone cache cleared after upgrade
- [ ] JavaScript resources verified in browser DevTools
- [ ] Translations verified in multiple languages
- [ ] Control panel settings migrated from code constants
- [ ] Catalog indexes rebuilt (`@@maintenance-controlpanel`)
- [ ] Performance benchmarks meet success criteria

---

## Troubleshooting

### JavaScript Not Loading

**Problem**: External .js files return 404

**Solution**:
```bash
# Restart Plone
bin/instance restart

# Clear resource registry cache
# Visit: http://localhost:8080/Plone/@@resourceregistry-controlpanel
# Click "Build bundles"
```

### Audit Logs Not Appearing

**Problem**: Events not saved to ZODB

**Solution**:
```python
# Check container exists
>>> from c2.pas.aal2.storage.audit import get_audit_container
>>> container = get_audit_container(portal)
>>> len(container.events)

# Check for exceptions in Zope log
tail -f var/log/instance.log
```

### Translations Not Showing

**Problem**: UI still in English despite .po files

**Solution**:
```bash
# Compile .mo files
msgfmt -o locales/ja/LC_MESSAGES/c2.pas.aal2.mo \
    locales/ja/LC_MESSAGES/c2.pas.aal2.po

# Restart Plone
bin/instance restart
```

### Catalog Indexes Empty

**Problem**: aal2_protected index has 0 items

**Solution**:
```bash
# Reindex all content
bin/instance debug
>>> catalog = app.Plone.portal_catalog
>>> catalog.manage_reindexIndex(ids=['aal2_protected', 'aal2_required_roles'])
```

---

## Next Steps

After completing all refinements:

1. Run `/speckit.tasks` to generate tasks.md for implementation tracking
2. Commit changes: `git commit -m "feat: implement refinements (feature 005)"`
3. Create pull request for code review
4. Deploy to staging environment for QA
5. Monitor audit logs and performance metrics in production

---

## Additional Resources

- [Plone Resource Registry Documentation](https://docs.plone.org/develop/plone/misc/registry.html)
- [ZODB BTrees Documentation](https://zodb.readthedocs.io/en/latest/guide/modules.html#btrees)
- [Plone i18n Guide](https://docs.plone.org/develop/plone/i18n/index.html)
- [plone.app.registry Tutorial](https://docs.plone.org/develop/addons/components/registry.html)
- [ZCatalog Indexing Best Practices](https://docs.plone.org/develop/plone/searching_and_indexing/indexing.html)
