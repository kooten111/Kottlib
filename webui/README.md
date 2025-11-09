# YACLib Enhanced - Web UI

Modern, responsive web interface for YACLib Enhanced comic library server.

## Features ✨

### Core Features
- 📚 **Library Browser** - Browse comics with grid/list views, folder navigation
- 📖 **Comic Reader** - Full-featured reader with keyboard shortcuts, fit modes, progress tracking
- 🏠 **Home Dashboard** - Continue reading, recently added, library sidebar
- 🔍 **Search** - Full-text search across all libraries with filters
- ⭐ **Favorites** - Mark and browse your favorite comics
- 📊 **Admin Dashboard** - Server statistics and management

### Design
- 🎨 Modern dark-mode-first design (with light mode toggle)
- 📱 Fully responsive (mobile, tablet, desktop)
- ⚡ Fast, optimized with SvelteKit
- 🎯 Tailwind CSS custom design system
- 🔍 TanStack Query for efficient data fetching
- ♿ Accessible (WCAG 2.1 AA compliant)

## Tech Stack

- **Framework**: SvelteKit
- **Styling**: Tailwind CSS
- **State Management**: Svelte stores + TanStack Query
- **Icons**: Lucide Svelte
- **Build Tool**: Vite

## Getting Started

### Quick Start (Recommended)

From the project root, run:
```bash
./run_server.sh
```

This automatically starts:
- ✅ Backend API on port 8081
- ✅ Web UI on port 5173

Then visit: **http://localhost:5173**

### Manual Setup

#### Prerequisites
- Node.js v18+ and npm
- Backend API running on port 8081

#### Installation
```bash
cd webui
npm install
```

#### Development
```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The API proxy is configured to forward `/v2/*` requests to `http://localhost:8081`.

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
webui/
├── src/
│   ├── routes/              # SvelteKit routes (pages)
│   │   ├── +layout.svelte   # Root layout
│   │   └── +page.svelte     # Home page
│   ├── lib/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── layout/      # Layout components (Navbar, Sidebar, Footer)
│   │   │   ├── common/      # Common components (Button, Card, Input)
│   │   │   ├── comic/       # Comic-specific components
│   │   │   └── reader/      # Reader components
│   │   ├── api/             # API client
│   │   ├── stores/          # Svelte stores (state management)
│   │   ├── utils/           # Utility functions
│   │   └── types/           # TypeScript types
│   ├── static/              # Static assets
│   └── app.css              # Global styles
├── svelte.config.js
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## Implementation Status

### ✅ Phase 1: Foundation (COMPLETE)
- SvelteKit project with Vite
- Tailwind CSS custom design system
- Layout components (Navbar, Sidebar, Footer)
- Common components (Button, Card, Input, Modal, ProgressBar, Breadcrumbs)
- API client with full backend integration
- Dark/light theme system with localStorage
- Development server with API proxy

### ✅ Phase 2: Comic Reader (COMPLETE)
- PageViewer component with fit modes (width, height, original)
- Reader controls (prev/next, page slider)
- Keyboard shortcuts (arrows, space, fullscreen, ESC)
- Reading progress tracking and auto-save
- Fullscreen mode
- Manga mode (RTL reading)
- ReaderSettings panel

### ✅ Phase 3: Library Browser (COMPLETE)
- Comic grid/list views with toggle
- Folder navigation with breadcrumbs
- Folder covers (using first comic)
- Sorting options (name, date, progress)
- Library sidebar on home page
- Continue reading page
- Favorites page
- Comic detail pages
- Progress indicators on cards

### ✅ Phase 4: Search & Discovery (COMPLETE)
- Search interface with filters
- Multi-library search
- Status filters (unread/reading/completed)
- Active filter chips
- Search autocomplete with covers and keyboard navigation

### ⏳ Phase 5: User Features (PARTIAL)
- Favorites system ✅
- Comic detail pages ✅
- Reading lists UI (pending)
- Tags/labels UI (pending)

### ⏳ Phase 6: Admin Panel (BASIC)
- Basic dashboard ✅
- Library stats ✅
- Full management UI (pending)

See [WEB_UI_PLAN.md](../docs/WEB_UI_PLAN.md) for the complete implementation roadmap.

## Development Notes

### API Integration

The web UI communicates with the YACLib Enhanced backend via REST API. All API calls go through the client in `src/lib/api/`.

Example:
```javascript
import { getLibraries } from '$api/libraries';

const libraries = await getLibraries();
```

### State Management

- **UI State**: Component-local state
- **User Preferences**: Svelte stores with localStorage
- **Server Data**: TanStack Query (automatic caching, refetching)

### Theme System

Theme is managed by `$stores/theme.js` and persisted to localStorage. The theme is applied to the `<html>` element's `class` attribute.

```javascript
import { themeStore } from '$stores/theme';

// Toggle theme
themeStore.toggle();

// Set specific theme
themeStore.set('dark');
```

## License

MIT
