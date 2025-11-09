# Metadata Enrichment & Auto-Tagging

**Status**: Planning
**Priority**: High (40k+ items without metadata)
**Created**: 2025-11-09

## Problem Statement

Many comic/manga collections lack embedded metadata (ComicInfo.xml). For a collection of **41,099 items (1.3TB)**, manual metadata entry is impractical. We need automated metadata enrichment using:

1. **Filename parsing** to extract series, volume, chapter, year
2. **Online database lookups** to fetch comprehensive metadata
3. **Batch processing** to handle large collections efficiently

---

## Example Collection Structure

```
Manga/
├── Accomplishments of the Duke's Daughter/
│   ├── Accomplishments of the Duke's Daughter v01 (2018) (Digital) (danke-Empire).cbz
│   ├── Accomplishments of the Duke's Daughter v02 (2018) (Digital) (danke-Empire).cbz
│   ├── Accomplishments of the Duke's Daughter v03 (2019) (Digital) (danke-Empire).cbz
│   ├── ...
│   └── Accomplishments of the Duke's Daughter v08 (2022) (Digital) [nao].cbz
│
├── One Piece/
│   ├── One Piece v001 (2003) (Digital) (AnHeroGold-Empire).cbz
│   ├── One Piece v002 (2003) (Digital) (AnHeroGold-Empire).cbz
│   └── ...
│
└── Batman/
    ├── Batman (1940) 001.cbr
    ├── Batman (1940) 002.cbr
    └── ...
```

**Common Patterns**:
- Series name from folder/filename
- Volume/Chapter number: `v01`, `#001`, `ch.123`
- Year in parentheses: `(2018)`, `(1940)`
- Release group in brackets: `[nao]`, `(Digital)`
- Format hints: `(Digital)`, `(Print)`

---

## Metadata Sources

### 1. AniList (Manga/Anime)

**API**: https://anilist.co/graphql
**Free**: Yes (no API key required)
**Rate Limit**: 90 requests/minute
**Coverage**: Manga, Manhwa, Manhua, Light Novels

**Available Metadata**:
- Title (English, Romaji, Native)
- Synonyms/Alternative titles
- Format (Manga, Manhwa, Light Novel, etc.)
- Status (Ongoing, Completed, Hiatus)
- Start/End dates
- Genres (Action, Romance, Fantasy, etc.)
- Tags (Detailed, community-driven)
- Description/Synopsis
- Average score & popularity
- Cover image URL
- Staff (Authors, Artists)
- Characters (main cast)
- Related media

**Example Query**:
```graphql
query ($search: String) {
  Media (search: $search, type: MANGA) {
    id
    title {
      romaji
      english
      native
    }
    synonyms
    format
    status
    startDate { year month day }
    endDate { year month day }
    genres
    tags { name rank }
    description
    averageScore
    popularity
    coverImage { large }
    staff { edges { node { name { full } } role } }
    characters { edges { node { name { full } } role } }
  }
}
```

**Pros**:
- Comprehensive manga metadata
- Free, no API key
- Active community (up-to-date)
- GraphQL (flexible queries)

**Cons**:
- Primarily anime/manga (limited Western comics)
- Rate limits (need throttling)

---

### 2. Comic Vine (Western Comics)

**API**: https://comicvine.gamespot.com/api/
**Free**: Yes (requires API key)
**Rate Limit**: 200 requests/hour
**Coverage**: Western comics (Marvel, DC, Image, etc.)

**Available Metadata**:
- Title, volume, issue number
- Series information
- Publisher
- Cover date
- Creators (writers, artists, etc.)
- Characters, teams, locations
- Story arcs
- Description
- Cover image URL
- Genres/Tags

**Pros**:
- Best for Western comics
- Detailed creator credits
- Character/team information
- Story arc tracking

**Cons**:
- Requires API key (registration)
- Strict rate limits
- Less coverage for manga

---

### 3. Open Library (Books/Graphic Novels)

**API**: https://openlibrary.org/developers/api
**Free**: Yes (no API key)
**Rate Limit**: Generous (undocumented)
**Coverage**: Books, graphic novels, collected editions

**Pros**:
- No API key required
- Good for collected editions
- ISBN lookup support

**Cons**:
- Limited comic-specific metadata
- Better for books than single issues

---

### 4. Fallback: Filename Parsing Only

When online lookup fails or is disabled:
- Extract series, volume, year from filename
- Use folder structure for organization
- Generate basic metadata from available info

---

## Filename Parsing Strategy

### Regex Patterns

```python
PATTERNS = {
    # Manga: "Series Name v01 (2018) (Digital) [Group].cbz"
    'manga_volume': r'^(?P<series>.+?)\s+v(?P<volume>\d+)\s*(?:\((?P<year>\d{4})\))?',

    # Comics: "Batman (1940) #001.cbr"
    'comic_issue': r'^(?P<series>.+?)\s*\((?P<year>\d{4})\)\s*#(?P<issue>\d+)',

    # Alternative: "One Piece - Chapter 123 (v12).cbz"
    'chapter': r'^(?P<series>.+?)\s*-?\s*(?:Chapter|Ch\.?)\s*(?P<chapter>\d+)',

    # Year extraction: "(2018)" or "(Digital) (2018)"
    'year': r'\((\d{4})\)',

    # Release group: "[GroupName]" or "(GroupName)"
    'group': r'[\[\(](?P<group>[^\]\)]+)[\]\)]$',
}
```

### Parsing Steps

1. **Extract from filename**:
   - Series name
   - Volume/Issue/Chapter number
   - Year (if present)
   - Release group (optional)

2. **Clean series name**:
   - Remove special characters
   - Normalize spacing
   - Handle common abbreviations

3. **Determine format**:
   - Check folder structure (Manga/ vs Comics/)
   - Look for format hints (Digital, Print)
   - Infer from patterns

4. **Extract metadata from folder hierarchy**:
   - Top-level folder = Publisher/Category
   - Parent folder = Series name
   - Filename = Volume/Issue

---

## Enrichment Workflow

### Phase 1: Scan & Parse

```
For each comic file:
├── Parse filename → Extract basic metadata
├── Check if metadata already exists in DB
│   └── If yes: Skip (unless force refresh)
├── Determine format (Manga vs Western)
└── Queue for online lookup
```

### Phase 2: Online Lookup

```
For each queued item:
├── Determine best API (AniList for manga, Comic Vine for Western)
├── Search by series name
│   ├── Match results (fuzzy matching)
│   ├── Select best match (score-based)
│   └── If no match: Try synonyms/alternative titles
├── Fetch full metadata
├── Map to database schema
└── Save to database
```

### Phase 3: Post-Processing

```
After enrichment:
├── Download cover images (if missing)
├── Group by series (auto-detect collections)
├── Sort by volume/issue number
├── Generate series metadata (aggregate from volumes)
└── Update search index
```

---

## Implementation Plan

### Database Schema Additions

**Series Table** (Already exists, enhance):
```sql
ALTER TABLE series ADD COLUMN:
- external_id (AniList ID, Comic Vine ID)
- external_source (enum: anilist, comicvine, openlibrary)
- genres (JSON array)
- tags (JSON array)
- synopsis (TEXT)
- average_score (FLOAT)
- popularity (INT)
- status (enum: ongoing, completed, hiatus, cancelled)
- start_date (DATE)
- end_date (DATE)
- cover_url (TEXT)
- last_enriched_at (TIMESTAMP)
```

**Comic Table** (Enhance existing):
```sql
ALTER TABLE comics ADD COLUMN:
- external_id (Issue ID from Comic Vine, etc.)
- release_group (TEXT) -- e.g., "danke-Empire", "nao"
- scan_quality (enum: digital, print, scan, unknown)
- language_code (TEXT) -- e.g., "en", "ja"
- parsed_from_filename (BOOLEAN) -- Track if metadata is inferred
```

### API Client Structure

```python
# src/metadata/sources/base.py
class MetadataSource(ABC):
    """Base class for metadata providers"""

    @abstractmethod
    async def search(self, query: str, **filters) -> List[SearchResult]:
        """Search for series by name"""
        pass

    @abstractmethod
    async def get_series(self, external_id: str) -> SeriesMetadata:
        """Get full series metadata by ID"""
        pass

    @abstractmethod
    async def get_volume(self, series_id: str, volume_num: int) -> VolumeMetadata:
        """Get volume-specific metadata"""
        pass

# src/metadata/sources/anilist.py
class AniListSource(MetadataSource):
    """AniList API client for manga metadata"""

    async def search(self, query: str, **filters):
        # GraphQL query to search
        ...

    async def get_series(self, anilist_id: str):
        # Fetch full series data
        ...

# src/metadata/sources/comicvine.py
class ComicVineSource(MetadataSource):
    """Comic Vine API client for Western comics"""

    async def search(self, query: str, **filters):
        # REST API search
        ...

    async def get_series(self, cv_id: str):
        # Fetch full series data
        ...
```

### Filename Parser

```python
# src/metadata/parser.py
class FilenameParser:
    """Parse comic filenames to extract metadata"""

    def parse(self, filename: str, folder_path: str) -> ParsedMetadata:
        """
        Extract metadata from filename and folder structure

        Returns:
            ParsedMetadata with fields:
            - series_name
            - volume/issue/chapter number
            - year
            - release_group
            - format_hint (manga, comic, etc.)
            - confidence (0.0-1.0)
        """

        # Try multiple patterns
        for pattern_name, regex in PATTERNS.items():
            match = re.match(regex, filename)
            if match:
                return self._build_metadata(match, pattern_name)

        # Fallback: basic parsing
        return self._fallback_parse(filename, folder_path)

    def extract_series_name(self, filename: str) -> str:
        """Clean and normalize series name"""
        # Remove volume/issue numbers
        # Remove year, group, format hints
        # Normalize spacing, capitalization
        ...
```

### Enrichment Service

```python
# src/metadata/enrichment.py
class MetadataEnricher:
    """Automated metadata enrichment service"""

    def __init__(self, db, sources: List[MetadataSource]):
        self.db = db
        self.sources = sources  # [AniListSource, ComicVineSource, ...]
        self.parser = FilenameParser()

    async def enrich_library(self, library_id: int, force: bool = False):
        """
        Enrich all comics in a library

        Args:
            library_id: Library to enrich
            force: Re-enrich even if metadata exists
        """
        comics = self.db.get_comics_in_library(library_id)

        for comic in comics:
            # Skip if already enriched (unless force)
            if comic.metadata_source and not force:
                continue

            await self.enrich_comic(comic)

    async def enrich_comic(self, comic: Comic):
        """Enrich a single comic"""

        # Step 1: Parse filename
        parsed = self.parser.parse(comic.filename, comic.folder.path)

        # Step 2: Determine format (manga vs Western)
        format_type = self._detect_format(comic, parsed)

        # Step 3: Select appropriate source
        source = self._select_source(format_type)

        # Step 4: Search for series
        results = await source.search(parsed.series_name)

        # Step 5: Match best result
        best_match = self._match_series(results, parsed)

        if best_match:
            # Step 6: Fetch full metadata
            series_meta = await source.get_series(best_match.id)
            volume_meta = await source.get_volume(
                best_match.id,
                parsed.volume_number
            )

            # Step 7: Update database
            self._update_comic(comic, series_meta, volume_meta, parsed)
        else:
            # Fallback: Use parsed data only
            self._update_comic_from_parse(comic, parsed)

    def _detect_format(self, comic: Comic, parsed: ParsedMetadata) -> str:
        """Detect if manga or Western comic"""

        # Check folder structure
        if 'manga' in comic.folder.path.lower():
            return 'manga'
        if 'comics' in comic.folder.path.lower():
            return 'comic'

        # Check filename patterns
        if parsed.pattern_name == 'manga_volume':
            return 'manga'
        if parsed.pattern_name == 'comic_issue':
            return 'comic'

        # Default: manga (more common in user's collection)
        return 'manga'

    def _select_source(self, format_type: str) -> MetadataSource:
        """Select best metadata source for format"""
        if format_type == 'manga':
            return self.sources['anilist']
        else:
            return self.sources['comicvine']

    def _match_series(self, results: List[SearchResult], parsed: ParsedMetadata):
        """Find best matching series from search results"""

        # Fuzzy matching (using rapidfuzz)
        from rapidfuzz import fuzz

        best_score = 0
        best_match = None

        for result in results:
            # Try all title variants
            titles = [
                result.title_romaji,
                result.title_english,
                result.title_native,
                *result.synonyms
            ]

            for title in titles:
                if not title:
                    continue

                # Fuzzy match
                score = fuzz.ratio(
                    parsed.series_name.lower(),
                    title.lower()
                )

                if score > best_score:
                    best_score = score
                    best_match = result

        # Require minimum confidence (80%)
        if best_score >= 80:
            return best_match

        return None
```

---

## Admin UI Integration

### Metadata Enrichment Page

**Location**: `/admin/metadata-enrichment`

**Features**:
1. **Library Selection**: Choose which library to enrich
2. **Preview Mode**: Show what would be changed (dry run)
3. **Batch Processing**: Enrich in batches (100 comics at a time)
4. **Progress Tracking**: Real-time progress bar
5. **Review Matches**: Manually approve/reject uncertain matches
6. **Statistics**: Success rate, failed matches, enriched count

**UI Mockup**:
```
┌────────────────────────────────────────────────────────────┐
│ Metadata Enrichment                                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Library: [Manga Collection ▼]                             │
│                                                            │
│ ┌─ Settings ──────────────────────────────────────────┐   │
│ │ ☑ Enable AniList lookup                             │   │
│ │ ☑ Enable Comic Vine lookup                          │   │
│ │ ☑ Download cover images                             │   │
│ │ ☑ Create series entries                             │   │
│ │ ☐ Force re-enrichment (overwrite existing)          │   │
│ │                                                      │   │
│ │ Confidence Threshold: [────●─────] 80%              │   │
│ │ Batch Size: [100_] comics                           │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                            │
│ [Preview Changes]  [Start Enrichment]                     │
│                                                            │
├────────────────────────────────────────────────────────────┤
│ Preview (Dry Run)                                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ✅ High Confidence (1,234 comics - 80-100%)               │
│ ⚠️  Medium Confidence (567 comics - 60-79%)               │
│ ❌ No Match Found (89 comics)                             │
│ ℹ️  Already Enriched (30,209 comics)                      │
│                                                            │
│ Total: 41,099 comics                                       │
│                                                            │
│ [View Details] [Export Report]                            │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Review Uncertain Matches

**For medium-confidence matches (60-79%)**:

```
┌────────────────────────────────────────────────────────────┐
│ Review Match: Accomplishments of the Duke's Daughter v01   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Parsed from filename:                                      │
│ ━━━━━━━━━━━━━━━━━━━                                       │
│ Series: "Accomplishments of the Duke's Daughter"          │
│ Volume: 01                                                 │
│ Year: 2018                                                 │
│                                                            │
│ Suggested Match (AniList - 75% confidence):                │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━        │
│ ┌────────┐                                                 │
│ │ Cover  │  Koushaku Reijou no Tashinami                  │
│ │ Image  │  公爵令嬢の嗜み                                │
│ │        │                                                 │
│ └────────┘  English: Accomplishments of the Duke's Daughter│
│            Status: Hiatus                                  │
│            Format: Manga                                   │
│            Genres: Drama, Fantasy, Romance                 │
│            Score: 76% (8,580 users)                        │
│            Volumes: 8                                      │
│                                                            │
│ [✓ Accept Match]  [Search Again]  [Skip]  [Edit Manually] │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Performance Considerations

### Rate Limiting

**Strategy**: Token bucket algorithm

```python
class RateLimiter:
    """Rate limiter for API calls"""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests  # e.g., 90
        self.time_window = time_window    # e.g., 60 seconds
        self.tokens = max_requests
        self.last_refill = time.time()

    async def acquire(self):
        """Wait until a token is available"""
        while self.tokens <= 0:
            await self._refill()
            await asyncio.sleep(0.1)

        self.tokens -= 1

    async def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill

        if elapsed >= self.time_window:
            self.tokens = self.max_requests
            self.last_refill = now
```

**Usage**:
```python
anilist_limiter = RateLimiter(max_requests=90, time_window=60)

async def fetch_from_anilist(query):
    await anilist_limiter.acquire()
    # Make API call
    ...
```

### Batch Processing

**Strategy**: Process in chunks with progress tracking

```python
async def enrich_library_batched(library_id: int, batch_size: int = 100):
    """Process library in batches"""

    comics = get_comics_in_library(library_id)
    total = len(comics)

    for i in range(0, total, batch_size):
        batch = comics[i:i+batch_size]

        # Process batch
        tasks = [enrich_comic(comic) for comic in batch]
        await asyncio.gather(*tasks)

        # Update progress
        progress = min(i + batch_size, total)
        yield {
            'processed': progress,
            'total': total,
            'percent': (progress / total) * 100
        }

        # Brief pause between batches
        await asyncio.sleep(1)
```

### Caching

**Strategy**: Cache API responses to avoid re-fetching

```python
from functools import lru_cache
import hashlib

class CachedMetadataSource:
    """Wrapper to add caching to metadata sources"""

    def __init__(self, source: MetadataSource, cache_dir: Path):
        self.source = source
        self.cache_dir = cache_dir

    async def search(self, query: str, **filters):
        # Generate cache key
        cache_key = self._cache_key('search', query, filters)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Check cache
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 86400:  # 24 hours
                return json.loads(cache_file.read_text())

        # Fetch from API
        result = await self.source.search(query, **filters)

        # Save to cache
        cache_file.write_text(json.dumps(result))

        return result

    def _cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_str = json.dumps(args, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
```

---

## Configuration

### Admin Settings Page

**Location**: `/admin/settings/metadata`

**Options**:
- **Enable Metadata Enrichment**: On/Off toggle
- **Default Source**: AniList, Comic Vine, Auto-detect
- **Confidence Threshold**: 0-100% (default: 80%)
- **Auto-enrich on scan**: Enable/disable automatic enrichment
- **Download covers**: Enable/disable cover downloads
- **API Keys**:
  - Comic Vine API Key
  - (AniList doesn't require key)

### Config File

```yaml
# config.yml
metadata:
  enrichment:
    enabled: true
    auto_enrich_on_scan: true
    confidence_threshold: 80
    batch_size: 100

  sources:
    anilist:
      enabled: true
      rate_limit: 90  # requests per minute

    comicvine:
      enabled: true
      api_key: "YOUR_API_KEY_HERE"
      rate_limit: 200  # requests per hour

    openlibrary:
      enabled: false

  covers:
    download: true
    overwrite: false
    max_size: 2048  # pixels
    format: "jpeg"
    quality: 90

  cache:
    enabled: true
    ttl: 86400  # 24 hours
    max_size_mb: 500
```

---

## Implementation Timeline

### Phase 1: Foundation (Week 1)
- [ ] Database schema updates
- [ ] Filename parser implementation
- [ ] Basic metadata structures

### Phase 2: API Clients (Week 2)
- [ ] AniList API client
- [ ] Comic Vine API client
- [ ] Rate limiting & caching

### Phase 3: Enrichment Service (Week 3)
- [ ] Enrichment workflow
- [ ] Fuzzy matching logic
- [ ] Batch processing

### Phase 4: Admin UI (Week 4)
- [ ] Enrichment page UI
- [ ] Preview/dry-run mode
- [ ] Manual review interface
- [ ] Progress tracking

### Phase 5: Testing & Optimization (Week 5)
- [ ] Test with real collection (41k items)
- [ ] Performance optimization
- [ ] Error handling & retries
- [ ] Documentation

---

## Success Metrics

**Goals for 41,099 item collection**:
- **80%+ Auto-enrichment**: Successful automatic matching
- **15% Manual Review**: Medium-confidence matches reviewed
- **5% Failed**: No match found (manual entry required)
- **Performance**: < 10 hours for full enrichment (with rate limits)

**Quality Metrics**:
- Metadata accuracy: 95%+
- Cover image success rate: 90%+
- Series grouping accuracy: 95%+

---

## Future Enhancements

1. **Machine Learning**: Train model on user corrections to improve matching
2. **Community Database**: Share enriched metadata with other users
3. **Multiple Sources**: Cross-reference multiple APIs for accuracy
4. **Custom Rules**: User-defined parsing patterns for unique collections
5. **Scheduled Re-enrichment**: Periodically update metadata for ongoing series

---

## Example: Enrichment Result

**Before** (Filename only):
```
Series: Accomplishments of the Duke's Daughter
Volume: 01
Filename: Accomplishments of the Duke's Daughter v01 (2018) (Digital) (danke-Empire).cbz
```

**After** (Enriched from AniList):
```
Series: Koushaku Reijou no Tashinami
English Title: Accomplishments of the Duke's Daughter
Native Title: 公爵令嬢の嗜み
Synonyms: Common Sense of a Duke's Daughter, Simply Good Sense for a Duke's Daughter
Format: Manga
Status: Hiatus
Genres: Drama, Fantasy, Romance
Tags: Female Protagonist, Nobility, Politics, Reincarnation, Otome Game
Synopsis: Iris, the "Accomplishments of the Duke's Daughter," is suddenly hit...
Start Date: 2015-12-22
Volume: 01 of 8+
Year: 2018
Publisher: Seven Seas Entertainment
Language: English
Release Group: danke-Empire
Scan Quality: Digital
Average Score: 76%
Popularity: 8,580 users
Cover URL: https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx97981-x...
External ID: 97981 (AniList)
```

---

**Last Updated**: 2025-11-09
**Status**: Ready for Implementation
**Priority**: High
