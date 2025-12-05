# Web UI Documentation

## Overview

The SvelteKit frontend provides a modern web interface for browsing and reading comics. Located in `webui/`.

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | SvelteKit | 2.x |
| Styling | TailwindCSS | 3.x |
| State Management | Svelte Stores | Native |
| Data Fetching | TanStack Query | 5.x |
| Build Tool | Vite | 5.x |
| Package Manager | npm/pnpm | - |

---

## Project Structure

```
webui/
├── src/
│   ├── routes/                 # Page routes (file-based routing)
│   │   ├── +layout.svelte      # Root layout
│   │   ├── +page.svelte        # Home page
│   │   ├── +page.server.js     # SSR data loading
│   │   ├── admin/              # Admin pages
│   │   ├── comic/              # Comic reader
│   │   ├── continue-reading/   # Continue reading list
│   │   ├── favorites/          # User favorites
│   │   ├── search/             # Search interface
│   │   └── series/             # Series browser
│   ├── lib/
│   │   ├── api/               # API client modules
│   │   ├── components/        # Reusable components
│   │   ├── stores/            # Svelte stores
│   │   ├── themes/            # Theme configuration
│   │   └── utils/             # Helper functions
│   └── app.html               # HTML template
├── static/                     # Static assets
├── package.json
├── svelte.config.js
├── tailwind.config.js
└── vite.config.js
```

---

## Routes (`src/routes/`)

### `/` - Home/Library Browser

**Files:**
- `+page.svelte` - Main library view
- `+page.server.js` - Server-side data fetching

**Features:**
- Library selection
- Folder navigation
- Comic grid/list view
- Sorting options

---

### `/admin/` - Admin Dashboard

**File:** `admin/+page.svelte`

**Features:**
- Server status overview
- Quick actions

---

### `/admin/libraries` - Library Management

**Files:** `admin/libraries/+page.svelte`

**Features:**
- Create/edit/delete libraries
- Trigger library scans
- View scan progress
- Configure scan intervals

---

### `/admin/scanners` - Scanner Configuration

**Files:** `admin/scanners/+page.svelte`

**Features:**
- View available scanners
- Configure scanner per library
- Set credentials (API keys)
- Adjust confidence thresholds
- Trigger metadata scans
- View scan progress

---

### `/admin/settings` - Server Settings

**Files:** `admin/settings/+page.svelte`

**Features:**
- General server settings
- Feature flags
- Database configuration

---

### `/comic/[id]` - Comic Reader

**Files:** `comic/[id]/+page.svelte`

**Features:**
- Full-page reading experience
- Page navigation (arrow keys, swipe)
- Reading direction toggle (LTR/RTL)
- Progress tracking (auto-save)
- Bookmarks
- Fit modes (width, height, original)
- Page thumbnails

**Route Parameter:** `id` - Comic ID

---

### `/continue-reading/` - Continue Reading List

**Files:** `continue-reading/+page.svelte`

**Features:**
- Resume from last position
- Progress indicators
- Remove from list

---

### `/favorites/` - User Favorites

**Files:** `favorites/+page.svelte`

**Features:**
- Favorited comics grid
- Add/remove favorites
- Filter by library

---

### `/search/` - Search Interface

**Files:** `search/+page.svelte`

**Features:**
- Global search
- Advanced search with filters
- Search history
- Saved searches

---

### `/series/[name]` - Series Browser

**Files:** `series/[name]/+page.svelte`

**Features:**
- Series metadata display
- Volume listing
- Reading progress per volume
- Cover art

**Route Parameter:** `name` - URL-encoded series name

---

## Components (`src/lib/components/`)

### Layout Components

**`layout/`**
- `Navbar.svelte` - Top navigation bar
- `Sidebar.svelte` - Side navigation (mobile)
- `Footer.svelte` - Page footer

### Common Components

**`common/`**
- `Button.svelte` - Styled button
- `Card.svelte` - Content card
- `Input.svelte` - Form input
- `Modal.svelte` - Modal dialog
- `Spinner.svelte` - Loading indicator
- `Toast.svelte` - Notification toast

### Comic Components

**`comic/`**
- `ComicCard.svelte` - Comic cover card with metadata
- `ComicGrid.svelte` - Grid layout for comics
- `ComicList.svelte` - List layout for comics

### Library Components

**`library/`**
- `LibrarySelector.svelte` - Library dropdown
- `FolderBreadcrumb.svelte` - Navigation breadcrumb
- `FolderTree.svelte` - Hierarchical folder view

### Reader Components

**`reader/`**
- `PageDisplay.svelte` - Current page display
- `PageNav.svelte` - Page navigation controls
- `ThumbnailStrip.svelte` - Page thumbnails
- `ReaderToolbar.svelte` - Reader controls

### Search Components

**`search/`**
- `SearchBar.svelte` - Search input
- `SearchResults.svelte` - Results display
- `AdvancedFilters.svelte` - Filter controls

### Settings Components

**`settings/`**
- `ThemeToggle.svelte` - Dark/light mode
- `SettingsForm.svelte` - Settings editor

---

## API Client (`src/lib/api/`)

### client.js

Base API client with fetch wrapper.

```javascript
// Base URL detection
const API_BASE = typeof window !== 'undefined' 
    ? window.location.origin 
    : 'http://localhost:8081';

// Fetch wrapper with error handling
export async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
}
```

---

### libraries.js

Library API calls.

```javascript
export async function getLibraries() {
    return apiRequest('/v2/libraries');
}

export async function getLibrary(id) {
    return apiRequest(`/v2/library/${id}/info`);
}

export async function createLibrary(data) {
    return apiRequest('/v2/libraries', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function scanLibrary(id) {
    return apiRequest(`/v2/libraries/${id}/scan`, {
        method: 'POST'
    });
}

export async function getScanProgress(id) {
    return apiRequest(`/v2/libraries/${id}/scan/progress`);
}
```

---

### comics.js

Comic API calls.

```javascript
export async function getComic(libraryId, comicId) {
    return apiRequest(`/v2/library/${libraryId}/comic/${comicId}/remote`);
}

export async function getComicPage(libraryId, comicId, pageNum) {
    return `${API_BASE}/library/${libraryId}/comic/${comicId}/page/${pageNum}`;
}

export async function getCoverUrl(hash, format = 'webp') {
    return `${API_BASE}/v2/cover/${hash}?format=${format}`;
}

export async function updateProgress(libraryId, comicId, page) {
    return apiRequest(`/library/${libraryId}/comic/${comicId}/setCurrentPage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `page=${page}`
    });
}
```

---

### config.js

Configuration API calls.

```javascript
export async function getConfig() {
    return apiRequest('/api/v2/config');
}

export async function updateConfig(config) {
    return apiRequest('/api/v2/config', {
        method: 'PUT',
        body: JSON.stringify(config)
    });
}
```

---

### search.js

Search API calls.

```javascript
export async function search(libraryId, query) {
    return apiRequest(`/v2/library/${libraryId}/search?q=${encodeURIComponent(query)}`);
}

export async function advancedSearch(libraryId, query, limit = 100, offset = 0) {
    return apiRequest(`/v2/library/${libraryId}/search/advanced`, {
        method: 'POST',
        body: JSON.stringify({ query, limit, offset })
    });
}

export async function getSearchFields(libraryId) {
    return apiRequest(`/v2/library/${libraryId}/search/fields`);
}
```

---

### scanners.js

Scanner API calls.

```javascript
export async function getAvailableScanners() {
    return apiRequest('/v2/scanners/available');
}

export async function getLibraryScannerConfigs() {
    return apiRequest('/v2/scanners/libraries');
}

export async function configureLibraryScanner(libraryId, config) {
    return apiRequest(`/v2/scanners/libraries/${libraryId}/configure`, {
        method: 'PUT',
        body: JSON.stringify(config)
    });
}

export async function scanLibraryMetadata(libraryId, options = {}) {
    return apiRequest('/v2/scanners/scan/library', {
        method: 'POST',
        body: JSON.stringify({
            library_id: libraryId,
            ...options
        })
    });
}

export async function getScannerProgress(libraryId) {
    return apiRequest(`/v2/scanners/scan/library/${libraryId}/progress`);
}
```

---

### favorites.js

Favorites API calls.

```javascript
export async function getFavorites() {
    return apiRequest('/api/v2/favorites');
}

export async function addFavorite(libraryId, comicId) {
    return apiRequest('/api/v2/favorites', {
        method: 'POST',
        body: JSON.stringify({ library_id: libraryId, comic_id: comicId })
    });
}

export async function removeFavorite(id) {
    return apiRequest(`/api/v2/favorites/${id}`, {
        method: 'DELETE'
    });
}
```

---

## Stores (`src/lib/stores/`)

### theme.js

Theme management with localStorage persistence.

```javascript
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const STORAGE_KEY = 'yaclib-theme';

function createThemeStore() {
    // Load from localStorage
    const stored = browser ? localStorage.getItem(STORAGE_KEY) : null;
    const initial = stored || 'system';
    
    const { subscribe, set, update } = writable(initial);
    
    return {
        subscribe,
        set: (value) => {
            set(value);
            if (browser) {
                localStorage.setItem(STORAGE_KEY, value);
                applyTheme(value);
            }
        },
        toggle: () => {
            update(current => {
                const next = current === 'dark' ? 'light' : 'dark';
                if (browser) {
                    localStorage.setItem(STORAGE_KEY, next);
                    applyTheme(next);
                }
                return next;
            });
        }
    };
}

function applyTheme(theme) {
    if (theme === 'dark' || 
        (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

export const theme = createThemeStore();
```

---

### library.js

Current library state.

```javascript
import { writable, derived } from 'svelte/store';

export const currentLibrary = writable(null);
export const currentFolder = writable(null);
export const libraries = writable([]);

export const currentLibraryName = derived(
    [currentLibrary, libraries],
    ([$currentLibrary, $libraries]) => {
        if (!$currentLibrary) return null;
        const lib = $libraries.find(l => l.id === $currentLibrary);
        return lib?.name;
    }
);
```

---

### reader.js

Reader state and preferences.

```javascript
import { writable } from 'svelte/store';

export const readerSettings = writable({
    fitMode: 'width',      // width, height, original
    direction: 'ltr',      // ltr, rtl
    continuous: false,     // Continuous scroll
    preloadPages: 2        // Pages to preload
});

export const currentPage = writable(0);
export const totalPages = writable(0);
```

---

### search.js

Search state and history.

```javascript
import { writable } from 'svelte/store';

export const searchQuery = writable('');
export const searchResults = writable([]);
export const isSearching = writable(false);
```

---

### advancedSearch.js

Advanced search with localStorage persistence.

```javascript
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const HISTORY_KEY = 'yaclib-search-history';
const SAVED_KEY = 'yaclib-saved-searches';

function createHistoryStore() {
    const stored = browser ? JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') : [];
    const { subscribe, set, update } = writable(stored);
    
    return {
        subscribe,
        add: (query) => {
            update(history => {
                const filtered = history.filter(q => q !== query);
                const updated = [query, ...filtered].slice(0, 20);
                if (browser) {
                    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
                }
                return updated;
            });
        },
        clear: () => {
            set([]);
            if (browser) {
                localStorage.removeItem(HISTORY_KEY);
            }
        }
    };
}

export const searchHistory = createHistoryStore();

function createSavedSearchesStore() {
    const stored = browser ? JSON.parse(localStorage.getItem(SAVED_KEY) || '[]') : [];
    const { subscribe, set, update } = writable(stored);
    
    return {
        subscribe,
        save: (name, query) => {
            update(saved => {
                const updated = [...saved, { name, query, createdAt: Date.now() }];
                if (browser) {
                    localStorage.setItem(SAVED_KEY, JSON.stringify(updated));
                }
                return updated;
            });
        },
        remove: (name) => {
            update(saved => {
                const updated = saved.filter(s => s.name !== name);
                if (browser) {
                    localStorage.setItem(SAVED_KEY, JSON.stringify(updated));
                }
                return updated;
            });
        }
    };
}

export const savedSearches = createSavedSearchesStore();
```

---

### preferences.js

User preferences.

```javascript
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const PREFS_KEY = 'yaclib-preferences';

const defaults = {
    gridSize: 'medium',    // small, medium, large
    sortOrder: 'name',     // name, date, progress
    viewMode: 'grid',      // grid, list
    showFilters: false
};

function createPreferencesStore() {
    const stored = browser ? JSON.parse(localStorage.getItem(PREFS_KEY) || 'null') : null;
    const initial = { ...defaults, ...stored };
    
    const { subscribe, set, update } = writable(initial);
    
    return {
        subscribe,
        set: (value) => {
            const merged = { ...defaults, ...value };
            set(merged);
            if (browser) {
                localStorage.setItem(PREFS_KEY, JSON.stringify(merged));
            }
        },
        update: (updater) => {
            update(current => {
                const updated = updater(current);
                if (browser) {
                    localStorage.setItem(PREFS_KEY, JSON.stringify(updated));
                }
                return updated;
            });
        }
    };
}

export const preferences = createPreferencesStore();
```

---

### user.js

User session state.

```javascript
import { writable } from 'svelte/store';

export const currentUser = writable(null);
export const isAuthenticated = writable(false);
```

---

## State Management Patterns

### UI State
Component-local using Svelte's reactive declarations.

```svelte
<script>
    let isOpen = false;
    let selectedItem = null;
    
    $: hasSelection = selectedItem !== null;
</script>
```

### User Preferences
Svelte stores with localStorage persistence.

```javascript
// Store updates automatically persist
preferences.update(p => ({ ...p, gridSize: 'large' }));
```

### Server Data
TanStack Query for caching and synchronization.

```javascript
import { createQuery } from '@tanstack/svelte-query';

const librariesQuery = createQuery({
    queryKey: ['libraries'],
    queryFn: () => getLibraries(),
    staleTime: 15 * 60 * 1000,    // 15 minutes
    cacheTime: 30 * 60 * 1000     // 30 minutes
});
```

---

## Development

### Setup

```bash
cd webui
npm install
npm run dev
```

### Environment Variables

```bash
VITE_API_URL=http://localhost:8081  # Backend URL (optional)
```

### Build

```bash
npm run build
npm run preview  # Preview production build
```

### Linting

```bash
npm run lint
npm run format
```
