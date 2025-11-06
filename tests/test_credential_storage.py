# -*- coding: utf-8 -*-
"""Tests for credential storage layer."""

import pytest
from datetime import datetime, timezone
from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAnnotations


class MockUser:
    """Mock Plone user for testing."""

    def __init__(self, user_id):
        self.user_id = user_id
        self._annotations = {}
        self._p_changed = False

    def getId(self):
        return self.user_id


class MockAnnotations:
    """Mock IAnnotations adapter."""

    def __init__(self, user):
        self.user = user
        self.data = user._annotations

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def __delitem__(self, key):
        del self.data[key]


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return MockUser('testuser')


@pytest.fixture
def mock_annotations(monkeypatch, mock_user):
    """Mock IAnnotations adapter."""
    def mock_iannotations(user):
        return MockAnnotations(user)

    # Monkeypatch IAnnotations
    import c2.pas.aal2.credential as cred_module
    monkeypatch.setattr(cred_module, 'IAnnotations', mock_iannotations)

    return mock_iannotations


class TestCredentialStorage:
    """Test credential storage functions."""

    def test_add_passkey(self, mock_user, mock_annotations):
        """Test adding a passkey to user storage."""
        from c2.pas.aal2.credential import add_passkey

        credential_data = {
            'credential_id': b'test_credential_123',
            'public_key': b'test_public_key',
            'sign_count': 0,
            'aaguid': b'test_aaguid',
            'device_name': 'Test Device',
            'device_type': 'platform',
            'transports': ['internal'],
        }

        # Add passkey
        credential_id_b64 = add_passkey(mock_user, credential_data)

        # Verify it was added
        assert credential_id_b64 is not None
        assert isinstance(credential_id_b64, str)
        assert mock_user._p_changed is True

        # Check annotations
        annotations = mock_annotations(mock_user)
        assert 'c2.pas.aal2.passkeys' in annotations
        passkeys = annotations['c2.pas.aal2.passkeys']
        assert credential_id_b64 in passkeys

        # Check stored data
        stored = passkeys[credential_id_b64]
        assert stored['device_name'] == 'Test Device'
        assert stored['device_type'] == 'platform'
        assert stored['sign_count'] == 0
        assert stored['created'] is not None
        assert stored['last_used'] is None

    def test_get_user_passkeys(self, mock_user, mock_annotations):
        """Test retrieving all passkeys for a user."""
        from c2.pas.aal2.credential import add_passkey, get_user_passkeys

        # Add two passkeys
        cred1 = {
            'credential_id': b'cred1',
            'public_key': b'key1',
            'sign_count': 0,
            'device_name': 'Device 1',
        }
        cred2 = {
            'credential_id': b'cred2',
            'public_key': b'key2',
            'sign_count': 5,
            'device_name': 'Device 2',
        }

        id1 = add_passkey(mock_user, cred1)
        id2 = add_passkey(mock_user, cred2)

        # Get all passkeys
        passkeys = get_user_passkeys(mock_user)

        assert len(passkeys) == 2
        assert id1 in passkeys
        assert id2 in passkeys
        assert passkeys[id1]['device_name'] == 'Device 1'
        assert passkeys[id2]['device_name'] == 'Device 2'

    def test_get_passkey(self, mock_user, mock_annotations):
        """Test retrieving a specific passkey."""
        from c2.pas.aal2.credential import add_passkey, get_passkey

        credential_data = {
            'credential_id': b'specific_cred',
            'public_key': b'specific_key',
            'sign_count': 10,
            'device_name': 'Specific Device',
        }

        cred_id = add_passkey(mock_user, credential_data)

        # Get the specific passkey
        passkey = get_passkey(mock_user, cred_id)

        assert passkey is not None
        assert passkey['device_name'] == 'Specific Device'
        assert passkey['sign_count'] == 10
        assert passkey['credential_id'] == b'specific_cred'

    def test_get_passkey_not_found(self, mock_user, mock_annotations):
        """Test getting a non-existent passkey returns None."""
        from c2.pas.aal2.credential import get_passkey

        passkey = get_passkey(mock_user, 'nonexistent')

        assert passkey is None

    def test_update_passkey_last_used(self, mock_user, mock_annotations):
        """Test updating passkey last_used timestamp and sign count."""
        from c2.pas.aal2.credential import (
            add_passkey,
            get_passkey,
            update_passkey_last_used
        )

        credential_data = {
            'credential_id': b'update_test',
            'public_key': b'test_key',
            'sign_count': 0,
            'device_name': 'Update Test Device',
        }

        cred_id = add_passkey(mock_user, credential_data)

        # Initially last_used should be None
        passkey = get_passkey(mock_user, cred_id)
        assert passkey['last_used'] is None
        assert passkey['sign_count'] == 0

        # Update
        update_passkey_last_used(mock_user, cred_id, new_sign_count=5)

        # Check updated values
        passkey = get_passkey(mock_user, cred_id)
        assert passkey['last_used'] is not None
        assert isinstance(passkey['last_used'], datetime)
        assert passkey['sign_count'] == 5
        assert mock_user._p_changed is True

    def test_delete_passkey(self, mock_user, mock_annotations):
        """Test deleting a passkey."""
        from c2.pas.aal2.credential import (
            add_passkey,
            get_passkey,
            delete_passkey
        )

        credential_data = {
            'credential_id': b'delete_test',
            'public_key': b'test_key',
            'sign_count': 0,
            'device_name': 'Delete Test',
        }

        cred_id = add_passkey(mock_user, credential_data)

        # Verify it exists
        assert get_passkey(mock_user, cred_id) is not None

        # Delete it
        result = delete_passkey(mock_user, cred_id)

        assert result is True
        assert get_passkey(mock_user, cred_id) is None
        assert mock_user._p_changed is True

    def test_delete_passkey_not_found(self, mock_user, mock_annotations):
        """Test deleting a non-existent passkey returns False."""
        from c2.pas.aal2.credential import delete_passkey

        result = delete_passkey(mock_user, 'nonexistent')

        assert result is False

    def test_count_passkeys(self, mock_user, mock_annotations):
        """Test counting passkeys."""
        from c2.pas.aal2.credential import add_passkey, count_passkeys

        # Initially 0
        assert count_passkeys(mock_user) == 0

        # Add one
        add_passkey(mock_user, {
            'credential_id': b'count1',
            'public_key': b'key1',
            'sign_count': 0,
        })
        assert count_passkeys(mock_user) == 1

        # Add another
        add_passkey(mock_user, {
            'credential_id': b'count2',
            'public_key': b'key2',
            'sign_count': 0,
        })
        assert count_passkeys(mock_user) == 2

    def test_passkey_isolation_between_users(self, mock_annotations):
        """Test that passkeys are isolated per user."""
        from c2.pas.aal2.credential import add_passkey, get_user_passkeys

        user1 = MockUser('user1')
        user2 = MockUser('user2')

        # Add passkey to user1
        add_passkey(user1, {
            'credential_id': b'user1_cred',
            'public_key': b'key1',
            'sign_count': 0,
            'device_name': 'User 1 Device',
        })

        # Add passkey to user2
        add_passkey(user2, {
            'credential_id': b'user2_cred',
            'public_key': b'key2',
            'sign_count': 0,
            'device_name': 'User 2 Device',
        })

        # Verify isolation
        user1_passkeys = get_user_passkeys(user1)
        user2_passkeys = get_user_passkeys(user2)

        assert len(user1_passkeys) == 1
        assert len(user2_passkeys) == 1
        assert list(user1_passkeys.values())[0]['device_name'] == 'User 1 Device'
        assert list(user2_passkeys.values())[0]['device_name'] == 'User 2 Device'

    def test_credential_id_base64_encoding(self, mock_user, mock_annotations):
        """Test that credential IDs are properly base64url encoded."""
        from c2.pas.aal2.credential import add_passkey
        import base64

        # Use a credential ID with special characters
        raw_cred_id = b'\x00\x01\x02\xff\xfe\xfd'

        credential_data = {
            'credential_id': raw_cred_id,
            'public_key': b'test_key',
            'sign_count': 0,
        }

        cred_id_b64 = add_passkey(mock_user, credential_data)

        # Should be base64url encoded (no padding)
        assert '=' not in cred_id_b64
        assert '+' not in cred_id_b64
        assert '/' not in cred_id_b64

        # Should be decodable
        decoded = base64.urlsafe_b64decode(cred_id_b64 + '==')
        assert decoded == raw_cred_id
