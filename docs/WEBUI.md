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
| Package Manager | Bun | - |

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
│   │   │   ├── +page.svelte         # Admin dashboard
│   │   │   ├── libraries/+page.svelte
│   │   │   ├── scanners/+page.svelte
│   │   │   └── settings/+page.svelte
│   │   ├── browse/             # Global browse
│   │   │   └── +page.server.js
│   │   ├── comic/[libraryId]/[comicId]/
│   │   │   └── read/+page.svelte    # Comic reader
│   │   ├── library/[libraryId]/browse/[...path]/
│   │   │   ├── +page.svelte         # Library folder browser
│   │   │   └── +page.server.js
│   │   ├── continue-reading/+page.svelte
│   │   ├── favorites/+page.svelte
│   │   └── search/+page.svelte
│   ├── lib/
│   │   ├── api/               # API client modules
│   │   ├── components/        # Reusable components
│   │   ├── stores/            # Svelte stores
│   │   ├── themes/            # Theme definitions (16 themes)
│   │   ├── actions/           # Svelte actions (tooltip, etc.)
│   │   ├── server/            # Server-side utilities
│   │   └── utils/             # Helper functions
│   └── app.html               # HTML template
├── static/                     # Static assets
├── bunfig.toml                 # Bun configuration
├── package.json
├── svelte.config.js
├── tailwind.config.js
├── postcss.config.js
└── vite.config.js
```

---

## Routes (`src/routes/`)

### `/` — Home

**Files:**
- `+page.svelte` — Main landing / library overview
- `+page.server.js` — Server-side data fetching

**Features:**
- Library selection
- Continue Reading and Favorites panels
- Sidebar with library tree navigation

---

### `/browse/` — Global Browse

**Files:** `browse/+page.server.js`

---

### `/library/[libraryId]/browse/[...path]/` — Library Browser

**Files:**
- `+page.svelte` — Library folder browser
- `+page.server.js` — SSR data loading

**Features:**
- Folder navigation with breadcrumbs
- Comic grid view
- Series grouping
- Sidebar tree navigation
- Inline Favorites and Continue Reading panels

**Route Parameters:**
- `libraryId` — Library ID
- `...path` — Catch-all ID-based browse path (folder IDs; optionally a trailing comic ID)

---

### `/comic/[libraryId]/[comicId]/read/` — Comic Reader

**Files:** `read/+page.svelte`

**Features:**
- Full-page reading experience
- Page navigation (arrow keys, swipe, click)
- Reading direction toggle (LTR/RTL)
- Double-page reading mode
- Fit modes (width, height, original)
- Progress tracking (auto-save)
- Bookmarks
- Align to top on page load (fit-width/original modes)

---

### `/admin/` — Admin Dashboard

**File:** `admin/+page.svelte`

**Features:**
- Server status overview
- Quick actions

---

### `/admin/libraries` — Library Management

**File:** `admin/libraries/+page.svelte`

**Features:**
- Create/edit/delete libraries
- Trigger library scans
- View scan progress
- Configure scan intervals

---

### `/admin/scanners` — Scanner Configuration

**File:** `admin/scanners/+page.svelte`

**Features:**
- View available metadata scanners
- Configure scanner per library
- Set credentials (API keys)
- Adjust confidence thresholds
- Trigger metadata scans
- View scan progress

---

### `/admin/settings` — Server Settings

**File:** `admin/settings/+page.svelte`

**Features:**
- General server settings
- Feature flags
- Database configuration
- Search index maintenance (initialize, rebuild, status)

---

### `/continue-reading/` — Continue Reading

**File:** `continue-reading/+page.svelte`

**Features:**
- Resume from last reading position
- Progress indicators

---

### `/favorites/` — Favorites

**File:** `favorites/+page.svelte`

**Features:**
- Favorited comics grid
- Filter by library

---

### `/search/` — Search

**File:** `search/+page.svelte`

**Features:**
- Global search
- Advanced search with field-specific filters
- Search history
- Saved searches

---

### Series Navigation

There is no dedicated `/series/[libraryId]/[seriesName]/` page route.
Series selections resolve to canonical library browse URLs under:
- `/library/[libraryId]/browse/[...path]/`

Browse paths are ID-first and use folder ancestry for stable navigation.

---

## Components (`src/lib/components/`)

### Layout Components (`layout/`)

| Component | Purpose |
|-----------|---------|
| `Navbar.svelte` | Top navigation bar |
| `Sidebar.svelte` | Side navigation (mobile) |
| `HomeSidebar.svelte` | Home page sidebar with library tree and folders |
| `Footer.svelte` | Page footer |
| `LibraryTree.svelte` | Hierarchical library tree in sidebar |
| `SeriesTree.svelte` | Series tree navigation |
| `SeriesTreeNode.svelte` | Individual series tree node |
| `TreeNode.svelte` | Generic tree node component |

### Common Components (`common/`)

| Component | Purpose |
|-----------|---------|
| `BackButton.svelte` | Navigation back button |
| `Breadcrumbs.svelte` | Breadcrumb navigation |
| `Button.svelte` | Styled button |
| `Card.svelte` | Content card |
| `ConfigInput.svelte` | Configuration input for admin panels |
| `DetailHeader.svelte` | Detail page header |
| `GenreTag.svelte` | Genre/tag pill |
| `HorizontalCarousel.svelte` | Horizontal scrolling carousel |
| `InfiniteScroll.svelte` | Infinite scroll loader |
| `Input.svelte` | Form input |
| `Modal.svelte` | Modal dialog |
| `ProgressBar.svelte` | Progress indicator bar |
| `SearchAutocomplete.svelte` | Search with autocomplete dropdown |
| `SkeletonCard.svelte` | Loading skeleton placeholder |
| `StarRating.svelte` | Star rating display |

### Comic Components (`comic/`)

| Component | Purpose |
|-----------|---------|
| `ComicCard.svelte` | Comic cover card with metadata |
| `LibraryCard.svelte` | Library overview card |
| `MetadataDisplay.svelte` | Full metadata display panel |
| `ScannerMetadata.svelte` | Scanner-specific metadata display |

### Library Components (`library/`)

| Component | Purpose |
|-----------|---------|
| `CollectionCard.svelte` | Collection card display |
| `FolderCard.svelte` | Folder navigation card |
| `LibraryScannerPanel.svelte` | Scanner configuration for library |
| `SeriesCard.svelte` | Series card display |

### Reader Components (`reader/`)

| Component | Purpose |
|-----------|---------|
| `PageViewer.svelte` | Page display with fit modes and double-page support |
| `ReaderControls.svelte` | Page navigation controls |
| `ReaderMenu.svelte` | Reader settings menu overlay |
| `ReaderSettings.svelte` | Reader preferences panel |

### Search Components (`search/`)

| Component | Purpose |
|-----------|---------|
| `AdvancedSearchModal.svelte` | Visual query builder with history and saved searches |

### Series Components (`series/`)

| Component | Purpose |
|-----------|---------|
| `SeriesInfoPanel.svelte` | Series metadata and statistics panel |

### Settings Components (`settings/`)

| Component | Purpose |
|-----------|---------|
| `ThemeSelector.svelte` | Theme selection with 16 theme options |

---

## Themes (`src/lib/themes/`)

The WebUI ships with 16 built-in themes:

| Theme | File |
|-------|------|
| Argonaut | `argonaut.js` |
| Catppuccin Frappé | `catppuccin-frappe.js` |
| Catppuccin Latte | `catppuccin-latte.js` |
| Catppuccin Macchiato | `catppuccin-macchiato.js` |
| Catppuccin Mocha | `catppuccin-mocha.js` |
| Dracula | `dracula.js` |
| Gruvbox Dark | `gruvbox-dark.js` |
| Gruvbox Light | `gruvbox-light.js` |
| Kottlib Original | `kottlib-original.js` |
| Nord | `nord.js` |
| One Dark | `one-dark.js` |
| Solarized Dark | `solarized-dark.js` |
| Solarized Light | `solarized-light.js` |
| Tokyo Night | `tokyo-night.js` |
| Zinc Dark | `zinc-dark.js` |

Theme selection is managed via the `ThemeSelector` component and persisted in `localStorage`.

---

## API Client (`src/lib/api/`)

| Module | Purpose |
|--------|---------|
| `client.js` | Base fetch wrapper with error handling |
| `comics.js` | Comic CRUD, page URLs, progress updates |
| `config.js` | Server configuration API |
| `favorites.js` | Favorites add/remove/list |
| `libraries.js` | Library listing, scanning, progress |
| `scanners.js` | Scanner management and metadata scans |
| `search.js` | Search, advanced search, field discovery |

---

## Stores (`src/lib/stores/`)

| Store | Purpose |
|-------|---------|
| `theme.js` | Theme management with localStorage persistence |
| `library.js` | Current library/folder state, library list |
| `reader.js` | Reader settings (fit mode, direction, preload) |
| `search.js` | Search query and results state |
| `advancedSearch.js` | Advanced search with history and saved searches |
| `preferences.js` | User preferences (grid size, sort, view mode) |
| `user.js` | User session state |
| `ui.js` | UI state (sidebar visibility, view toggles) |

---

## Utils (`src/lib/utils/`)

| Module | Purpose |
|--------|---------|
| `cacheWarmer.js` | Pre-fetch and warm caches for faster navigation |
| `colors.js` | Color utilities for theme support |
| `persistentCache.js` | Persistent client-side cache layer |

---

## Actions (`src/lib/actions/`)

| Action | Purpose |
|--------|---------|
| `tooltip.js` | Tooltip action for hover tooltips on elements |

---

## Server Utilities (`src/lib/server/`)

| Module | Purpose |
|--------|---------|
| `config.js` | Server-side configuration utilities |

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
bun install
bun run dev
```

### Environment Variables

```bash
VITE_API_URL=http://localhost:8081  # Backend URL (optional)
```

### Build

```bash
bun run build
bun run preview  # Preview production build
```

### Linting

```bash
bun run lint
bun run format
```
