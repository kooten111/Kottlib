  YACReader Server API Documentation

  Overview

  YACReader Server provides two API versions:
  - V1 API: HTML template-based (legacy, used by older iOS apps)
  - V2 API: JSON-based (modern, used by current iOS/Android apps)
  - Server Version: 2.1

  ---
  Authentication & Session Management

  V1 API Session

  Session Creation:
  - First request to / creates a session
  - Session data sent via POST body with format:
  deviceType:ipad
  displayType:@2x
  comics:hash1\thash2\thash3

  Session Parameters:
  - deviceType: Device identifier (e.g., "ipad", "android")
  - displayType: Screen resolution ("@2x" for retina, "@1x" for standard)
  - comics: Tab-separated list of comic hashes already on device

  V2 API Session

  Token-Based Authentication:
  - Uses x-request-id header for session identification
  - No cookies required
  - Session persists comic state for remote reading

  Example Header:
  x-request-id: <unique-session-token>

  ---
  V1 API Endpoints

  Base Path: /

  All V1 endpoints (except /sync) require an active session.

  1. Get Libraries

  Endpoint: POST /
  Response: HTML page with library list
  Session: Creates new session

  Response Fields:
  - Libraries with ID and name

  ---
  2. Browse Folder

  Endpoint: GET /library/{libraryId}/folder/{folderId}
  Query Parameters:
  - page: Page number (optional, default: 0)
  - up: Navigation flag (optional)

  Response: HTML page with folder contents (24 items per page)

  Folder Items Include:
  - Subfolders with cover images
  - Comics with metadata
  - Navigation breadcrumbs
  - Pagination controls
  - Alpha-numeric index

  ---
  3. Get Folder Info (Recursive)

  Endpoint: GET /library/{libraryId}/folder/{folderId}/info
  Response: Plain text, one comic per line
  Format:
  /library/{libraryId}/comic/{comicId}:{fileName}:{fileSize}\r\n

  Behavior: Recursively lists all comics in folder and subfolders

  ---
  4. Get Comic Download Info

  Endpoint: GET /library/{libraryId}/comic/{comicId}
  Response: Plain text
  Format:
  fileName:{name}\r\n
  fileSize:{bytes}\r\n

  ---
  5. Open Comic (Full Info)

  Endpoint: GET /library/{libraryId}/comic/{comicId}/info
  Purpose: Get full comic metadata and prepare for download
  Response: Plain text format (see Comic Data Format section)

  ---
  6. Open Comic for Remote Reading

  Endpoint: GET /library/{libraryId}/comic/{comicId}/remote
  Purpose: Open comic for server-side page serving
  Response: Plain text with comic info + navigation
  Additional Fields:
  previousComic:{id}\r\n
  nextComic:{id}\r\n

  ---
  7. Get Comic Page

  Endpoint: GET /library/{libraryId}/comic/{comicId}/page/{pageNumber}
  Purpose: Download a specific page for offline reading
  Response: JPEG image

  ---
  8. Get Comic Page (Remote Reading)

  Endpoint: GET /library/{libraryId}/comic/{comicId}/page/{pageNumber}/remote
  Purpose: Stream page for online reading
  Response: JPEG image (chunked transfer)

  ---
  9. Get Cover Image

  Endpoint: GET /library/{libraryId}/cover/{hash}.jpg
  Query Parameters:
  - folderCover: Set to "true" for folder covers (optional)

  Response: JPEG image
  Sizes:
  - Standard (@1x): 80x120px
  - Retina (@2x): 160x240px

  Features:
  - Auto-scaled to fit dimensions
  - Black letterboxing for aspect ratio preservation
  - Folder overlay icon for folder covers

  ---
  10. Update Comic Progress

  Endpoint: POST /library/{libraryId}/comic/{comicId}/update
  Body Format:
  currentPage:{pageNumber}\n
  Response: "OK"

  ---
  11. Sync From Client

  Endpoint: POST /sync
  Purpose: Batch update reading progress from mobile app
  No Session Required

  Body Format (one per line):
  {libraryId}\t{comicId}\t{hash}\t{currentPage}\t{rating}\n

  Client Version 2.1+ includes rating

  Response: "OK"

  ---
  V2 API Endpoints

  Base Path: /v2

  All V2 endpoints return JSON and use x-request-id header.

  1. Get Server Version

  Endpoint: GET /v2/version
  Response: Plain text (e.g., "2.1")

  ---
  2. Get Libraries

  Endpoint: GET /v2/libraries
  Response: JSON array

  Example:
  [
    {
      "name": "My Comics",
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000"
    }
  ]

  ---
  3. Get Folder Contents

  Endpoint: GET /v2/library/{libraryId}/folder/{folderId}/content
  Response: JSON array of folders and comics

  Folder Object:
  {
    "type": "folder",
    "id": "123",
    "library_id": "1",
    "library_uuid": "550e8400-...",
    "folder_name": "Marvel",
    "num_children": 42,
    "first_comic_hash": "abc123...",
    "finished": false,
    "completed": false,
    "custom_image": "",
    "file_type": 0,
    "added": 1234567890,
    "updated": 1234567890,
    "parent_id": "1",
    "path": "/Marvel"
  }

  Comic Object (Basic):
  {
    "type": "comic",
    "id": "456",
    "comic_info_id": "456",
    "parent_id": "123",
    "library_id": "1",
    "library_uuid": "550e8400-...",
    "file_name": "Amazing Spider-Man #001.cbz",
    "file_size": "15728640",
    "hash": "abc123...def456...size",
    "path": "/Marvel/Amazing Spider-Man #001.cbz",
    "current_page": 5,
    "num_pages": 24,
    "read": false,
    "manga": false,
    "file_type": 0,
    "cover_size_ratio": 1.5,
    "number": 1,
    "cover_page": 0,
    "title": "Amazing Spider-Man",
    "universal_number": "1",
    "last_time_opened": 1234567890,
    "has_been_opened": true,
    "added": 1234567890
  }

  ---
  4. Get Folder Info (Metadata)

  Endpoint: GET /v2/library/{libraryId}/folder/{folderId}/info
  Purpose: Recursive list of all comics in folder tree
  Response: Same as folder content but recursive

  ---
  5. Get Folder Metadata

  Endpoint: GET /v2/library/{libraryId}/folder/{folderId}/metadata
  Added: Version 9.14
  Response: JSON with folder metadata

  ---
  6. Get Comic Full Info

  Endpoint: GET /v2/library/{libraryId}/comic/{comicId}/fullinfo
  Response: JSON object with complete metadata

  Full Comic Object (extends Basic):
  {
    // ... all basic fields plus:
    "volume": "1",
    "total_volume_count": 600,
    "genre": "Superhero",
    "date": "2023-01-15",
    "synopsis": "Peter Parker's adventures...",
    "count": 600,
    "story_arc": "Brand New Day",
    "arc_number": "1",
    "arc_count": 12,
    "writer": "Dan Slott",
    "penciller": "John Romita Jr.",
    "inker": "Klaus Janson",
    "colorist": "Dean White",
    "letterer": "Joe Caramagna",
    "cover_artist": "John Romita Jr.",
    "publisher": "Marvel Comics",
    "format": "Comic",
    "color": true,
    "age_rating": "T",
    "editor": "Stephen Wacker",
    "characters": "Spider-Man, Mary Jane Watson",
    "notes": "",
    "imprint": "",
    "teams": "Avengers",
    "locations": "New York",
    "series": "Amazing Spider-Man",
    "alternate_series": "",
    "alternate_number": "",
    "alternate_count": 0,
    "language_iso": "en",
    "series_group": "",
    "main_character_or_team": "Spider-Man",
    "review": "",
    "tags": "favorite,must-read",
    "rating": 5,
    "comic_vine_id": "140154",
    "original_cover_size": "1988x3056",
    "edited": true,
    "bookmark1": 0,
    "bookmark2": 0,
    "bookmark3": 0,
    "brightness": 0,
    "contrast": 0,
    "gamma": 100,
    "image_filters_json": "{\"brightness\":0,\"contrast\":0}",
    "last_time_image_filters_set": 1234567890,
    "last_time_cover_set": 1234567890,
    "uses_external_cover": false,
    "last_time_metadata_set": 1234567890
  }

  ---
  7. Open Comic for Download

  Endpoint: GET /v2/library/{libraryId}/comic/{comicId}
  Response: Plain text (V1 format) with comic metadata

  ---
  8. Open Comic for Remote Reading

  Endpoint: GET /v2/library/{libraryId}/comic/{comicId}/remote
  Response: Plain text with navigation info

  Additional Fields:
  previousComic:{id}\r\n
  previousComicHash:{hash}\r\n
  nextComic:{id}\r\n
  nextComicHash:{hash}\r\n

  ---
  9. Open Comic in Reading List

  Endpoint: GET /v2/library/{libraryId}/reading_list/{listId}/comic/{comicId}/remote
  Purpose: Remote reading with reading list context
  Response: Same as regular remote reading

  ---
  10. Get Comic Download Info

  Endpoint: GET /v2/library/{libraryId}/comic/{comicId}/info
  Response: JSON with download info

  ---
  11. Get Comic Page

  Endpoint: GET /v2/library/{libraryId}/comic/{comicId}/page/{pageNumber}
  Response: JPEG image

  ---
  12. Get Comic Page (Remote)

  Endpoint: GET /v2/library/{libraryId}/comic/{comicId}/page/{pageNumber}/remote
  Response: JPEG image (chunked)

  ---
  13. Get Cover Image

  Endpoint: GET /v2/library/{libraryId}/cover/{path}
  Path: Can include subdirectories (e.g., {hash}.jpg or folders/{hash}.jpg)
  Response: JPEG image (full resolution, no scaling)

  ---
  14. Update Comic Progress

  Endpoint: POST /v2/library/{libraryId}/comic/{comicId}/update
  Body Format:
  currentPage:{page}\n
  {nextComicId}\n
  {timestamp}\t{imageFiltersJson}

  Line 1: Current page
  Line 2: Next comic ID to mark as "reading" (optional)
  Line 3: Image filters update (optional, added 9.16)

  Response: "OK"

  ---
  15. Get Favorites

  Endpoint: GET /v2/library/{libraryId}/favs
  Response: JSON array of favorite comics

  ---
  16. Get Reading Comics

  Endpoint: GET /v2/library/{libraryId}/reading
  Response: JSON array of comics currently being read

  ---
  17. Get Tags

  Endpoint: GET /v2/library/{libraryId}/tags
  Response: JSON array of tags/labels

  Tag Object:
  {
    "type": "label",
    "id": "1",
    "library_id": "1",
    "library_uuid": "550e8400-...",
    "label_name": "Must Read",
    "color_id": 3
  }

  ---
  18. Get Tag Content

  Endpoint: GET /v2/library/{libraryId}/tag/{tagId}/content
  Response: JSON array of comics with this tag

  ---
  19. Get Tag Info

  Endpoint: GET /v2/library/{libraryId}/tag/{tagId}/info
  Response: JSON with tag details

  ---
  20. Get Reading Lists

  Endpoint: GET /v2/library/{libraryId}/reading_lists
  Response: JSON array of reading lists

  Reading List Object:
  {
    "type": "reading_list",
    "id": "1",
    "library_id": "1",
    "library_uuid": "550e8400-...",
    "reading_list_name": "Spider-Verse Reading Order"
  }

  ---
  21. Get Reading List Content

  Endpoint: GET /v2/library/{libraryId}/reading_list/{listId}/content
  Response: JSON array of comics in reading order

  ---
  22. Get Reading List Info

  Endpoint: GET /v2/library/{libraryId}/reading_list/{listId}/info
  Response: JSON with reading list details

  ---
  23. Search

  Endpoint: POST /v2/library/{libraryId}/search
  Added: Version 9.12
  Body: JSON with search query

  Request:
  {
    "query": "spider-man title:amazing"
  }

  Response: JSON array of matching comics and folders

  Supports YACReader Search Syntax:
  - title:value - Search in title
  - writer:name - Search by writer
  - >, <, >=, <=, == - Comparison operators
  - added > 7 - Added in last 7 days
  - Multiple terms with implicit AND

  ---
  24. Sync From Client

  Endpoint: POST /v2/sync
  Purpose: Bidirectional sync of reading progress
  Response: JSON array of more recent comics on server

  iOS Format (per line):
  {libraryId}\t{comicId}\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFiltersJson}\n

  Android Format (per line):
  u\t{libraryUUID}\t{comicId}\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{hasBeenOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFilte
  rsJson}\n

  Unknown Library Format:
  unknown\t\t{hash}\t{currentPage}\t{rating}\t{lastTimeOpened}\t{read}\t{lastTimeImageFiltersSet}\t{imageFiltersJson}\n

  Response: JSON array of comics that are more recent on server

  ---
  WebUI Status Page

  Endpoint: GET /webui
  Purpose: Browser-accessible server status page
  Response: HTML page with server info

  ---
  Data Formats

  Comic Data Format (V1 Text Format)

  Used in V1 API responses:

  comicid:{id}\r\n
  hash:{hash}\r\n
  path:{relativePath}\r\n
  numpages:{count}\r\n
  rating:{0-10}\r\n
  currentPage:{page}\r\n
  contrast:{value}\r\n
  read:{0|1}\r\n
  coverPage:{pageNum}\r\n
  title:{title}\r\n
  number:{issueNumber}\r\n
  isBis:{0|1}\r\n
  count:{totalInSeries}\r\n
  volume:{volumeNumber}\r\n
  storyArc:{arcName}\r\n
  arcNumber:{numberInArc}\r\n
  arcCount:{totalInArc}\r\n
  genere:{genre}\r\n
  writer:{names}\r\n
  penciller:{names}\r\n
  inker:{names}\r\n
  colorist:{names}\r\n
  letterer:{names}\r\n
  coverArtist:{names}\r\n
  date:{publishDate}\r\n
  publisher:{name}\r\n
  format:{format}\r\n
  color:{value}\r\n
  ageRating:{rating}\r\n
  manga:{0|1}\r\n
  synopsis:{text}\r\n
  characters:{names}\r\n
  notes:{text}\r\n
  lastTimeOpened:{timestamp}\r\n
  added:{timestamp}\r\n
  type:{fileType}\r\n
  editor:{names}\r\n
  imprint:{name}\r\n
  teams:{names}\r\n
  locations:{names}\r\n
  series:{seriesName}\r\n
  alternateSeries:{name}\r\n
  alternateNumber:{number}\r\n
  alternateCount:{count}\r\n
  languageISO:{code}\r\n
  seriesGroup:{name}\r\n
  mainCharacterOrTeam:{name}\r\n
  review:{text}\r\n
  tags:{tagList}\r\n
  imageFiltersJson:{json}\r\n
  lastTimeImageFiltersSet:{timestamp}\r\n
  lastTimeCoverSet:{timestamp}\r\n
  usesExternalCover:{0|1}\r\n
  lastTimeMetadataSet:{timestamp}\r\n

  File Type Enum

  0 = Comic (Western, LTR)
  1 = Manga (Eastern, RTL)
  2 = Western Manga (LTR manga-style)

  Image Filters JSON (v9.16+)

  Used by mobile apps to store custom image adjustments:

  {
    "brightness": 0,
    "contrast": 0,
    "gamma": 100,
    "saturation": 100
  }

  ---
  Mobile App Compatibility

  iOS App Requirements

  Minimum API: V1 or V2
  Session: Cookie-based (V1) or Token-based (V2)
  Sync Format: Tab-separated with library ID
  Remote Reading: Uses /remote endpoints
  Image Filters: Supported from iOS 3.29.0+

  Android App Requirements

  Minimum API: V2
  Session: Token-based with x-request-id header
  Sync Format: UUID-based with "u" prefix
  Remote Reading: Uses /remote endpoints
  Image Filters: Supported from Android 1.4.0+

  ---
  Important Implementation Notes

  1. Comic Hash Format

  The hash field encodes both a content hash and file size:
  - First 40 characters: Content hash (SHA1 or MD5)
  - Remaining characters: File size in bytes

  Extract file size:
  fileSize = hash.substring(40).toInt()

  2. Session Persistence

  - V1: Server tracks opened comics per session
  - V2: Server tracks remote reading state per x-request-id
  - Remote reading requires keeping comic file loaded in memory

  3. Cover Paths

  - V1: Covers scaled by server based on device display type
  - V2: Full-resolution covers, client handles scaling
  - Path: {libraryPath}/.yacreaderlibrary/covers/{hash}.jpg

  4. Page Serving

  - Pages must be loaded before serving
  - Server checks Comic::pageIsLoaded(pageNum)
  - 404 returned if page not ready
  - Use chunked transfer encoding for large pages

  5. Bidirectional Sync

  - V2 sync compares timestamps
  - Server returns comics more recent than client's version
  - Supports image filters from 9.16+
  - Supports hasBeenOpened flag from Android

  6. Image Filters (v9.16+)

  - Stored as JSON string
  - Synced between devices
  - Timestamp tracks last modification
  - Empty/null means no filters applied

  ---

● Summary & Key Takeaways

  V1 vs V2 API Differences

  | Feature                | V1 API                          | V2 API                        |
  |------------------------|---------------------------------|-------------------------------|
  | Response Format        | HTML templates + plain text     | JSON                          |
  | Session                | Cookie-based                    | Token header (x-request-id)   |
  | Mobile Support         | iOS only (older versions)       | iOS & Android                 |
  | Cover Scaling          | Server-side (80x120 or 160x240) | Client-side (full resolution) |
  | Library Identification | Legacy integer ID               | UUID + legacy ID              |
  | Metadata Completeness  | Full (text format)              | Full (JSON format)            |
  | Sync                   | One-way (client → server)       | Bidirectional                 |
  | Search                 | Not available                   | Advanced search engine        |
  | Reading Lists          | Not available                   | Full support                  |
  | Tags/Labels            | Not available                   | Full support                  |

  Critical Features for Mobile Apps

  1. Remote Reading: Both APIs support streaming pages without downloading
  2. Progress Sync: V2 provides bidirectional sync with conflict resolution
  3. Image Filters: New in 9.16, allows per-comic display preferences
  4. Navigation: Next/previous comic info provided during remote reading
  5. Reading Lists: V2 supports ordered reading lists for story arcs
  6. Search: V2 allows complex queries across metadata fields

  Recommended Implementation

  For a new backend targeting mobile apps:

  1. Implement V2 API first - It's cleaner, JSON-based, and supports both iOS and Android
  2. Focus on these essential endpoints:
    - /v2/libraries - Library listing
    - /v2/library/{id}/folder/{id}/content - Browsing
    - /v2/library/{id}/comic/{id}/remote - Remote reading
    - /v2/library/{id}/comic/{id}/page/{num}/remote - Page streaming
    - /v2/library/{id}/cover/{path} - Cover images
    - /v2/sync - Progress synchronization
    - /v2/library/{id}/reading_lists - Reading lists
    - /v2/library/{id}/search - Search
  3. V1 API is optional unless supporting very old iOS clients (pre-3.29.0)
  4. Key Implementation Details:
    - Store comics indexed by hash (first 40 chars) + file size (remaining)
    - Support UUID-based library identification for Android
    - Implement timestamp-based sync conflict resolution
    - Store image filters as JSON per comic
    - Keep track of reading state (read, reading, unread)