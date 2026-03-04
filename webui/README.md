# Kottlib - Web UI

Modern, responsive web interface for Kottlib comic library server.

## Features ✨

### Core Features
- 📚 **Library Browser** - Browse comics with grid/list views, folder navigation
- 📖 **Comic Reader** - Full-featured reader with keyboard shortcuts, fit modes, progress tracking
- 🏠 **Home Dashboard** - Continue reading, recently added, library sidebar
- 🔍 **Search** - Full-text search across all libraries with filters
- ⭐ **Favorites** - Mark and browse your favorite comics
- 📊 **Admin Dashboard** - Server statistics and management

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
./start.sh
```

This automatically starts:
- ✅ Backend API on port 8081
- ✅ Web UI on port 5173

Then visit: **http://localhost:5173**

### Manual Setup

#### Prerequisites
- Bun (https://bun.sh)
- Backend API running on port 8081

#### Installation
```bash
cd webui
bun install
```

#### Development
```bash
bun run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The API proxy forwards both `/api/*` (primary WebUI API) and `/v2/*` (YACReader compatibility) to `http://localhost:8081`.

### Build for Production

```bash
bun run build
bun run preview
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

See [WEB_UI_PLAN.md](../docs/WEB_UI_PLAN.md) for the complete implementation roadmap.

## Development Notes

### API Integration

The web UI communicates with the Kottlib backend via REST API. All API calls go through the client in `src/lib/api/`.

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
