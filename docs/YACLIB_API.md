# YACLibrary Server API Documentation

Reverse-engineered API documentation for YACReaderLibrary Server.

## Overview

YACReaderLibrary Server uses a session-based HTTP API with two versions (v1 and v2). The server loads comics asynchronously into memory and serves pages via session cookies.

## Base Concepts

- **Session-based**: Each client gets a session cookie that tracks state
- **Asynchronous loading**: Comics are loaded in background threads
- **In-memory caching**: Pages are cached in session for fast access
- **Two API versions**: v1 (legacy) and v2 (modern, JSON-based)

## API v1 Endpoints (Legacy - Used by Mobile Apps)

### Libraries

#### `GET /`
Lists all available libraries.

**Response**: HTML page with library list
```html
<ul id="librariesList">
  <li><a href="/library/3/folder/1">Comics</a></li>
  <li><a href="/library/2/folder/1">Manga</a></li>
</ul>
```

### Folders

#### `GET /library/{libraryId}/folder/{folderId}`
Lists contents of a folder (comics and subfolders).

**Parameters**:
- `page` (query, optional): Page number for pagination

**Response**: HTML page with folder contents

### Comics

#### `GET /library/{libraryId}/comic/{comicId}`
Get basic comic information.

**Response**: Plain text key-value format
```
fileName:All You Need Is Kill v01.cbz
fileSize:93169878
```

#### `GET /library/{libraryId}/comic/{comicId}/remote`
Open a comic for remote reading. This endpoint:
1. Loads the comic file into memory (asynchronously)
2. Stores it in the session
3. Returns metadata

**IMPORTANT**: Pages won't be available immediately. Wait 2-5 seconds for loading.

**Response**: Plain text key-value format
```
library:Manga
libraryId:2
nextComic:189
comicid:188
hash:c3b0fa6a89c83f6f09a18df4306da51e3a8fe6d193169878
path:/All You Need Is Kill/All You Need Is Kill v01.cbz
numpages:207
rating:0
currentPage:1
contrast:-1
read:0
coverPage:1
manga:0
added:1758385461
type:0
```

**Metadata Fields**:
- `library`: Library name
- `libraryId`: Library ID
- `nextComic`: ID of next comic in folder (if exists)
- `previousComic`: ID of previous comic in folder (if exists)
- `comicid`: Comic ID
- `hash`: Unique hash for this comic file
- `path`: Relative path to comic file
- `numpages`: Total number of pages
- `rating`: User rating (0-5)
- `currentPage`: Last read page number
- `contrast`: Display contrast setting
- `read`: Read status (0=unread, 1=read)
- `coverPage`: Page number of cover (usually 1)
- `manga`: Manga mode flag (0=LTR, 1=RTL)
- `added`: Unix timestamp when added
- `type`: Comic type

### Pages

#### `GET /library/{libraryId}/comic/{comicId}/page/{pageNum}/remote`
Get a specific page image.

**Prerequisites**:
- Must have called `/library/{libraryId}/comic/{comicId}/remote` first
- Must wait for comic to load (2-5 seconds)
- Must use the same session (cookie)

**Parameters**:
- `pageNum`: 0-indexed page number (0 to numpages-1)

**Response**: JPEG image (Content-Type: image/jpeg)

**Error Responses**:
- `404 not found`: Comic not loaded or page not ready yet

### Covers

#### `GET /library/{libraryId}/cover/{hash}.jpg`
Get comic cover image.

**Parameters**:
- `hash`: Comic hash from metadata

**Response**: JPEG image

**Note**: This works without opening the comic first.

## Session Management

The server uses HTTP cookies for session management:

```
Set-Cookie: sessionid={uuid}; Max-Age=864000; SameSite=Lax; Version=1
```

Sessions expire after 864000 seconds (10 days).

## Typical Usage Flow

### Reading a Comic (Mobile App Flow)

```python
import requests
import time

session = requests.Session()

# 1. Open the comic
response = session.get('http://server:8080/library/2/comic/188/remote')
metadata = parse_metadata(response.text)  # Parse key:value format

# 2. Wait for loading (IMPORTANT!)
time.sleep(3)

# 3. Read pages
for page_num in range(metadata['numpages']):
    response = session.get(
        f'http://server:8080/library/2/comic/188/page/{page_num}/remote'
    )
    if response.status_code == 200:
        save_page(page_num, response.content)
```

## API v2 Endpoints (Modern)

### Libraries

#### `GET /v2/libraries`
Get all libraries (JSON format).

### Comics

#### `GET /v2/library/{libraryId}/comic/{comicId}/remote`
Open comic for remote reading (v2).

#### `GET /v2/library/{libraryId}/comic/{comicId}/page/{pageNum}/remote`
Get page image (v2).

### Additional v2 Features

- `GET /v2/library/{libraryId}/folder/{folderId}/content` - Get folder contents as JSON
- `GET /v2/library/{libraryId}/favs` - Get favorites
- `GET /v2/library/{libraryId}/reading` - Get reading list
- `GET /v2/library/{libraryId}/tags` - Get tags
- `GET /v2/library/{libraryId}/search` - Search comics
- `GET /v2/version` - Get server version

## Implementation Notes

### Asynchronous Loading

The server loads comics in background threads using Qt's threading model:

```cpp
Comic *comicFile = FactoryComic::newComic(path);
QThread *thread = new QThread();
comicFile->moveToThread(thread);
connect(thread, &QThread::started, comicFile, &Comic::process);
thread->start();
```

This means:
- `/remote` endpoint returns immediately
- Pages load asynchronously in background
- First page requests may fail with 404
- Must implement retry logic or wait

### Session Storage

Each session stores:
- Currently opened comic for download
- Currently opened comic for remote reading (separate!)
- Device type (ipad, iphone, etc.)
- Display type (@2x, @3x)
- List of comics on device (for sync)

### Security

**WARNING**: The current implementation has minimal security:
- No authentication on most endpoints
- Session-based access control only
- No HTTPS enforcement
- No rate limiting

## Server Configuration

Default settings (stored in YACReaderLibrary.ini):

```ini
[listener]
port=8080
maxRequestSize=32000000
maxMultiPartSize=32000000
cleanupInterval=10000
minThreads=50
maxThreads=1000

[sessions]
expirationTime=864000000

[templates]
cacheSize=160000
```

## Error Handling

Common errors:
- `404 not found`: Resource doesn't exist or comic not loaded yet
- `300`: Unauthorized (session invalid)
- Empty response (0 bytes): Comic still loading, page not ready

## Technology Stack

- **Framework**: QtWebApp (custom Qt-based HTTP server)
- **Language**: C++ with Qt
- **Database**: SQLite (for library metadata)
- **Image Processing**: Qt image libraries
- **Archive Support**: Built-in CBZ/CBR/PDF support
