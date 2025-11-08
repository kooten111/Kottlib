"""
Example usage of YACLib client library
"""

import sys
sys.path.insert(0, '../src')

from client.yaclib import YACLibClient, YACLibAsyncClient


def example_basic_usage():
    """Basic usage example"""
    print("=" * 60)
    print("Basic Usage Example")
    print("=" * 60)

    # Create client
    client = YACLibClient(base_url="http://192.168.1.5:25565")

    # Open a comic
    print("\n1. Opening comic...")
    metadata = client.open_comic(library_id=2, comic_id=188)

    print(f"   Title: {metadata.path}")
    print(f"   Pages: {metadata.num_pages}")
    print(f"   Hash: {metadata.hash}")
    print(f"   Read: {'Yes' if metadata.read else 'No'}")
    if metadata.next_comic:
        print(f"   Next comic: {metadata.next_comic}")

    # Get cover
    print("\n2. Downloading cover...")
    cover = client.get_cover(metadata.library_id, metadata.hash)
    print(f"   Cover size: {len(cover)} bytes")

    with open('/tmp/cover.jpg', 'wb') as f:
        f.write(cover)
    print("   Saved to /tmp/cover.jpg")

    # Get first page
    print("\n3. Downloading first page...")
    page1 = client.get_page(metadata.library_id, metadata.comic_id, 0)
    print(f"   Page size: {len(page1)} bytes")

    with open('/tmp/page_0.jpg', 'wb') as f:
        f.write(page1)
    print("   Saved to /tmp/page_0.jpg")

    # Get multiple pages
    print("\n4. Downloading pages 1-5...")
    pages = client.get_all_pages(
        metadata.library_id,
        metadata.comic_id,
        start_page=1,
        end_page=6
    )
    print(f"   Downloaded {len(pages)} pages")

    for i, page_data in enumerate(pages, start=1):
        with open(f'/tmp/page_{i}.jpg', 'wb') as f:
            f.write(page_data)
    print("   Saved to /tmp/page_1.jpg through /tmp/page_5.jpg")

    client.close()
    print("\n✓ Done!")


def example_context_manager():
    """Using context manager"""
    print("\n" + "=" * 60)
    print("Context Manager Example")
    print("=" * 60)

    with YACLibClient("http://192.168.1.5:25565") as client:
        # Open comic
        metadata = client.open_comic(2, 188)
        print(f"\nOpened: {metadata.path}")

        # Read first 3 pages
        for page_num in range(3):
            page_data = client.get_page(2, 188, page_num)
            print(f"Page {page_num}: {len(page_data)} bytes")

    print("✓ Done! (session automatically closed)")


def example_async_client():
    """Using async client with better loading detection"""
    print("\n" + "=" * 60)
    print("Async Client Example")
    print("=" * 60)

    client = YACLibAsyncClient("http://192.168.1.5:25565")

    # Open comic (async client will wait for loading)
    print("\n1. Opening comic...")
    metadata = client.open_comic(2, 188, wait_for_load=True)
    print(f"   Opened: {metadata.path}")

    # Check if loaded
    if client.is_comic_loaded():
        print("   ✓ Comic is loaded and ready")

    # Get pages (will wait if needed)
    print("\n2. Getting pages...")
    for page_num in range(5):
        page_data = client.get_page(
            2, 188, page_num,
            wait_if_not_loaded=True  # Async client feature
        )
        print(f"   Page {page_num}: {len(page_data)} bytes")

    client.close()
    print("\n✓ Done!")


def example_error_handling():
    """Error handling example"""
    print("\n" + "=" * 60)
    print("Error Handling Example")
    print("=" * 60)

    client = YACLibClient("http://192.168.1.5:25565")

    try:
        # Open comic
        metadata = client.open_comic(2, 188)
        print(f"\nOpened: {metadata.path} ({metadata.num_pages} pages)")

        # Try to get invalid page
        print("\nTrying to get page 9999 (should fail)...")
        try:
            client.get_page(2, 188, 9999)
        except ValueError as e:
            print(f"   ✓ Caught expected error: {e}")

        # Get valid page
        print("\nGetting valid page 0...")
        page = client.get_page(2, 188, 0)
        print(f"   ✓ Success: {len(page)} bytes")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

    print("\n✓ Done!")


def example_reading_session():
    """Simulate reading a comic"""
    print("\n" + "=" * 60)
    print("Reading Session Example")
    print("=" * 60)

    with YACLibClient("http://192.168.1.5:25565") as client:
        # Open comic
        metadata = client.open_comic(2, 188)
        print(f"\nReading: {metadata.path}")
        print(f"Total pages: {metadata.num_pages}")
        print(f"Current page: {metadata.current_page}")

        # "Read" first 10 pages
        print("\nReading pages 0-9...")
        for page_num in range(10):
            page_data = client.get_page(2, 188, page_num)
            print(f"  Page {page_num + 1}/{metadata.num_pages} ({len(page_data)} bytes)")

            # Update progress every 5 pages
            if (page_num + 1) % 5 == 0:
                client.update_reading_progress(2, 188, page_num + 1)
                print(f"  → Progress saved: page {page_num + 1}")

    print("\n✓ Reading session complete!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='YACLib Client Examples')
    parser.add_argument(
        'example',
        nargs='?',
        choices=['basic', 'context', 'async', 'error', 'reading', 'all'],
        default='all',
        help='Which example to run'
    )

    args = parser.parse_args()

    if args.example == 'all':
        example_basic_usage()
        example_context_manager()
        example_async_client()
        example_error_handling()
        example_reading_session()
    elif args.example == 'basic':
        example_basic_usage()
    elif args.example == 'context':
        example_context_manager()
    elif args.example == 'async':
        example_async_client()
    elif args.example == 'error':
        example_error_handling()
    elif args.example == 'reading':
        example_reading_session()
