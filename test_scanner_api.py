#!/usr/bin/env python3
"""
Test script for Scanner API

Run this after server restart to test the scanner endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8081/v2"

def test_available_scanners():
    """Test GET /scanners/available"""
    print("\n" + "="*80)
    print("TEST: Get Available Scanners")
    print("="*80)

    response = requests.get(f"{BASE_URL}/scanners/available")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nAvailable Scanners: {len(data)}")
        for scanner in data:
            print(f"  - {scanner['name']} ({scanner['scan_level']})")
            print(f"    {scanner['description']}")
    else:
        print(f"Error: {response.text}")


def test_scan_single():
    """Test POST /scanners/scan"""
    print("\n" + "="*80)
    print("TEST: Scan Single File")
    print("="*80)

    payload = {
        "query": "(C102) [Yachan Coffee (Yachan)] Satsuei Genba Machigaete Daijoyuu AV Debut (Love Live!) [English].cbz",
        "library_type": "doujinshi"
    }

    print(f"Query: {payload['query'][:60]}...")

    response = requests.post(f"{BASE_URL}/scanners/scan", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Match Found!")
        print(f"  Confidence: {data['confidence']:.0%} ({data['confidence_level']})")
        print(f"  Source: {data['source_url']}")
        print(f"  Title: {data['metadata'].get('title', 'N/A')[:60]}")
        print(f"  Artists: {', '.join(data['metadata'].get('artists', []))}")
        print(f"  Tags: {len(data['tags'])} tags")
    else:
        print(f"Error: {response.text}")


def test_bulk_scan():
    """Test POST /scanners/scan/bulk"""
    print("\n" + "="*80)
    print("TEST: Bulk Scan")
    print("="*80)

    payload = {
        "queries": [
            "[Cuvie] Splaaaash!!.cbz",
            "[DATE] Hypnosis DVD.cbz",
            "[Invalid] This Should Fail.cbz"
        ],
        "library_type": "doujinshi",
        "confidence_threshold": 0.4
    }

    print(f"Scanning {len(payload['queries'])} files...")

    response = requests.post(f"{BASE_URL}/scanners/scan/bulk", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nResults:")
        print(f"  Total: {data['total']}")
        print(f"  Matched: {data['matched']}")
        print(f"  Rejected: {data['rejected']}")

        for result in data['results']:
            status_emoji = "✅" if result['status'] == 'matched' else "❌"
            query = result['query'][:50]
            if result['status'] == 'matched':
                print(f"  {status_emoji} {query}: {result['confidence']:.0%}")
            else:
                print(f"  {status_emoji} {query}: {result.get('reason', 'Unknown')}")
    else:
        print(f"Error: {response.text}")


def test_library_config():
    """Test GET /scanners/libraries"""
    print("\n" + "="*80)
    print("TEST: Get Library Configurations")
    print("="*80)

    response = requests.get(f"{BASE_URL}/scanners/libraries")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nConfigured Libraries: {len(data)}")
        for lib in data:
            print(f"  - {lib['library_name']}")
            print(f"    Primary: {lib['primary_scanner']}")
            if lib['fallback_scanners']:
                print(f"    Fallback: {', '.join(lib['fallback_scanners'])}")
            print(f"    Confidence Threshold: {lib['confidence_threshold']:.0%}")
    else:
        print(f"Error: {response.text}")


def main():
    print("\n╔" + "="*78 + "╗")
    print("║" + " "*25 + "Scanner API Test Suite" + " "*30 + "║")
    print("╚" + "="*78 + "╝")

    try:
        test_available_scanners()
        test_library_config()
        test_scan_single()
        test_bulk_scan()

        print("\n" + "="*80)
        print("✅ All tests completed!")
        print("="*80 + "\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("   Make sure the server is running on http://localhost:8081")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
