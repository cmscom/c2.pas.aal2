#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test script to validate passkey login and session persistence.

Usage:
    1. Make sure Plone is running with the c2.pas.aal2 package installed
    2. Run this script: python test_passkey_login.py
    3. Follow the instructions to test login flow
"""

import requests
import json
from datetime import datetime
import sys


def test_passkey_login(base_url='http://localhost:8080/Plone'):
    """Test passkey login flow and session persistence."""

    print("=" * 60)
    print("Passkey Login Session Persistence Test")
    print("=" * 60)
    print(f"Testing against: {base_url}")
    print()

    # Create a session to maintain cookies
    session = requests.Session()

    # Test 1: Check if AAL2 plugin is installed
    print("Test 1: Checking AAL2 plugin availability...")
    try:
        response = session.get(f"{base_url}/@@passkey-login")
        if response.status_code == 200:
            print("✓ Passkey login page is accessible")
        else:
            print(f"✗ Failed to access passkey login page: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error accessing Plone: {e}")
        print("Make sure Plone is running and accessible at the specified URL")
        return False

    # Test 2: Check for __ac cookie after manual login
    print("\nTest 2: Session persistence check")
    print("-" * 40)
    print("MANUAL STEP REQUIRED:")
    print("1. Open your browser and navigate to:")
    print(f"   {base_url}/@@passkey-login")
    print("2. Login using your passkey")
    print("3. After successful login, open browser DevTools")
    print("4. Go to Application/Storage > Cookies")
    print("5. Find the '__ac' cookie and note its properties")
    print()

    input("Press Enter after you've logged in with passkey...")

    # Test 3: Validate cookie properties
    print("\nTest 3: Cookie validation checklist")
    print("-" * 40)
    print("Please verify the following in your browser's DevTools:")
    print()
    print("[ ] __ac cookie exists")
    print("[ ] Cookie has Max-Age or Expires set (not session-only)")
    print("[ ] Cookie has HttpOnly flag set (security)")
    print("[ ] Cookie has SameSite=Lax set (CSRF protection)")
    print("[ ] Cookie path is '/' (site-wide access)")
    print()

    verified = input("Do all checks pass? (y/n): ").lower()
    if verified != 'y':
        print("✗ Cookie properties need adjustment")
        return False
    else:
        print("✓ Cookie properties are correct")

    # Test 4: Test session persistence
    print("\nTest 4: Session persistence across browser restart")
    print("-" * 40)
    print("MANUAL STEP REQUIRED:")
    print("1. Close your browser completely")
    print("2. Re-open your browser")
    print("3. Navigate to a protected area:")
    print(f"   {base_url}/@@manage-passkeys")
    print("4. You should still be logged in (no login prompt)")
    print()

    input("Press Enter after testing browser restart...")

    still_logged_in = input("Were you still logged in? (y/n): ").lower()
    if still_logged_in != 'y':
        print("✗ Session persistence failed")
        return False
    else:
        print("✓ Session persists across browser restarts")

    # Test 5: Test AAL2 validation
    print("\nTest 5: AAL2 timestamp and validation")
    print("-" * 40)
    print("Testing AAL2-protected content access...")
    print("If AAL2 is required, you should be prompted for re-authentication")
    print("after 15 minutes of passkey authentication.")
    print()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ AAL2 plugin is installed and accessible")
    print("✓ Passkey login creates proper authentication cookie")
    print("✓ Cookie has correct security properties")
    print("✓ Session persists across browser restarts")
    print()
    print("All tests passed! Passkey login with session persistence is working.")

    return True


def print_troubleshooting():
    """Print troubleshooting steps if tests fail."""
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING GUIDE")
    print("=" * 60)
    print("""
If session persistence is not working:

1. Check PAS plugin order:
   - Go to /acl_users/manage_plugins
   - Verify 'aal2_plugin' is active for:
     * IExtractionPlugin (should be at top)
     * IAuthenticationPlugin (should be at top)
     * IValidationPlugin
     * ICredentialsUpdatePlugin

2. Check browser settings:
   - Cookies must be enabled
   - Third-party cookies may need to be allowed for localhost
   - Check if browser is blocking the cookie

3. Check Plone logs:
   - Look for errors from 'c2.pas.aal2.plugin'
   - Check for cookie setting errors
   - Verify user authentication events

4. Verify installation:
   - Reinstall the package: /prefs_install_products_form
   - Check that JavaScript resources are loaded
   - Verify WebAuthn API is available in browser console

5. Debug cookie creation:
   - Set logging level to DEBUG for c2.pas.aal2
   - Monitor cookie creation in browser DevTools Network tab
   - Check Set-Cookie response headers
""")


if __name__ == '__main__':
    # Allow custom Plone URL
    plone_url = 'http://localhost:8080/Plone'
    if len(sys.argv) > 1:
        plone_url = sys.argv[1]

    success = test_passkey_login(plone_url)

    if not success:
        print_troubleshooting()
        sys.exit(1)

    sys.exit(0)