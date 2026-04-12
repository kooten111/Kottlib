# Kottlib Product TODO

Living backlog for feature ideas, UX parity goals, and implementation notes.

## Current Priorities

- [ ] Add content type support at library level
  - [ ] Support `comic`, `manga`, `western manga (left to right)`, `web comic`, `yonkoma`
  - [ ] Persist type in library settings/config and expose through API
  - [ ] Show and edit library type in admin + web UI
  - [ ] Define a migration path for existing libraries with no type set

- [ ] Add type-aware defaults
  - [ ] Reader defaults per library type (reading direction, page flow, layout defaults)
  - [ ] Scanner defaults per library type (preferred scanner set, fallback order)
  - [ ] Allow per-library override of type defaults

- [ ] Read/unread controls for both series and comic scope
  - [ ] Mark series as read
  - [ ] Mark series as unread
  - [ ] Mark individual comic as read
  - [ ] Mark individual comic as unread
  - [ ] Ensure progress/stat endpoints remain consistent after bulk updates

- [ ] Custom cover support
  - [ ] Set series cover from another comic in the same series/library
  - [ ] Upload a custom cover image
  - [ ] Store cover source metadata (auto vs selected comic vs upload)
  - [ ] Add reset-to-auto cover option

- [ ] Full metadata editor for series
  - [ ] Editable core fields (title, description, genres, tags, status, year, author/artist, publisher)
  - [ ] Editable scanner/provider metadata mappings
  - [ ] Save provenance or change history for manual edits
  - [ ] Define merge behavior when scanner updates run after manual edits

- [ ] ComicInfo.xml compatibility without unsafe auto-import
  - [ ] Keep automatic ComicInfo import disabled by default (especially for overwrite-prone fields)
  - [ ] Add library-level policy: `off`, `manual import only`, `import on scan (safe fields only)`
  - [ ] Add a manual import action in metadata editor with preview/diff before apply
  - [ ] Add per-field merge strategy: `keep existing`, `replace`, `fill empty only`
  - [ ] Track metadata source per field (`manual`, `scanner`, `comicinfo`, `derived`) for conflict handling
  - [ ] Add ComicInfo export from metadata editor to write a normalized `ComicInfo.xml`
  - [ ] Preserve unknown/unmapped ComicInfo tags when round-tripping if feasible

- [ ] Decouple sorting behavior by context
  - [ ] `/library/:id/browse` sorting should be independent from series view sorting
  - [ ] `/library/:id/browse/:seriesOrPath` sorting preferences should be separate
  - [ ] Persist per-view sort options in UI state (and optionally user prefs)
  - [ ] Confirm API sorting params are context-specific and do not leak between views

- [ ] Comic metadata editor parity (YACReader-inspired)
  - [ ] General info tab fields: `series`, `title`, `issue number`, `issue count`, `volume`, `story arc`, `arc number`, `arc count`, `alternate series`, `alternate number`, `alternate count`, `series group`, `genre`
  - [ ] Plot tab fields: `synopsis`, `characters`, `teams`, `locations`, `main character or team`
  - [ ] Authors tab fields: `writer(s)`, `penciller(s)`, `inker(s)`, `colorist(s)`, `letterer(s)`, `cover artist(s)`, `editor(s)`, `imprint`
  - [ ] Publishing tab fields: `day`, `month`, `year`, `publisher`, `format`, `color/BW`, `age rating`, `type`, `language (ISO)`
  - [ ] Notes tab field: `notes`
  - [ ] Add editable `tags` field in metadata editor (series + comic scope)
  - [ ] Define tag UX behavior: add/remove chips, dedupe/case handling, and comma/newline paste parsing

## UX Parity Targets (Inspired by YACReader)

- [ ] Context menu actions at folder/series/comic level
- [ ] Quick type assignment flow
- [ ] Quick read/unread toggles with clear visual state
- [ ] Cover management from context menu

## Architecture Notes

- Library type should be a first-class concept shared across:
  - Config
  - Database
  - API contracts
  - Scanner selection
  - Reader defaults

- Manual metadata/covers should coexist with scanner-derived data:
  - Manual fields should be lockable or marked as authoritative
  - Scanner refresh should not silently overwrite locked manual fields

- ComicInfo.xml should be treated as an interoperability format, not an authoritative source by default:
  - Import should be explicit or constrained by safe-field policy
  - Export should prioritize producing clean, consistent files for external readers

## Suggested Delivery Order

1. Library type model + migration + API exposure
2. Type-aware reader/scanner defaults
3. Read/unread endpoints and UI actions (series + comic)
4. Custom cover source selection + upload
5. Series metadata editor
6. Sort-state decoupling between browse and series views

## Open Questions

- Should library type be single-select only, or allow mixed libraries with per-series type overrides?
- Should read/unread actions be user-scoped only, or support admin/global actions?
- For cover uploads, where should assets live and what cleanup policy should apply?
- Should metadata editor support field locking to protect manual edits from scanner refresh?
- Should sort preferences persist per user/session/device?
- Which ComicInfo fields are considered "safe" for optional scan-time import vs "manual-only"?
- Do we need one-click "import from ComicInfo" and "export to ComicInfo" at both series and comic level?
