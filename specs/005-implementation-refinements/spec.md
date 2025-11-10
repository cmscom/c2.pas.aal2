# Feature Specification: Implementation Refinements and Production Readiness

**Feature Branch**: `005-implementation-refinements`
**Created**: 2025-11-10
**Status**: Draft
**Input**: User description: "ここまでの実装で足りていない分を新規のタスクとしてまとめてから実装をお願いします。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Externalized JavaScript Assets (Priority: P1)

As a **developer maintaining the codebase**, I want JavaScript code moved from inline templates to separate external files so that the code is easier to maintain, test, and debug.

**Why this priority**: Currently WebAuthn JavaScript is embedded inline in .pt templates, making it difficult to maintain, debug, and test. This is the highest priority technical debt that affects code quality and maintainability.

**Independent Test**: Can be fully tested by verifying that all WebAuthn functionality (registration, authentication, AAL2 challenge) works identically after extracting JavaScript to external files. Delivers cleaner, more maintainable code structure.

**Acceptance Scenarios**:

1. **Given** a user on the passkey registration page, **When** they click "Register Passkey", **Then** the WebAuthn flow executes correctly using externalized JavaScript
2. **Given** a user on the login page, **When** they choose passkey login, **Then** authentication works using externalized JavaScript
3. **Given** a user accessing AAL2-protected content, **When** they need to re-authenticate, **Then** the AAL2 challenge works using externalized JavaScript
4. **Given** a developer debugging WebAuthn code, **When** they open browser DevTools, **Then** they can see clear source maps pointing to external .js files

---

### User Story 2 - Persistent Audit Logging (Priority: P2)

As a **security administrator**, I want all authentication events persistently logged to a queryable storage so that I can review security incidents, generate compliance reports, and detect anomalies.

**Why this priority**: Current logging only writes to Python logger, which is ephemeral. Compliance requirements (SOC2, GDPR, HIPAA) often require persistent audit trails. This is P2 because the system works without it, but it's important for production security.

**Independent Test**: Can be fully tested by performing various authentication actions (register passkey, login, AAL2 re-auth, etc.) and querying the audit log storage to verify all events were recorded with correct timestamps and metadata. Delivers compliance-ready audit trail.

**Acceptance Scenarios**:

1. **Given** a user registers a new passkey, **When** the registration completes, **Then** an audit record is created with timestamp, user ID, device info, and success/failure status
2. **Given** an administrator reviewing security events, **When** they query the audit log, **Then** they can filter by user, action type, date range, and outcome
3. **Given** a failed authentication attempt, **When** the failure occurs, **Then** the audit log captures the reason for failure and source IP
4. **Given** an AAL2 policy change, **When** an admin modifies content protection settings, **Then** the change is logged with before/after states

---

### User Story 3 - Internationalization Support (Priority: P2)

As an **international user**, I want the passkey authentication interface in my preferred language so that I can understand instructions and error messages clearly.

**Why this priority**: The code has i18n markers but no translation catalogs. This limits usability for non-English users. P2 because English works but excludes international audiences.

**Independent Test**: Can be fully tested by changing browser language settings and verifying that all UI text (buttons, labels, error messages) displays in the selected language. Delivers globally accessible interface.

**Acceptance Scenarios**:

1. **Given** a Japanese user with browser set to Japanese, **When** they access the passkey registration page, **Then** all UI text displays in Japanese
2. **Given** a Spanish user encountering a WebAuthn error, **When** the error occurs, **Then** the error message displays in Spanish
3. **Given** a developer adding a new UI message, **When** they mark it with i18n, **Then** the message automatically appears in translation catalogs for localization

---

### User Story 4 - Plone Control Panel Integration (Priority: P3)

As a **Plone site administrator**, I want AAL2 settings accessible through the standard Plone control panel so that I can manage security policies using familiar Plone admin interfaces.

**Why this priority**: Currently AAL2 settings are accessible via custom views. Integrating with Plone's control panel provides a more native experience. P3 because current admin UI works but could be more intuitive.

**Independent Test**: Can be fully tested by accessing the Plone control panel, configuring AAL2 settings there, and verifying the changes take effect. Delivers native Plone admin experience.

**Acceptance Scenarios**:

1. **Given** an administrator in the Plone control panel, **When** they navigate to security settings, **Then** they see an "AAL2 Settings" option
2. **Given** an administrator configuring AAL2 timeout, **When** they change the 15-minute default to 10 minutes, **Then** the new timeout is applied system-wide
3. **Given** an administrator managing roles, **When** they assign the "AAL2 Required User" role, **Then** the change is visible in standard Plone user management

---

### User Story 5 - Performance Optimization (Priority: P3)

As a **site administrator**, I want fast lookups of AAL2-protected content so that the system remains responsive even with thousands of protected items.

**Why this priority**: The policy.py code notes that catalog indexing would improve performance when listing AAL2-protected content. P3 because current implementation works but could be optimized for scale.

**Independent Test**: Can be fully tested by creating 1000+ pieces of content with AAL2 protection, then timing the list_aal2_protected_content() function before and after adding catalog indexes. Delivers scalable performance.

**Acceptance Scenarios**:

1. **Given** a site with 5000 AAL2-protected content items, **When** an admin lists protected content, **Then** results return in under 2 seconds
2. **Given** a user accessing AAL2-protected content, **When** the system checks AAL2 requirements, **Then** the check completes in under 100ms
3. **Given** a developer adding new AAL2 annotations, **When** content is indexed, **Then** the catalog automatically indexes AAL2 metadata

---

### Edge Cases

- What happens when JavaScript files fail to load (network error)? → Graceful degradation with error message
- How does the system handle audit log database connection failures? → Falls back to Python logging, logs the failure itself
- What if translation catalogs are missing for a requested language? → Falls back to English with a logged warning
- How does catalog indexing handle content without AAL2 annotations? → Indexes as "not protected" rather than erroring
- What if external JavaScript is cached with old versions? → Version-based cache busting in URLs

## Requirements *(mandatory)*

### Functional Requirements

#### JavaScript Externalization (P1)
- **FR-001**: System MUST extract all inline JavaScript from .pt templates into separate .js files in browser/static/js/
- **FR-002**: System MUST maintain identical WebAuthn functionality after JavaScript extraction
- **FR-003**: System MUST use Plone resource registry for JavaScript delivery with proper dependency management
- **FR-004**: System MUST include source maps for debugging externalized JavaScript
- **FR-005**: System MUST use cache-busting versioning for JavaScript assets

#### Persistent Audit Logging (P2)
- **FR-006**: System MUST store audit events in persistent ZODB storage or SQL database
- **FR-007**: System MUST record the following fields for each audit event: timestamp (UTC), user_id, action_type, outcome (success/failure), source_ip, user_agent, metadata (JSON)
- **FR-008**: System MUST provide query interface for filtering audit events by user, action type, date range, and outcome
- **FR-009**: System MUST retain audit logs for configurable retention period (default: 90 days)
- **FR-010**: System MUST handle audit logging failures gracefully without blocking primary operations
- **FR-011**: System MUST support audit log export in CSV and JSON formats

#### Internationalization (P2)
- **FR-012**: System MUST provide translation catalogs (.po files) for all user-facing text
- **FR-013**: System MUST support at minimum: English (en), Japanese (ja), Spanish (es), French (fr), German (de)
- **FR-014**: System MUST detect user's preferred language from browser Accept-Language header
- **FR-015**: System MUST fall back to English when requested language is unavailable
- **FR-016**: System MUST provide developer-friendly workflow for adding new translatable strings

#### Control Panel Integration (P3)
- **FR-017**: System MUST register AAL2 settings in Plone control panel under "Security" section
- **FR-018**: System MUST provide configurable AAL2 timeout duration via control panel
- **FR-019**: System MUST allow role assignment through control panel interface
- **FR-020**: System MUST display list of AAL2-protected content in control panel
- **FR-021**: System MUST validate AAL2 configuration changes before applying

#### Performance Optimization (P3)
- **FR-022**: System MUST create catalog index for AAL2 protection status
- **FR-023**: System MUST create catalog index for AAL2 role requirements
- **FR-024**: System MUST use catalog queries instead of iterating all content when listing protected items
- **FR-025**: System MUST cache AAL2 policy lookups for 60 seconds to reduce ZODB queries

### Key Entities *(include if feature involves data)*

- **AuditEvent**: Represents a single security or authentication event; attributes include timestamp, user_id, action_type (registration_start, authentication_success, etc.), outcome, ip_address, user_agent, metadata (JSON blob for action-specific data)
- **TranslationCatalog**: Represents a language-specific message catalog; attributes include language_code (ISO 639-1), messages (key-value pairs), last_updated
- **AAL2ControlPanelSettings**: Represents configurable AAL2 parameters; attributes include timeout_seconds (default 900), enabled_features (list), notification_preferences
- **CatalogIndex**: Represents indexed AAL2 metadata for content; attributes include content_uid, aal2_protected (boolean), required_roles (list), protection_level

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All WebAuthn functionality operates identically with externalized JavaScript, verified by existing test suite passing without modification
- **SC-002**: Developers can locate and modify JavaScript code in under 30 seconds (compared to searching through templates currently)
- **SC-003**: Security administrators can query 90 days of audit logs and generate reports in under 5 seconds
- **SC-004**: Audit log storage grows at predictable rate (approximately 1KB per authentication event)
- **SC-005**: Users see interface in their browser's language for all 5 supported languages (en, ja, es, fr, de)
- **SC-006**: Translation coverage reaches 100% for P1 user stories, 80% minimum for P2/P3 features
- **SC-007**: Administrators can configure all AAL2 settings through Plone control panel without using custom views
- **SC-008**: Listing 5000+ AAL2-protected content items completes in under 2 seconds (vs. current O(n) iteration)
- **SC-009**: AAL2 policy checks complete in under 100ms for 95% of requests
- **SC-010**: Zero regressions in existing functionality after implementing all refinements

## Assumptions

1. **Infrastructure**: ZODB is acceptable for audit log storage initially; migration to SQL database can be a future enhancement if needed
2. **Translation**: Translation strings will be provided by community or professional translators; this spec covers the technical framework
3. **JavaScript Bundling**: Plone's resource registry provides adequate bundling and minification; no need for webpack/rollup
4. **Catalog Schema**: Plone's catalog supports adding custom indexes without schema migration complexity
5. **Performance Baseline**: Current implementation handles <1000 AAL2-protected items reasonably; optimization targets sites with 1000+ items
6. **Browser Support**: External JavaScript files maintain same browser compatibility as inline code (modern browsers with WebAuthn API)
7. **Deployment**: Changes can be applied via GenericSetup upgrade steps without requiring full site reinstall

## Dependencies

- Existing c2.pas.aal2 implementation (features 001, 002, 003) must be complete and working
- Plone 5.2+ with functional resource registry for JavaScript management
- plone.app.registry for control panel settings storage
- Products.GenericSetup for upgrade steps and profile management
- For SQL audit logging (optional): SQLAlchemy and database adapter (psycopg2 for PostgreSQL, etc.)

## Out of Scope

The following are explicitly NOT included in this feature:

- **Advanced analytics dashboard**: Audit logs provide raw data; visualization/analytics are future enhancements
- **Real-time monitoring**: Audit system logs events but doesn't provide real-time alerting (use separate monitoring tools)
- **Automated translation**: Translation catalogs will be populated manually or via translation services
- **Migration from existing data**: This assumes a fresh implementation; migrating existing inline JS is manual
- **Mobile app support**: Optimizations focus on web browser performance
- **Custom catalog backends**: Uses Plone's standard catalog; alternative search engines (Solr, Elasticsearch) not covered
- **User-facing audit log access**: Audit logs are admin-only; user-facing "activity history" is separate feature
- **Distributed tracing**: Audit logging is local to Plone instance; distributed systems tracing is separate concern

## Non-Functional Requirements

- **Performance**: JavaScript externalization must not increase page load time by more than 50ms
- **Security**: Audit logs must not expose sensitive data (passwords, security tokens); store only metadata
- **Maintainability**: Code structure should reduce complexity by separating concerns (JS in .js files, not templates)
- **Scalability**: Audit log queries must scale logarithmically, not linearly, with number of events
- **Accessibility**: Translated UI must maintain WCAG 2.1 AA compliance across all languages
- **Backward Compatibility**: Existing AAL2-protected content and user configurations must work without modification

## Technical Constraints

- Must work with Plone 5.2+ (cannot require Plone 6-specific features)
- JavaScript must support browsers that support WebAuthn API (Chrome 67+, Firefox 60+, Safari 13+, Edge 18+)
- Audit log schema must be extensible for future event types without breaking existing queries
- Translation framework must use standard Plone i18n toolchain (plone.app.locales, lingua)
- Control panel must integrate with existing Plone permission model (no new permission types)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JavaScript extraction breaks WebAuthn flow | Medium | High | Extensive testing with all browsers; staged rollout |
| Audit log storage grows too large | Medium | Medium | Implement configurable retention and archival strategy |
| Translation quality is poor | Low | Medium | Professional review for critical languages (ja, es, fr, de) |
| Control panel conflicts with existing plugins | Low | High | Thorough compatibility testing with popular Plone add-ons |
| Catalog indexes slow down content editing | Low | Medium | Benchmark indexing performance; optimize if needed |
| Cache-busting breaks CDN deployments | Low | Medium | Test with common CDN configurations (Cloudflare, etc.) |
