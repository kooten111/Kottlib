# Server-Side Control Over Mobile App UI

## TL;DR: **YES, We Have FULL Control!** 🎉

The mobile app is a **dumb client** - it just renders HTML sent by the server. We can modify EVERYTHING the mobile app displays by changing server-side templates and code.

---

## How It Works

### Template System

YACReader uses **server-side templates** (`.tpl` files) that generate HTML:

**Location**: `release/server/templates/`
- `libraries.tpl` - Library list page
- `folder.tpl` - Folder/comic browsing page

**Template Engine**: Custom template system (part of QtWebApp framework)

**Syntax**:
```html
{loop element}
  <li>
    <div class="{element.class}">
      <img src="{element.image.url}"/>
    </div>
    <div class="info">
      <p>{element.name}</p>
    </div>
  </li>
{end element}
```

### Current Flow

```
Mobile App Request
    ↓
Server Controller (C++ code)
    ↓
Query Database
    ↓
Populate Template Variables
    ↓
Render Template → HTML
    ↓
Send HTML to Mobile App
    ↓
Mobile App Displays HTML
```

---

## What We Can Control

### ✅ 1. Folder/Comic List Display

**Current Code** (foldercontroller.cpp:68-75):
```cpp
// Get folders and comics
QList<LibraryItem *> folderContent = DBHelper::getFolderSubfoldersFromLibrary(libraryId, folderId);
QList<LibraryItem *> folderComics = DBHelper::getFolderComicsFromLibrary(libraryId, folderId);

// THEY MIX THEM TOGETHER!
folderContent.append(folderComics);

// Then sort alphabetically (mixed)
std::sort(folderContent.begin(), folderContent.end(), LibraryItemSorter());
```

**What We Can Change**:
- ✅ **Separate folders and comics** (folders first!)
- ✅ **Custom sorting** (alphabetical, date, recently read)
- ✅ **Filter items** (hide read comics, show only favorites)
- ✅ **Group by series** (detect and group related comics)
- ✅ **Add metadata** (progress bars, ratings, tags)

**Example Python Implementation**:
```python
def render_folder(library_id, folder_id, sort='folders_first'):
    # Get data
    folders = get_subfolders(library_id, folder_id)
    comics = get_comics(library_id, folder_id)

    # FOLDERS FIRST!
    if sort == 'folders_first':
        folders.sort(key=lambda x: x.name.lower())
        comics.sort(key=lambda x: x.name.lower())
        items = folders + comics  # Folders on top!

    # Render template
    return render_template('folder.html', items=items)
```

---

### ✅ 2. HTML Structure

**Current Template** (folder.tpl:52-68):
```html
<ul id="itemContainer">
  {loop element}
  <li>
    <div class="{element.class}">
      <img style="width: 80px" src="{element.image.url}"/>
    </div>
    <div class="info">
      <div class="title"><p>{element.name}</p></div>
      <div class="elementInfo"> {element.pages} {element.size}</div>
      <div class="buttons"> {element.download} {element.read} {element.browse}</div>
    </div>
  </li>
  {end element}
</ul>
```

**What We Can Add**:
```html
<ul id="itemContainer">
  <!-- ADD: Folders Section Header -->
  <li class="section-header">
    <h2>📁 Folders</h2>
  </li>

  <!-- Folders -->
  {loop folder}
  <li class="folder-item">
    <div class="folder-icon">📁</div>
    <div class="info">
      <p>{folder.name}</p>
      <!-- NEW: Show comic count -->
      <span class="badge">{folder.comic_count} comics</span>
    </div>
  </li>
  {end folder}

  <!-- ADD: Comics Section Header -->
  <li class="section-header">
    <h2>📚 Comics</h2>
  </li>

  <!-- Comics -->
  {loop comic}
  <li class="comic-item">
    <div class="cover">
      <img src="{comic.cover}"/>
      <!-- NEW: Progress indicator -->
      {if comic.in_progress}
      <div class="progress-badge">{comic.progress}%</div>
      {end if}
    </div>
    <div class="info">
      <p>{comic.title}</p>
      <!-- NEW: Reading progress bar -->
      {if comic.current_page}
      <div class="progress-bar">
        <div class="fill" style="width: {comic.progress}%"></div>
      </div>
      <span class="progress-text">Page {comic.current_page}/{comic.total_pages}</span>
      {end if}
      <!-- NEW: Tags/metadata -->
      {if comic.series}
      <span class="series-badge">{comic.series} #{comic.issue}</span>
      {end if}
    </div>
  </li>
  {end comic}
</ul>
```

---

### ✅ 3. CSS Styling

**Current**: References `/css/styles_{device}.css`

**What We Can Do**:
- ✅ **Completely redesign the UI** (new colors, layout, fonts)
- ✅ **Add responsive design** (better mobile experience)
- ✅ **Custom themes** (dark mode, different color schemes)
- ✅ **Animations** (smooth transitions, loading states)

**Example**:
```css
/* New styles for folder-first display */
.section-header {
    background: #f0f0f0;
    padding: 10px;
    font-weight: bold;
    border-bottom: 2px solid #ccc;
}

.folder-item {
    background: #fff9e6;  /* Light yellow for folders */
    border-left: 4px solid #ffa500;
}

.comic-item {
    background: #fff;
}

.progress-badge {
    position: absolute;
    top: 5px;
    right: 5px;
    background: rgba(0, 150, 0, 0.8);
    color: white;
    padding: 3px 6px;
    border-radius: 3px;
    font-size: 11px;
}

.progress-bar {
    height: 4px;
    background: #e0e0e0;
    border-radius: 2px;
    overflow: hidden;
}

.progress-bar .fill {
    height: 100%;
    background: #4caf50;
    transition: width 0.3s ease;
}
```

---

### ✅ 4. Search Results

**Currently**: YACReader has basic search but we can enhance it.

**What We Can Add**:
```html
<!-- Search results page -->
<div id="search-results">
  <h1>Search: "{query}"</h1>

  <!-- Group by type -->
  <div class="results-group">
    <h2>Series ({series_count})</h2>
    <ul>
      {loop series}
      <li>
        <strong>{series.name}</strong>
        <span class="badge">{series.comic_count} issues</span>
      </li>
      {end loop}
    </ul>
  </div>

  <div class="results-group">
    <h2>Comics ({comic_count})</h2>
    <ul>
      {loop comic}
      <li>
        <img src="{comic.cover}"/>
        <div class="info">
          <p>{comic.title}</p>
          <!-- NEW: Highlight matching text -->
          <p class="snippet">...{matched_text}...</p>
          <span class="meta">{comic.series} - {comic.date}</span>
        </div>
      </li>
      {end loop}
    </ul>
  </div>

  <!-- NEW: Did you mean? -->
  {if suggestions}
  <div class="suggestions">
    <p>Did you mean:
      {loop suggestion}
      <a href="/search?q={suggestion}">{suggestion}</a>
      {end loop}
    </p>
  </div>
  {end if}
</div>
```

---

### ✅ 5. New Panels/Elements

**We Can Insert Anything**:

```html
<!-- Continue Reading Panel (NEW!) -->
<div id="continue-reading">
  <h2>Continue Reading</h2>
  <ul class="continue-list">
    {loop continue}
    <li>
      <img src="{comic.cover}"/>
      <div class="info">
        <p>{comic.title}</p>
        <div class="progress-bar">
          <div class="fill" style="width: {comic.progress}%"></div>
        </div>
        <p class="meta">Page {comic.page}/{comic.total} ({comic.progress}%)</p>
        <a href="{comic.continue_url}" class="btn-continue">Continue</a>
      </div>
    </li>
    {end loop}
  </ul>
</div>

<!-- Recently Added Panel (NEW!) -->
<div id="recently-added">
  <h2>📥 Recently Added</h2>
  <ul class="recent-grid">
    {loop recent}
    <li>
      <img src="{comic.cover}"/>
      <p>{comic.title}</p>
      <span class="badge-new">NEW</span>
    </li>
    {end loop}
  </ul>
</div>

<!-- Statistics Panel (NEW!) -->
<div id="stats">
  <h2>📊 Your Stats</h2>
  <div class="stats-grid">
    <div class="stat">
      <div class="number">{stats.comics_read}</div>
      <div class="label">Comics Read</div>
    </div>
    <div class="stat">
      <div class="number">{stats.total_pages}</div>
      <div class="label">Pages Read</div>
    </div>
    <div class="stat">
      <div class="number">{stats.streak_days}</div>
      <div class="label">Day Streak</div>
    </div>
  </div>
</div>
```

---

### ✅ 6. Dynamic Sorting UI

**Add Sorting Controls**:

```html
<!-- Sorting dropdown (NEW!) -->
<div id="sort-controls">
  <label>Sort by:</label>
  <select id="sort-select" onchange="changeSort(this.value)">
    <option value="folders_first" {if sort=='folders_first'}selected{endif}>
      📁 Folders First
    </option>
    <option value="alphabetical" {if sort=='alphabetical'}selected{endif}>
      🔤 Alphabetical
    </option>
    <option value="date_added" {if sort=='date_added'}selected{endif}>
      📅 Date Added
    </option>
    <option value="recently_read" {if sort=='recently_read'}selected{endif}>
      📖 Recently Read
    </option>
    <option value="series_grouped" {if sort=='series_grouped'}selected{endif}>
      📚 Grouped by Series
    </option>
  </select>

  <label>View:</label>
  <select id="view-select" onchange="changeView(this.value)">
    <option value="grid" {if view=='grid'}selected{endif}>Grid</option>
    <option value="list" {if view=='list'}selected{endif}>List</option>
    <option value="compact" {if view=='compact'}selected{endif}>Compact</option>
  </select>
</div>

<script>
function changeSort(sort) {
  window.location.href = window.location.pathname + '?sort=' + sort;
}

function changeView(view) {
  // Store in session/localStorage
  localStorage.setItem('view_mode', view);
  window.location.reload();
}
</script>
```

---

## Mobile App Behavior

### What the App Does

1. **Makes HTTP Request** to server (e.g., `/library/2/folder/1`)
2. **Receives HTML** from server
3. **Renders HTML** in embedded WebView
4. **Handles Links** (when user taps, makes new request)

### What the App Does NOT Do

- ❌ **No client-side logic** (it's just a WebView)
- ❌ **No custom rendering** (displays whatever HTML we send)
- ❌ **No filtering/sorting** (all done server-side)
- ❌ **No caching** (besides standard HTTP caching)

### What This Means

**We have 100% control over what the mobile app displays!**

The app is literally just:
```
┌────────────────────┐
│   Mobile App       │
│                    │
│  ┌──────────────┐  │
│  │   WebView    │  │  ← Displays our HTML
│  │ (Safari/     │  │
│  │  Chrome)     │  │
│  └──────────────┘  │
└────────────────────┘
```

---

## Limitations

### Things We CANNOT Change

1. **App Chrome** (navigation bar, buttons) - Those are native UI
2. **Comic Reader** - The page viewer is likely native for performance
3. **Gestures** - Swipe/pinch handled by native code
4. **Offline Mode** - App's download/cache system

### Things We CAN Change

✅ **Everything visible in the browsing interface**:
- Library list
- Folder contents
- Comic listings
- Search results
- Any HTML page

---

## Implementation Strategy

### Option 1: Modify Templates (Quick)

Just edit the `.tpl` files to change layout:

```python
# Our server serves modified templates
templates = {
    'folder': 'templates/folder_enhanced.html',  # Our version
    'libraries': 'templates/libraries_enhanced.html'
}
```

### Option 2: Complete Control (Recommended)

Generate HTML dynamically in our Python server:

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@app.get("/library/{lib_id}/folder/{folder_id}")
def get_folder(lib_id: int, folder_id: int, sort: str = 'folders_first'):
    # Get data
    folders = db.get_folders(lib_id, folder_id)
    comics = db.get_comics(lib_id, folder_id)

    # Apply sorting
    if sort == 'folders_first':
        folders.sort(key=lambda x: x.name.lower())
        comics.sort(key=lambda x: x.name.lower())
        items = {
            'folders': folders,
            'comics': comics
        }

    # Render OUR template with OUR data
    return templates.TemplateResponse("folder.html", {
        "request": request,
        "items": items,
        "sort": sort,
        "library": get_library(lib_id),
        # NEW FEATURES:
        "continue_reading": get_continue_reading(),
        "recently_added": get_recently_added(limit=5),
        "user_stats": get_user_stats()
    })
```

---

## Examples of What We Can Build

### 1. Folders-First Display (Requested Feature)

```html
<h2 class="section">📁 Folders</h2>
<ul class="folder-list">
  {% for folder in folders %}
  <li class="folder-item">
    📁 {{ folder.name }}
    <span class="count">{{ folder.comic_count }}</span>
  </li>
  {% endfor %}
</ul>

<h2 class="section">📚 Comics</h2>
<ul class="comic-grid">
  {% for comic in comics %}
  <li class="comic-item">
    <img src="{{ comic.cover }}"/>
    <p>{{ comic.name }}</p>
    {% if comic.progress %}
    <div class="progress">{{ comic.progress }}%</div>
    {% endif %}
  </li>
  {% endfor %}
</ul>
```

### 2. Continue Reading Widget

```html
<!-- At top of library page -->
<div class="widget continue-reading">
  <h3>📖 Continue Reading</h3>
  {% for comic in continue_reading[:3] %}
  <div class="continue-item">
    <img src="{{ comic.cover }}"/>
    <div class="info">
      <p>{{ comic.title }}</p>
      <div class="progress-bar">
        <div class="fill" style="width: {{ comic.progress }}%"></div>
      </div>
      <a href="{{ comic.continue_url }}">Continue →</a>
    </div>
  </div>
  {% endfor %}
</div>
```

### 3. Series Grouping

```html
<div class="series-view">
  {% for series in grouped_series %}
  <div class="series-group">
    <h3>{{ series.name }}</h3>
    <ul class="series-comics">
      {% for comic in series.comics %}
      <li>
        <span class="issue">#{{ comic.issue }}</span>
        <img src="{{ comic.cover }}"/>
        <p>{{ comic.subtitle }}</p>
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
</div>
```

---

## Summary

### ✅ What We Can Do

1. **Folders-first sorting** - YES, 100% control
2. **Insert new panels** - YES, add anything
3. **Edit search results** - YES, full control
4. **Change library look/behavior** - YES, it's all server-generated HTML
5. **Add progress bars, ratings, tags** - YES, all server-side
6. **Custom sorting, filtering, grouping** - YES, we control the data
7. **Redesign entire UI** - YES, it's just HTML/CSS
8. **Add JavaScript features** - YES, mobile app runs it

### ❌ What We Cannot Do

1. Modify native app chrome (top bar, etc.)
2. Change the comic reader/page viewer
3. Modify app settings/preferences
4. Change native gestures

### Bottom Line

**The mobile app is essentially a browser.** We have complete control over everything it displays when browsing libraries, folders, and comics. We can implement ALL the features we discussed!
