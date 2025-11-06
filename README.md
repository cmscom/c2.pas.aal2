# c2.pas.aal2 - Plone PAS AAL2 Authentication Plugin Template

A template/skeleton package for implementing AAL2 (Authentication Assurance Level 2) authentication support in Plone through the Pluggable Authentication Service (PAS).

## Overview

This package provides a complete structural template for a Plone PAS plugin that supports AAL2 authentication requirements. It includes:

- **2-dot namespace package structure** (`c2.pas.aal2`)
- **PAS plugin stub implementation** with `IAuthenticationPlugin` and `IExtractionPlugin` interfaces
- **ZCML configuration** for plugin registration
- **Pytest test structure** with basic tests
- **Complete documentation** and implementation guides

**Note:** This is a template/skeleton package. The authentication methods are stubs that do not affect existing authentication flows. Future developers should implement the actual AAL2 authentication logic.

## Requirements

- Python 3.11 or higher
- Plone 5.2 or higher
- Products.PluggableAuthService (included with Plone)

## Installation

### Development Installation

```bash
# Clone or download the package
git clone <repository-url> c2.pas.aal2
cd c2.pas.aal2

# Create a virtual environment (Python 3.11+)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with test dependencies
pip install -e ".[test]"
```

### Verify Installation

```bash
# Test package import
python -c "import c2.pas.aal2; print('Import successful!')"

# Run tests
pytest tests/ -v
```

## Package Structure

```
c2.pas.aal2/
├── src/                         # Source code directory (src layout)
│   └── c2/                      # Top-level namespace
│       └── pas/                 # Second-level namespace
│           └── aal2/            # Actual package code
│               ├── __init__.py  # Package initialization
│               ├── plugin.py    # AAL2Plugin stub class
│               ├── interfaces.py # Zope interface definitions
│               └── configure.zcml # ZCML configuration
├── tests/                       # Test directory
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── test_import.py           # Import tests
│   ├── test_plugin_registration.py  # Plugin registration tests
│   └── test_stub_methods.py     # Stub method tests
├── docs/                        # Documentation directory
│   └── implementation_guide.md  # Implementation guidelines
├── setup.py                     # Setup script (package_dir={'': 'src'})
├── MANIFEST.in                  # Package manifest
├── README.md                    # This file
├── LICENSE                      # License file (GPLv2)
├── .gitignore                   # Git exclusions
├── tox.ini                      # Tox configuration
├── pytest.ini                   # Pytest configuration
└── CHANGES.rst                  # Changelog (Plone standard)
```

## Usage in Plone

### Add to Plone Buildout

Add the package to your Plone `buildout.cfg`:

```ini
[buildout]
eggs =
    ...
    c2.pas.aal2

develop =
    path/to/c2.pas.aal2
```

### Run Buildout

```bash
bin/buildout
```

### Start Plone

```bash
bin/instance fg
```

### Enable the Plugin

1. Log in to Plone management interface
2. Navigate to **Site Setup** → **Zope Management Interface** → **acl_users**
3. The "C2 PAS AAL2 Authentication Plugin" should appear in the plugin list
4. Click to enable it

**Note:** The stub implementation doesn't affect existing authentication flows. All methods return neutral values (None or empty dict).

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=c2.pas.aal2 --cov-report=term-missing

# Run specific test file
pytest tests/test_import.py -v
```

## Key Components

### AAL2Plugin Class (`src/c2/pas/aal2/plugin.py`)

The main plugin class implementing:
- `IAuthenticationPlugin`: Authentication credential validation
- `IExtractionPlugin`: Credential extraction from requests
- `IAAL2Plugin`: Custom AAL2-specific interface

**Stub Methods:**
- `extractCredentials(request)`: Returns empty dict
- `authenticateCredentials(credentials)`: Returns None
- `get_aal_level(user_id)`: Returns 1
- `require_aal2(user_id, context)`: Returns False

### IAAL2Plugin Interface (`src/c2/pas/aal2/interfaces.py`)

Defines the contract for AAL2 functionality:
- `get_aal_level(user_id)`: Get user's current AAL level
- `require_aal2(user_id, context)`: Check if AAL2 is required

### ZCML Configuration (`src/c2/pas/aal2/configure.zcml`)

Registers the plugin with Plone's PAS framework.

## Future Implementation

To implement actual AAL2 authentication logic, extend the stub methods:

### 1. Implement Authentication Logic

```python
def authenticateCredentials(self, credentials):
    """
    TODO: Implement AAL2 authentication
    - Verify 2FA tokens
    - Check authentication strength
    - Return (user_id, login) on success
    """
    # Current: return None
    pass
```

### 2. Add AAL Level Detection

```python
def get_aal_level(self, user_id):
    """
    TODO: Detect actual AAL level
    - Check authentication method
    - Verify 2FA status
    - Return 1, 2, or 3
    """
    # Current: return 1
    pass
```

### 3. Implement Policy Enforcement

```python
def require_aal2(self, user_id, context):
    """
    TODO: Enforce AAL2 policies
    - Check content annotations
    - Trigger step-up authentication
    - Return True if AAL2 required but not met
    """
    # Current: return False
    pass
```

### 4. Add Tests

Create additional test files in `tests/`:
- `test_aal2_authentication.py`: AAL2 authentication logic tests
- `test_aal2_policies.py`: Policy enforcement tests
- `test_session_management.py`: Session handling tests

### 5. Add GenericSetup Profile (Optional)

```bash
mkdir -p src/c2/pas/aal2/profiles/default
touch src/c2/pas/aal2/profiles/default/metadata.xml
```

## Documentation

- **Implementation Guide**: See `docs/implementation_guide.md` for detailed implementation instructions
- **Plone PAS Documentation**: https://docs.plone.org/develop/plone/security/pas.html
- **Products.PluggableAuthService**: https://pypi.org/project/Products.PluggableAuthService/

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest tests/ -v`
6. Submit a pull request

## License

GPLv2 (GNU General Public License v2)

See LICENSE file for full license text.

## Author

Your Name <your.email@example.com>

## Support

- Plone Community Forum: https://community.plone.org/
- Issue Tracker: <repository-url>/issues

## Changelog

See `CHANGES.rst` for version history and changes.

---

**Estimated Setup Time**: 10 minutes (with existing Plone environment)

This is a template package. Implement the stub methods to add actual AAL2 authentication functionality.
