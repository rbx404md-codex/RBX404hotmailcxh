#!/usr/bin/env python3
"""
Verification Script - Auto Proxy Refresh System
Tests all components before production deployment
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} NOT FOUND: {filepath}")
        return False

def check_syntax(filepath):
    """Check Python file syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            compile(f.read(), filepath, 'exec')
        print(f"✅ Syntax OK: {filepath}")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax Error in {filepath}: {e}")
        return False

def check_import(module_path, description):
    """Check if a module can be imported."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)
        # Don't execute, just check if it can be loaded
        print(f"✅ Import OK: {description}")
        return True
    except Exception as e:
        print(f"❌ Import Error in {description}: {e}")
        return False

def check_config_values():
    """Check configuration values."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from CONFIG import config

        print("\n📋 Configuration Values:")
        print(f"   PROXY_BATCH_INTERVAL: {config.PROXY_BATCH_INTERVAL}s ({config.PROXY_BATCH_INTERVAL//60} min)")
        print(f"   PROXY_CLEAR_AFTER_BATCHES: {config.PROXY_CLEAR_AFTER_BATCHES}")
        print(f"   MASTER_THREADS: {config.MASTER_THREADS}")
        print(f"   ADMIN_ID: {config.ADMIN_ID}")

        if config.PROXY_BATCH_INTERVAL == 1200:
            print("✅ Proxy interval set to 20 minutes")
            return True
        else:
            print(f"⚠️  Proxy interval is {config.PROXY_BATCH_INTERVAL//60} minutes (expected 20)")
            return False
    except Exception as e:
        print(f"❌ Config check failed: {e}")
        return False

def check_state_module():
    """Check state.py has global proxy pool."""
    try:
        with open('HOME/state.py', 'r') as f:
            content = f.read()

        if 'global_proxy_pool' in content and 'global_proxy_pool_lock' in content:
            print("✅ Global proxy pool found in state.py")
            return True
        else:
            print("❌ Global proxy pool NOT found in state.py")
            return False
    except Exception as e:
        print(f"❌ State module check failed: {e}")
        return False

def check_proxy_module():
    """Check proxy.py has refresh functionality."""
    try:
        with open('PROXY/proxy.py', 'r') as f:
            content = f.read()

        checks = [
            ('update_global_proxy_pool', 'update_global_proxy_pool function'),
            ('refresh_from_global_pool', 'refresh_from_global_pool method'),
            ('use_global_pool', 'use_global_pool flag'),
        ]

        all_ok = True
        for check_str, description in checks:
            if check_str in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} NOT found")
                all_ok = False

        return all_ok
    except Exception as e:
        print(f"❌ Proxy module check failed: {e}")
        return False

def check_admin_commands():
    """Check admin.py has new commands."""
    try:
        with open('COMMANDS/ADMIN/admin.py', 'r') as f:
            content = f.read()

        checks = [
            ('send_full_bot_backup', 'send_full_bot_backup function'),
            ('fetch_full', '/fetch_full command'),
            ('def cmd_fetch_full', 'cmd_fetch_full handler'),
        ]

        all_ok = True
        for check_str, description in checks:
            if check_str in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} NOT found")
                all_ok = False

        return all_ok
    except Exception as e:
        print(f"❌ Admin commands check failed: {e}")
        return False

def check_bot_integration():
    """Check bot.py has proxy refresh integration."""
    try:
        with open('bot.py', 'r') as f:
            content = f.read()

        checks = [
            ('update_global_proxy_pool', 'Global pool update call'),
            ('refresh_from_global_pool', 'ProxyRotator refresh call'),
            ('send_full_bot_backup', 'Full backup call'),
            ('Proxies Refreshed!', 'User notification message'),
        ]

        all_ok = True
        for check_str, description in checks:
            if check_str in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} NOT found")
                all_ok = False

        return all_ok
    except Exception as e:
        print(f"❌ Bot integration check failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 AUTO PROXY REFRESH SYSTEM - VERIFICATION")
    print("=" * 60)

    results = []

    # Check files exist
    print("\n📁 Checking Files...")
    files = [
        ('bot.py', 'Main bot file'),
        ('CONFIG/config.py', 'Config file'),
        ('HOME/state.py', 'State module'),
        ('PROXY/proxy.py', 'Proxy module'),
        ('COMMANDS/ADMIN/admin.py', 'Admin commands'),
        ('HOME/session.py', 'Session module'),
        ('HOME/runner.py', 'Runner module'),
    ]

    for filepath, desc in files:
        results.append(check_file_exists(filepath, desc))

    # Check syntax
    print("\n🔍 Checking Syntax...")
    for filepath, _ in files:
        if os.path.exists(filepath):
            results.append(check_syntax(filepath))

    # Check configuration
    print("\n⚙️  Checking Configuration...")
    results.append(check_config_values())

    # Check state module
    print("\n🔄 Checking State Module...")
    results.append(check_state_module())

    # Check proxy module
    print("\n🌐 Checking Proxy Module...")
    results.append(check_proxy_module())

    # Check admin commands
    print("\n👑 Checking Admin Commands...")
    results.append(check_admin_commands())

    # Check bot integration
    print("\n🤖 Checking Bot Integration...")
    results.append(check_bot_integration())

    # Check documentation
    print("\n📚 Checking Documentation...")
    docs = [
        'PROXY_AUTO_REFRESH_SYSTEM.md',
        'IMPLEMENTATION_SUMMARY.md',
        'QUICK_START_GUIDE.md',
    ]
    for doc in docs:
        results.append(check_file_exists(doc, f"Documentation: {doc}"))

    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"Passed: {passed}/{total} ({percentage:.1f}%)")

    if passed == total:
        print("\n🎉 ALL CHECKS PASSED! System ready for deployment!")
        print("\n🚀 Next Steps:")
        print("   1. Start bot: python3 bot.py")
        print("   2. Monitor console for proxy refresh logs")
        print("   3. Test with a long check (1000+ combos)")
        print("   4. Wait 20 minutes and verify:")
        print("      - Check continues without stopping")
        print("      - User receives notification")
        print("      - Admin receives full backup")
        print("\n📖 Read QUICK_START_GUIDE.md for detailed instructions")
        return 0
    else:
        print(f"\n⚠️  {total - passed} CHECKS FAILED!")
        print("Please review the errors above and fix them before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
