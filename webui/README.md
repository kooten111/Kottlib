# YACLib Enhanced - Web UI

Modern, responsive web interface for YACLib Enhanced comic library server.

## Features

- 🎨 Modern dark-mode-first design
- 📱 Fully responsive (mobile, tablet, desktop)
- ⚡ Fast, optimized with SvelteKit
- 🎯 Tailwind CSS for styling
- 🔍 TanStack Query for efficient data fetching
- 🎭 Theme switching (dark/light)
- ♿ Accessible (WCAG 2.1 AA)

## Tech Stack

- **Framework**: SvelteKit
- **Styling**: Tailwind CSS
- **State Management**: Svelte stores + TanStack Query
- **Icons**: Lucide Svelte
- **Build Tool**: Vite

## Getting Started

### Prerequisites

- Node.js v18+ and npm

### Installation

```bash
cd webui
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The API proxy is configured to forward `/v2/*` requests to `http://localhost:8000`.

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

## Phase 1 Complete ✅

**Foundation (Week 1-2)**:
- ✅ SvelteKit project setup
- ✅ Tailwind CSS configured
- ✅ Layout components created (Navbar, Sidebar, Footer)
- ✅ Routing structure established
- ✅ API client implemented
- ✅ Dark/light theme system
- ✅ Basic component library (Button, Card, Input, Modal, etc.)

## Next Steps

**Phase 2: Comic Reader (Week 3-4)**
- Implement PageViewer component
- Add reader controls
- Implement reading modes (single, double, continuous)
- Add keyboard shortcuts
- Implement progress saving

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
