# Scanner System Quick Start

## Installation

No installation needed - just ensure dependencies are available:
```bash
cd /mnt/Black/Apps/KottLib
pip install requests  # Already installed
```

## Quick Examples

### 1. Scan a Single File

```python
from scanners.nhentai import scan_file

result = scan_file("[Artist] Comic Title [English].cbz")

if result:
    print(f"✅ Match: {result.metadata['title']}")
    print(f"   Confidence: {result.confidence:.0%}")
    print(f"   Artists: {', '.join(result.metadata['artists'])}")
    print(f"   URL: {result.source_url}")
else:
    print("❌ No match found")
```

### 2. Batch Scan Multiple Files

```python
from scanners import init_default_scanners

manager = init_default_scanners()

files = [
    "comic1.cbz",
    "comic2.cbz",
    "comic3.cbz"
]

for filename in files:
    result, _ = manager.scan('library_type', filename)

    if result:
        print(f"✅ {filename}: {result.confidence:.0%} - {result.source_id}")
    else:
        print(f"❌ {filename}: No match")
```

### 3. Get Detailed Results

```python
from scanners.nhentai import scan_file

result = scan_file("comic.cbz")

if result:
    # Access metadata
    print(f"Title: {result.metadata['title']}")
    print(f"Artists: {result.metadata['artists']}")
    print(f"Groups: {result.metadata['groups']}")
    print(f"Parodies: {result.metadata['parodies']}")
    print(f"Language: {result.metadata['language']}")

    # Access tags
    content_tags = [t.split(':')[1] for t in result.tags if t.startswith('tag:')]
    print(f"Content Tags: {', '.join(content_tags[:10])}")

    # Check confidence level
    print(f"Confidence Level: {result.confidence_level.name}")

    # Get raw response for debugging
    print(f"Search Strategy: {result.raw_response['search_strategy']}")
    print(f"Score Bonuses: {result.raw_response['score_bonuses']}")
```

## Configuration Options

### Adjust Confidence Threshold

```python
from scanners.nhentai import NhentaiScanner

# More strict (fewer false positives)
scanner = NhentaiScanner({'confidence_threshold': 0.6})

# More lenient (fewer missed matches)
scanner = NhentaiScanner({'confidence_threshold': 0.3})

result, _ = scanner.scan("comic.cbz")
```

### Disable Fallback Searches

```python
from scanners.nhentai import NhentaiScanner

scanner = NhentaiScanner({
    'use_fallback_searches': False  # Don't try artist+title, etc.
})

result, _ = scanner.scan("comic.cbz")
```

## Understanding Results

### Confidence Levels

| Level | Range | Meaning |
|-------|-------|---------|
| EXACT | 90-100% | Trust this match completely |
| HIGH | 70-89% | Very likely correct |
| MEDIUM | 40-69% | Possibly correct, review recommended |
| LOW | 1-39% | Probably wrong |
| NONE | 0% | No match |

### Score Bonuses

Check `result.raw_response['score_bonuses']` to see why a match got its score:

```python
{
    'artist_unique': 0.15,      # Artist matched and was unique
    'event': 0.10,              # Event (C102) matched
    'artist_mismatch_penalty': -0.5  # Expected artist not found
}
```

## Common Patterns

### Filter by Confidence

```python
results = []
for filename in files:
    result, _ = manager.scan('library_type', filename)
    if result and result.confidence >= 0.8:  # Only high confidence
        results.append((filename, result))
```

### Manual Review Queue

```python
high_confidence = []
needs_review = []
no_match = []

for filename in files:
    result, _ = manager.scan('library_type', filename)

    if result:
        if result.confidence >= 0.8:
            high_confidence.append((filename, result))
        else:
            needs_review.append((filename, result))
    else:
        no_match.append(filename)

print(f"Auto-accepted: {len(high_confidence)}")
print(f"Need review: {len(needs_review)}")
print(f"No match: {len(no_match)}")
```

### Extract Specific Tags

```python
def get_tags_by_type(result, tag_type):
    """Extract tags of a specific type"""
    prefix = f"{tag_type}:"
    return [t.split(':', 1)[1] for t in result.tags if t.startswith(prefix)]

# Usage
artists = get_tags_by_type(result, 'artist')
parodies = get_tags_by_type(result, 'parody')
content_tags = get_tags_by_type(result, 'tag')
```

## Testing

Run the demo to verify everything works:

```bash
cd /mnt/Black/Apps/KottLib/Kottlib
python3 scanners/demo_scanners.py
```

## Troubleshooting

### "No match found" for valid files

1. Check the filename format - does it include artist name in brackets?
2. Try lowering confidence threshold
3. Check if the comic exists on nhentai.net
4. Look at `result.raw_response['num_results']` to see if search returned anything

### Wrong matches

1. Check `result.raw_response['score_bonuses']` for penalties
2. If artist mismatch penalty is applied, the artist might not be on nhentai
3. Try a more specific search query

### Import errors

Make sure you're in the right directory:
```bash
cd /mnt/Black/Apps/KottLib/Kottlib
python3 -c "from scanners import NhentaiScanner; print('OK')"
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [base_scanner.py](base_scanner.py) for API reference
- See [demo_scanners.py](demo_scanners.py) for more examples
