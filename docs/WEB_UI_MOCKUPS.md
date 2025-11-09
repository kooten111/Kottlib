# Web UI Visual Mockups & Wireframes

**Companion to**: [WEB_UI_PLAN.md](WEB_UI_PLAN.md)
**Created**: 2025-11-09

This document provides ASCII wireframes and visual descriptions for the Web UI.

---

## Color Palette Reference

```
Dark Mode (Default):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
█ #1a1a1a  Background (Primary)
█ #242424  Background (Cards/Secondary)
█ #ff6740  Accent (Orange)
█ #e0e0e0  Text (Primary)
█ #a0a0a0  Text (Secondary)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Light Mode:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
█ #ffffff  Background (Primary)
█ #f5f5f5  Background (Cards/Secondary)
█ #ff6740  Accent (Orange)
█ #1a1a1a  Text (Primary)
█ #666666  Text (Secondary)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 1. Home Page Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ [YACLib] [🔍 Search comics...]           [☀️/🌙] [@User ▼]     │ ← Navbar (sticky)
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Continue Reading                                    [See All →] │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │ ← Cover images
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤   │
│  │░░░░░░70%│ │░░░░░25% │ │░░░░░░85%│ │░░15%    │ │░░░░50%  │   │ ← Progress bar
│  ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤   │
│  │Title #42│ │Amazing  │ │X-Men #1 │ │Batman #3│ │Flash #12│   │ ← Title
│  │Pg 21/30 │ │Pg 5/20  │ │Pg 17/20 │ │Pg 3/20  │ │Pg 10/20 │   │ ← Page info
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                  │
│  Recently Added                                      [See All →] │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │ │ ▓▓▓▓▓▓▓ │   │
│  ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤   │
│  │New #1   │ │Series #2│ │Comic #99│ │Issue #1 │ │Vol 2 #1 │   │
│  │Unread   │ │Unread   │ │Unread   │ │Unread   │ │Unread   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                  │
│  Quick Access                                                    │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐         │
│  │ ♥ Favorites   │ │ 📚 Reading    │ │ 🏷️ My Tags    │         │
│  │    142 comics │ │    5 lists    │ │    12 tags    │         │
│  └───────────────┘ └───────────────┘ └───────────────┘         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Features**:
- Horizontal scrolling carousels for each section
- Hover on cover → Show quick actions (Read, Favorite, Add to List)
- Click cover → Go to comic detail page
- Progress bars show reading completion

---

## 2. Library Browser (Desktop)

```
┌──────────────────────────────────────────────────────────────────┐
│ [YACLib] [🔍 Search...]                     [☀️/🌙] [@User ▼]   │
├──────────┬───────────────────────────────────────────────────────┤
│ Browse   │  Home > Comics Library > Marvel                       │ ← Breadcrumb
│          │                                                        │
│ 📚 All   │  [Sort: Name ▼] [Grid/List] [Filter ≡]               │
│ ♥ Favs   │  ┌────────────────────────────────────────────────┐  │
│ 📖 Lists │  │ 🔍 Filter by:                                  │  │
│ 🏷️ Tags  │  │ [x] Action  [x] Marvel  [ ] DC  [ ] 2020s     │  │
│          │  └────────────────────────────────────────────────┘  │
├──────────┤                                                        │
│ Series   │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│ ☑ Marvel │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ ☑ DC     │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ □ Image  │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│          │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ Year     │  ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤       │
│ ☑ 2020s  │  │Title │ │Title │ │Title │ │Title │ │Title │       │
│ □ 2010s  │  │ #1   │ │ #2   │ │ #3   │ │ #4   │ │ #5   │       │
│ □ 2000s  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
│          │                                                        │
│ Tags     │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│ ☑ Action │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ ☑ Sci-Fi │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ □ Horror │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│          │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ Status   │  ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤       │
│ □ Unread │  │Title │ │Title │ │Title │ │Title │ │Title │       │
│ ☑ Reading│  │ #6   │ │ #7   │ │ #8   │ │ #9   │ │ #10  │       │
│ □ Done   │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
│          │                                                        │
│ [Clear]  │  Showing 142 of 1,234 comics          [1] 2 3 4 ... │ ← Pagination
└──────────┴────────────────────────────────────────────────────────┘
```

**Responsive Behavior**:
- **Tablet**: Sidebar collapses to icon-only, expands on tap
- **Mobile**: Sidebar becomes bottom sheet, filters in modal

---

## 3. Comic Detail Page

```
┌──────────────────────────────────────────────────────────────────┐
│ [YACLib] [🔍 Search...]                     [☀️/🌙] [@User ▼]   │
├──────────────────────────────────────────────────────────────────┤
│  Home > Comics Library > Marvel > Amazing Spider-Man            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │              │  The Amazing Spider-Man #1                    │
│  │              │  ━━━━━━━━━━━━━━━━━━━━━━━━━                   │
│  │    ████      │                                               │
│  │    ████      │  📚 Series: Amazing Spider-Man                │
│  │    ████      │  📖 Issue: #1                                 │
│  │    ████      │  ✍️  Writer: Stan Lee                         │
│  │    ████      │  🎨 Artist: Steve Ditko                       │
│  │    ████      │  📅 Year: 1963                                │
│  │    ████      │  🏢 Publisher: Marvel Comics                  │
│  │    ████      │  📄 Pages: 24                                 │
│  │              │  💾 Size: 15.2 MB                             │
│  │  COVER ART   │                                               │
│  │   (300x450)  │  ┌──────────────────────────────────────┐    │
│  │              │  │ [▶️ Read]  [↻ Continue (Page 12)]   │    │
│  │              │  └──────────────────────────────────────┘    │
│  │              │  [♥ Favorite] [➕ Add to List] [🏷️ Tags]     │
│  │              │                                               │
│  └──────────────┘  Progress: ░░░░░░░░░░░░░░ 50% (12/24 pages)  │
│                                                                  │
│  🏷️ Tags: [Action] [Superhero] [Marvel]                        │
│                                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Description                                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  The origin of Spider-Man! After being bitten by a radioactive  │
│  spider, teenager Peter Parker gains incredible powers and      │
│  must learn that with great power comes great responsibility.   │
│                                                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  More from this Series                          [See All 700 →] │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │        │
│  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │        │
│  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │        │
│  ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤        │
│  │ #2   │ │ #3   │ │ #4   │ │ #5   │ │ #6   │ │ #7   │        │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
│                                                                  │
│  ◀ Previous: N/A          |          Next: Issue #2 ▶           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Comic Reader (Full Screen)

```
┌──────────────────────────────────────────────────────────────────┐
│ [⚙️ Settings] [←][→] Page 12/24 (50%)      [Fullscreen] [✕]    │ ← Top bar (auto-hide)
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                                                                  │
│                                                                  │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                                                                  │
│                       COMIC PAGE IMAGE                          │
│                       (Fit to width)                            │
│                                                                  │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                        ████████████                             │
│                                                                  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ◀ Prev     ░░░░░░░░░░●░░░░░░░░░░░░░░       Next ▶             │ ← Bottom bar (auto-hide)
│              |-------|-----------|------|                       │    (Page slider)
│              0       12          24                             │
└──────────────────────────────────────────────────────────────────┘
```

**Settings Panel** (Slides in from right):
```
┌─────────────────────┐
│ Reader Settings     │
├─────────────────────┤
│ Reading Mode:       │
│ ○ Single Page       │
│ ● Double Page       │
│ ○ Continuous Scroll │
│                     │
│ Fit Mode:           │
│ ● Fit Width         │
│ ○ Fit Height        │
│ ○ Original Size     │
│                     │
│ Direction:          │
│ ● Left-to-Right     │
│ ○ Right-to-Left     │
│                     │
│ Preload Pages:      │
│ [─●───────] 3       │
│                     │
│ Background:         │
│ ● Dark              │
│ ○ Light             │
│ ○ Black             │
│                     │
│ ┌─────────────────┐ │
│ │ Keyboard Shortcuts│
│ ├─────────────────┤ │
│ │ ← → : Navigate  │ │
│ │ Space: Next     │ │
│ │ F: Fullscreen   │ │
│ │ S: Settings     │ │
│ │ Esc: Exit       │ │
│ └─────────────────┘ │
└─────────────────────┘
```

---

## 5. Search Results Page

```
┌──────────────────────────────────────────────────────────────────┐
│ [YACLib] [🔍 spider-man________________________] [☀️/🌙] [@User] │
├──────────┬───────────────────────────────────────────────────────┤
│          │  Search: "spider-man"                                 │
│          │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ Filters  │                                                        │
│          │  Found 142 results         [Sort: Relevance ▼]        │
│ Series   │                                                        │
│ ☑ Amazing│  Active Filters: [Series: Amazing ✕] [Year: 1960s ✕] │
│ ☑ Ultimate│                                                       │
│ □ Superior│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│          │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ Publisher│  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ ☑ Marvel │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ □ DC     │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│          │  ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤       │
│ Year     │  │Amaz. │ │Amaz. │ │Amaz. │ │Spect.│ │Ulti. │       │
│ ☑ 1960s  │  │ #1   │ │ #2   │ │ #3   │ │ #1   │ │ #1   │       │
│ □ 1970s  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
│ □ 1980s  │                                                        │
│          │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│ Tags     │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ ☑ Action │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│ ☑ Superhero│ │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │     │
│ □ Sci-Fi │  │ ████ │ │ ████ │ │ ████ │ │ ████ │ │ ████ │       │
│          │  ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤       │
│ [Clear]  │  │Amaz. │ │Web of│ │Friend│ │Spec. │ │Sens. │       │
│          │  │ #4   │ │ #1   │ │ #1   │ │ #2   │ │ #1   │       │
│          │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
└──────────┴────────────────────────────────────────────────────────┘
```

**Instant Search** (Dropdown):
```
┌──────────────────────────────────────────┐
│ [🔍 spi_________________________] [Ctrl+K]│
├──────────────────────────────────────────┤
│ 🔎 Suggestions:                          │
│   → spider-man                           │
│   → spider-woman                         │
│   → spider-verse                         │
│                                          │
│ 📚 Series:                               │
│   → Amazing Spider-Man (142)             │
│   → Ultimate Spider-Man (68)             │
│                                          │
│ 📖 Recent Searches:                      │
│   → batman                               │
│   → x-men 1990                           │
└──────────────────────────────────────────┘
```

---

## 6. Admin Dashboard

```
┌──────────────────────────────────────────────────────────────────┐
│ [YACLib Admin] [🔍 Search...]              [☀️/🌙] [@Admin ▼]   │
├──────────┬───────────────────────────────────────────────────────┤
│ Admin    │  Dashboard                                             │
│          │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ Dashboard│                                                        │
│ Libraries│  ┌─────────────┬─────────────┬─────────────┐          │
│ Users    │  │ 📚 Comics   │ 📖 Libraries│ 👥 Users    │          │
│ Settings │  │   1,234     │      3      │     5       │          │
│ Logs     │  └─────────────┴─────────────┴─────────────┘          │
│          │                                                        │
│          │  ┌────────────────────────────────────────────────┐   │
│          │  │ 📊 Storage Usage                              │   │
│          │  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│          │  │ Comics:  ▓▓▓▓▓▓▓▓▓▓░░░░░░░░  52 GB / 100 GB  │   │
│          │  │ Covers:  ▓▓░░░░░░░░░░░░░░░░   3 GB / 100 GB  │   │
│          │  │ Database:▓░░░░░░░░░░░░░░░░░ 512 MB / 100 GB  │   │
│          │  │ Total:   ▓▓▓▓▓▓▓▓▓▓░░░░░░░░  55 GB / 100 GB  │   │
│          │  └────────────────────────────────────────────────┘   │
│          │                                                        │
│          │  ┌────────────────────────────────────────────────┐   │
│          │  │ 📡 Recent Activity                            │   │
│          │  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│          │  │ ✅ Library scan completed (142 new comics)    │   │
│          │  │    2 minutes ago                              │   │
│          │  │                                               │   │
│          │  │ 👤 New user registered: john_doe              │   │
│          │  │    15 minutes ago                             │   │
│          │  │                                               │   │
│          │  │ 📖 Comic read: Amazing Spider-Man #42         │   │
│          │  │    1 hour ago                                 │   │
│          │  │                                               │   │
│          │  │ ⚠️  Failed to generate cover: batman.cbz      │   │
│          │  │    2 hours ago                                │   │
│          │  └────────────────────────────────────────────────┘   │
│          │                                                        │
│          │  ┌────────────────────────────────────────────────┐   │
│          │  │ 🔄 Scan Queue (3 pending)                     │   │
│          │  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│          │  │ [▶️] Comics Library      ░░░░░░░░░░  45%      │   │
│          │  │ [⏸️] Manga Library       Ready                │   │
│          │  │ [⏹️] Archive Library     Queued               │   │
│          │  └────────────────────────────────────────────────┘   │
└──────────┴────────────────────────────────────────────────────────┘
```

---

## 7. Mobile Layouts

### Mobile Home Page (Portrait)

```
┌────────────────────┐
│ ☰ YACLib    🔍 @U  │ ← Hamburger menu
├────────────────────┤
│ Continue Reading   │
│ ┌────┐ ┌────┐     │
│ │████│ │████│ →   │ ← Horizontal scroll
│ │████│ │████│     │
│ ├────┤ ├────┤     │
│ │░70%│ │░25%│     │
│ └────┘ └────┘     │
│                    │
│ Recently Added     │
│ ┌────┐ ┌────┐     │
│ │████│ │████│ →   │
│ │████│ │████│     │
│ └────┘ └────┘     │
│                    │
│ Quick Access       │
│ ┌────────────────┐ │
│ │ ♥ Favorites    │ │
│ └────────────────┘ │
│ ┌────────────────┐ │
│ │ 📚 Lists       │ │
│ └────────────────┘ │
└────────────────────┘
```

### Mobile Reader (Landscape)

```
┌──────────────────────────────────────┐
│                                      │ ← Full screen
│         ████████████████             │
│         ████████████████             │
│         ████████████████             │
│                                      │
│         COMIC PAGE IMAGE             │
│                                      │
│         ████████████████             │
│         ████████████████             │
│         ████████████████             │
│                                      │
│  [Tap edges to navigate]             │ ← Hint (fades out)
└──────────────────────────────────────┘
```

**Touch Zones**:
- Left 1/3: Previous page
- Center 1/3: Toggle controls
- Right 1/3: Next page

---

## 8. Component Gallery

### Comic Card States

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  ████    │  │  ████    │  │  ████    │
│  ████    │  │  ████  ♥ │  │  ████  ★ │ ← Badges
│  ████    │  │  ████    │  │  ████    │
│  ████    │  │  ████    │  │  ████    │
├──────────┤  ├──────────┤  ├──────────┤
│          │  │░░░░░░50% │  │░░░░░░100%│ ← Progress
├──────────┤  ├──────────┤  ├──────────┤
│ Title #1 │  │ Title #2 │  │ Title #3 │
│ Unread   │  │ Reading  │  │ Complete │
└──────────┘  └──────────┘  └──────────┘
   Normal      Favorited       Finished

HOVER STATE:
┌──────────┐
│  ████    │
│ [▶️ READ]│ ← Quick actions appear
│ [♥ FAV] │
│ [+ LIST]│
├──────────┤
│░░░░░░50% │
├──────────┤
│ Title #2 │
└──────────┘
```

### Buttons

```
Primary:    [  Read Now  ]  ← Accent color background
Secondary:  [  Cancel    ]  ← Border only
Danger:     [  Delete    ]  ← Red
Icon:       [ ♥ ] [➕] [⚙️]  ← Icon only
```

### Loading States

```
Comic Grid Loading (Skeleton):
┌──────┐ ┌──────┐ ┌──────┐
│ ▒▒▒▒ │ │ ▒▒▒▒ │ │ ▒▒▒▒ │ ← Shimmer animation
│ ▒▒▒▒ │ │ ▒▒▒▒ │ │ ▒▒▒▒ │
│ ▒▒▒▒ │ │ ▒▒▒▒ │ │ ▒▒▒▒ │
├──────┤ ├──────┤ ├──────┤
│ ▒▒▒▒ │ │ ▒▒▒▒ │ │ ▒▒▒▒ │
└──────┘ └──────┘ └──────┘
```

---

## 9. Responsive Breakpoints

```
Mobile:     320px - 767px   (1 column)
Tablet:     768px - 1023px  (2-3 columns)
Desktop:    1024px - 1439px (4-5 columns)
Large:      1440px+         (6 columns)
```

**Grid Columns**:
- Mobile: 2 comics per row
- Tablet: 3-4 comics per row
- Desktop: 5 comics per row
- Large: 6 comics per row

---

## 10. Animations & Transitions

**Page Transitions**:
- Fade in/out: 200ms
- Slide in/out: 300ms
- Expand/collapse: 250ms

**Hover Effects**:
- Scale up covers: 1.05x
- Brighten on hover: +10% brightness
- Shadow on hover: 0 4px 8px rgba(0,0,0,0.2)

**Loading**:
- Skeleton shimmer: 1.5s loop
- Spinner: 1s rotation
- Progress bar: smooth 300ms

---

**Last Updated**: 2025-11-09
**Status**: Reference for WEB_UI_PLAN.md
