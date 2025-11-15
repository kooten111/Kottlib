# AniList Scanner

Series-level metadata scanner for manga and light novels using the AniList GraphQL API.

## Scan Level: SERIES

This scanner operates at the **SERIES** level, meaning it scans entire manga/light novel series rather than individual files or volumes.

### What This Means

- **In the UI**: When a library is configured to use the AniList scanner, you'll see options to scan by series name
- **Metadata Fetched**: Information applies to the entire series (title, author, artist, description, genres, etc.)
- **Use Case**: Best for organizing complete manga/light novel series

## Features

- **AniList GraphQL API Integration**: Official, stable API with no rate limiting concerns
- **Rich Metadata**: Fetches comprehensive series information including:
  - Multiple title formats (Romaji, English, Native)
  - Staff information (writers, artists)
  - Characters
  - Genres and tags
  - Publication dates
  - Volume/chapter counts
  - Cover and banner images
  - MAL ID cross-reference

- **Smart Matching**: Fuzzy title matching with confidence scores
- **No API Key Required**: Free and open API

## Configuration

See `config.json` for available options:

- `confidence_threshold`: Minimum match confidence (default: 0.6)
- `use_romaji_titles`: Match against Romaji titles (default: true)
- `use_english_titles`: Match against English titles (default: true)
- `use_native_titles`: Match against Native titles (default: false)
- `max_results`: Maximum search results (default: 10)

## Usage

### Via API
```python
from scanners.AniList.anilist_scanner import AniListScanner

scanner = AniListScanner()
best_match, all_matches = scanner.scan("Berserk")

if best_match:
    print(f"Found: {best_match.metadata['title']}")
    print(f"Writer: {best_match.metadata['writer']}")
    print(f"Confidence: {best_match.confidence:.2%}")
```

### Via Command Line
```bash
python scanners/AniList/anilist_scanner.py "One Piece"
python scanners/AniList/anilist_scanner.py "Berserk" --detailed
python scanners/AniList/anilist_scanner.py "Vagabond" --json
```

## Scan Level Comparison

| Scanner | Scan Level | UI Behavior | Best For |
|---------|-----------|-------------|----------|
| **nhentai** | FILE | Scan individual files/volumes | Doujinshi, single releases |
| **AniList** | SERIES | Scan entire series | Manga, light novels |

When browsing a library:
- **nhentai scanner** → UI shows "Scan File" options for individual comics
- **AniList scanner** → UI shows "Scan Series" options for entire series
