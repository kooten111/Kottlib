#!/usr/bin/env python3
"""
Quick verification script to check scanner system setup
Run this before restarting the server to ensure everything is configured correctly.
"""

import sys
from pathlib import Path

def check_files():
    """Verify all required files exist"""
    print("=" * 80)
    print("FILE CHECK")
    print("=" * 80)

    required_files = [
        "scanners/__init__.py",
        "scanners/base_scanner.py",
        "scanners/scanner_manager.py",
        "scanners/nhentai/__init__.py",
        "scanners/nhentai/nhentai_scanner.py",
        "src/api/routers/scanners.py",
        "webui/src/routes/admin/scanners/+page.svelte",
        "test_scanner_api.py",
    ]

    all_exist = True
    for filepath in required_files:
        path = Path(filepath)
        if path.exists():
            print(f"✅ {filepath}")
        else:
            print(f"❌ MISSING: {filepath}")
            all_exist = False

    return all_exist


def check_imports():
    """Verify Python imports work"""
    print("\n" + "=" * 80)
    print("IMPORT CHECK")
    print("=" * 80)

    # Add scanners to path
    SCANNERS_PATH = Path(__file__).parent / "scanners"
    sys.path.insert(0, str(SCANNERS_PATH))

    checks = []

    # Check scanner base
    try:
        from scanners.base_scanner import BaseScanner, ScanResult, MatchConfidence
        print("✅ scanners.base_scanner")
        checks.append(True)
    except Exception as e:
        print(f"❌ scanners.base_scanner: {e}")
        checks.append(False)

    # Check scanner manager
    try:
        from scanners.scanner_manager import ScannerManager, init_default_scanners
        print("✅ scanners.scanner_manager")
        checks.append(True)
    except Exception as e:
        print(f"❌ scanners.scanner_manager: {e}")
        checks.append(False)

    # Check nhentai scanner
    try:
        from scanners.nhentai.nhentai_scanner import NhentaiScanner
        print("✅ scanners.nhentai.nhentai_scanner")
        checks.append(True)
    except Exception as e:
        print(f"❌ scanners.nhentai.nhentai_scanner: {e}")
        checks.append(False)

    # Check API router
    try:
        from src.api.routers import scanners
        print("✅ src.api.routers.scanners")
        checks.append(True)
    except Exception as e:
        print(f"❌ src.api.routers.scanners: {e}")
        checks.append(False)

    return all(checks)


def check_fastapi_routes():
    """Verify FastAPI routes are registered"""
    print("\n" + "=" * 80)
    print("FASTAPI ROUTES CHECK")
    print("=" * 80)

    try:
        from src.api.main import app

        scanner_routes = [
            route for route in app.routes
            if hasattr(route, 'path') and 'scanner' in route.path.lower()
        ]

        expected_routes = [
            '/v2/scanners/available',
            '/v2/scanners/libraries',
            '/v2/scanners/scan',
            '/v2/scanners/scan/bulk',
        ]

        print(f"\nFound {len(scanner_routes)} scanner routes:")
        for route in scanner_routes:
            methods = ','.join(route.methods) if hasattr(route, 'methods') else 'N/A'
            print(f"  [{methods}] {route.path}")

        all_found = all(
            any(route.path == expected for route in scanner_routes)
            for expected in expected_routes
        )

        if all_found:
            print("\n✅ All expected routes registered")
            return True
        else:
            print("\n⚠️  Some expected routes missing")
            return False

    except Exception as e:
        print(f"❌ Failed to check routes: {e}")
        return False


def check_scanner_initialization():
    """Verify scanner manager can be initialized"""
    print("\n" + "=" * 80)
    print("SCANNER INITIALIZATION CHECK")
    print("=" * 80)

    try:
        # Add scanners to path
        SCANNERS_PATH = Path(__file__).parent / "scanners"
        sys.path.insert(0, str(SCANNERS_PATH))

        from scanners import init_default_scanners

        manager = init_default_scanners()

        available = manager.get_available_scanners()
        print(f"✅ Scanner manager initialized")
        print(f"   Available scanners: {', '.join(available)}")

        configured = manager.get_configured_libraries()
        print(f"   Configured libraries: {', '.join(configured)}")

        return True

    except Exception as e:
        print(f"❌ Scanner initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_vite_config():
    """Verify Vite proxy configuration"""
    print("\n" + "=" * 80)
    print("VITE PROXY CHECK")
    print("=" * 80)

    vite_config = Path("webui/vite.config.js")
    if not vite_config.exists():
        print("❌ vite.config.js not found")
        return False

    content = vite_config.read_text()

    checks = {
        "'/v2'": False,
        "'http://localhost:8081'": False,
        "changeOrigin: true": False,
    }

    for check in checks:
        if check in content:
            checks[check] = True
            print(f"✅ Found: {check}")
        else:
            print(f"❌ Missing: {check}")

    return all(checks.values())


def main():
    print("\n╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Scanner System Verification" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝\n")

    results = []

    results.append(("Files", check_files()))
    results.append(("Imports", check_imports()))
    results.append(("FastAPI Routes", check_fastapi_routes()))
    results.append(("Scanner Init", check_scanner_initialization()))
    results.append(("Vite Config", check_vite_config()))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n" + "=" * 80)
        print("✅ All checks passed! Scanner system is ready.")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Restart the backend server:")
        print("   python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8081")
        print("\n2. Run API tests:")
        print("   python3 test_scanner_api.py")
        print("\n3. Open admin UI:")
        print("   http://localhost:5173/admin/scanners")
    else:
        print("\n" + "=" * 80)
        print("❌ Some checks failed. Review errors above.")
        print("=" * 80)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
