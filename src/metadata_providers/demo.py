#!/usr/bin/env python3
"""
Demo script for Kottlib Scanner System

Shows how to use the scanner framework for different library types.
"""

import sys
from pathlib import Path

from .manager import init_default_scanners, get_manager
from .base import MatchConfidence


def demo_nhentai_scanner():
    """Demo the nhentai scanner"""
    print("="*80)
    print("DEMO: nhentai Scanner (File-level)")
    print("="*80)

    # Initialize manager
    manager = init_default_scanners()

    # Test files
    test_files = [
        "(C102) [Yachan Coffee (Yachan)] Satsuei Genba Machigaete Daijoyuu AV Debut (Love Live!) [English].cbz",
        "[Cuvie] Splaaaash!!.cbz",
        "[DATE] Hypnosis DVD - The Case of the Elder Sister and Younger Brother.cbz",
        "[Mikarin] On or Off (COMIC X-Eros #76).cbz",  # Should be rejected
    ]

    for i, filename in enumerate(test_files, 1):
        print(f"\n{i}. Testing: {filename[:60]}...")
        print("-" * 80)

        # Scan using manager
        result, candidates = manager.scan('nhentai', filename)

        if result:
            confidence_emoji = {
                MatchConfidence.EXACT: "🎯",
                MatchConfidence.HIGH: "✅",
                MatchConfidence.MEDIUM: "⚠️",
                MatchConfidence.LOW: "❌",
                MatchConfidence.NONE: "❌"
            }

            emoji = confidence_emoji[result.confidence_level]
            print(f"{emoji} Match found: {result.confidence_level.name} ({result.confidence:.0%})")
            print(f"   Source: {result.source_url}")
            print(f"   Title: {result.metadata.get('title', 'N/A')[:60]}")

            # Show artists
            artists = result.metadata.get('artists', [])
            if artists:
                print(f"   Artists: {', '.join(artists)}")

            # Show some tags
            if result.tags:
                sample_tags = [t for t in result.tags if t.startswith('tag:')][:5]
                if sample_tags:
                    tag_names = [t.split(':', 1)[1] for t in sample_tags]
                    print(f"   Tags: {', '.join(tag_names)}")

            # Show metadata bonuses if any
            bonuses = result.metadata.get('score_bonuses', {})
            if bonuses:
                bonus_str = ', '.join([f"{k}:{v:+.0%}" for k, v in bonuses.items() if v != 0])
                if bonus_str:
                    print(f"   Bonuses: {bonus_str}")

        else:
            print(f"❌ No match found (low confidence)")


def demo_scanner_stats():
    """Show statistics about configured scanners"""
    print("\n" + "="*80)
    print("SCANNER CONFIGURATION")
    print("="*80)

    manager = get_manager()

    print(f"\nAvailable Scanners: {', '.join(manager.get_available_scanners())}")
    print(f"Configured Libraries: {', '.join(manager.get_configured_libraries())}")

    for lib_type in manager.get_configured_libraries():
        configs = manager.get_library_config(lib_type)
        print(f"\n{lib_type.upper()}:")
        for i, config in enumerate(configs, 1):
            scanner = config.scanner_class(config.config)
            role = "PRIMARY" if config.is_primary else "FALLBACK"
            print(f"  {i}. {scanner.source_name} ({scanner.scan_level.value}) - {role}")


def demo_direct_scanner_use():
    """Demo using a scanner directly without the manager"""
    print("\n" + "="*80)
    print("DEMO: Direct Scanner Usage")
    print("="*80)

    from .providers.nhentai import scan_file

    filename = "[Aiue Oka] FamiCon - Family Control Ch 3.cbz"
    print(f"\nScanning: {filename}")

    result = scan_file(filename)

    if result:
        print(f"✅ Found: {result.metadata.get('title', 'Unknown')}")
        print(f"   Confidence: {result.confidence:.0%}")
        print(f"   ID: {result.source_id}")
        print(f"   URL: {result.source_url}")
    else:
        print("❌ No match found")


def main():
    """Run all demos"""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "Kottlib Scanner System Demo" + " "*32 + "║")
    print("╚" + "="*78 + "╝\n")

    try:
        # Demo 1: nhentai scanner
        demo_nhentai_scanner()

        # Demo 2: Scanner configuration
        demo_scanner_stats()

        # Demo 3: Direct use
        demo_direct_scanner_use()

        print("\n" + "="*80)
        print("✅ Demo completed successfully!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
