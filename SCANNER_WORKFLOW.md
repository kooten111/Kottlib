# Scanner Workflow - Complete Implementation Plan

## Overview

Complete system for scanning individual comics and entire libraries, with intelligent metadata handling based on what each scanner provides.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Scan                                                     │
│     • Select comic(s) or entire library                      │
│     • System scans using configured scanner                  │
│     • Results stored temporarily (not applied yet)           │
│                                                              │
│  2. Review                                                   │
│     • See what metadata would be applied                     │
│     • Current vs New values side-by-side                     │
│     • Confidence scores and field categories                 │
│     • Select which fields to apply                           │
│                                                              │
│  3. Apply                                                    │
│     • User confirms which fields to update                   │
│     • Choose overwrite mode (overwrite all vs fill empty)    │
│     • Metadata saved to database                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Metadata Schema (`scanners/metadata_schema.py`) ✅

**Purpose:** Define what fields each scanner can provide

**Features:**
- `MetadataField` enum - All possible metadata fields
- `FieldDefinition` - Maps fields to database columns
- `ScannerCapabilities` - What each scanner can provide
- `map_scanner_metadata_to_comic()` - Convert scanner data to DB format

**Scanner Capabilities:**
```python
nhentai:
  - title, artist, genre, language, tags, characters,
page_count, web_link
  - Primary fields: title, artist, tags

anilist (future):
  - title, series, volume, issue, year, description,
genre, tags, web_link

comicvine (future):
  - Comprehensive: all people fields, series info,
characters, teams, etc.
```

### 2. Metadata Service (`src/services/metadata_service.py`) ✅

**Purpose:** Apply scanner results to database

**Key Functions:**
- `apply_scan_result_to_comic()` - Apply metadata to a comic
- `get_metadata_preview()` - Preview what would change
- `batch_apply_metadata()` - Apply to multiple comics
- `get_scanner_field_mapping()` - Get scanner capabilities

**Options:**
- `overwrite`: Overwrite existing metadata or only fill empty fields
- `selected_fields`: Choose which fields to apply

### 3. API Endpoints (To Implement)

#### A. Scan Operations

```
POST /v2/scanners/comics/{comic_id}/scan
  - Scan a single comic
  - Returns scan result (not applied yet)
  - Response: ScanResult with preview

POST /v2/scanners/libraries/{library_id}/scan
  - Scan all comics in a library
  - Background job
  - Returns job ID for tracking

GET /v2/scanners/jobs/{job_id}
  - Check scan job status
  - Get progress and results
```

#### B. Review & Apply

```
GET /v2/scanners/comics/{comic_id}/preview
  - Get metadata preview (current vs new)
  - Shows what would change

POST /v2/scanners/comics/{comic_id}/apply
  - Apply scanned metadata to comic
  - Body: {
      "scan_result_id": "...",
      "overwrite": false,
      "selected_fields": ["title", "artist", ...]
    }

POST /v2/scanners/libraries/{library_id}/apply-batch
  - Apply metadata to multiple comics
  - Body: {
      "comic_ids": [1, 2, 3],
      "overwrite": false,
      "selected_fields": [...]
    }
```

#### C. Scanner Info

```
GET /v2/scanners/{scanner_name}/capabilities
  - Get what fields a scanner provides
  - Organized by category

GET /v2/scanners/{scanner_name}/field-mapping
  - Get detailed field mapping
  - Shows DB columns and data types
```

### 4. Database Tables (To Add)

#### ScanJob Table
```sql
CREATE TABLE scan_jobs (
    id INTEGER PRIMARY KEY,
    library_id INTEGER REFERENCES libraries(id),
    scanner_name VARCHAR,
    status VARCHAR,  -- 'pending', 'running', 'completed', 'failed'
    total_comics INTEGER,
    scanned_comics INTEGER,
    matched_comics INTEGER,
    failed_comics INTEGER,
    started_at INTEGER,
    completed_at INTEGER,
    error TEXT
);
```

#### ScanResult Table (Temporary Storage)
```sql
CREATE TABLE scan_results (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES scan_jobs(id),
    comic_id INTEGER REFERENCES comics(id),
    scanner_name VARCHAR,
    confidence FLOAT,
    confidence_level VARCHAR,
    source_id VARCHAR,
    source_url VARCHAR,
    metadata JSON,  -- Full metadata from scanner
    tags JSON,      -- Tags array
    scanned_at INTEGER,
    applied BOOLEAN DEFAULT FALSE,
    applied_at INTEGER
);
```

### 5. UI Components (To Implement)

#### A. Comic Details Page - Scan Button

```
┌─────────────────────────────────────────────┐
│ Comic: [Artist] Title [English].cbz        │
│                                             │
│ Current Metadata:                           │
│   Title: (empty)                            │
│   Artist: (empty)                           │
│   Tags: (empty)                             │
│                                             │
│ [Scan for Metadata]                         │
└─────────────────────────────────────────────┘
```

After scanning:
```
┌─────────────────────────────────────────────┐
│ Scan Results (85% Confidence - HIGH)        │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Current      →    New Value             │ │
│ ├─────────────────────────────────────────┤ │
│ │ Title:                                  │ │
│ │ (empty)      →    [Full Title]          │ │
│ │ ☑ Apply                                 │ │
│ │                                         │ │
│ │ Artist:                                 │ │
│ │ (empty)      →    Artist Name           │ │
│ │ ☑ Apply                                 │ │
│ │                                         │ │
│ │ Tags: (15 tags)                         │ │
│ │ (empty)      →    tag1, tag2, tag3...   │ │
│ │ ☑ Apply                                 │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Overwrite existing: [No ▼]                  │
│                                             │
│ [Apply Selected]  [Cancel]                  │
└─────────────────────────────────────────────┘
```

#### B. Library Page - Bulk Scan

```
┌─────────────────────────────────────────────┐
│ Library: My Doujinshi Collection            │
│                                             │
│ 1,247 comics                                │
│                                             │
│ [Scan All Comics]                           │
└─────────────────────────────────────────────┘
```

During scanning:
```
┌─────────────────────────────────────────────┐
│ Scanning Library...                         │
│                                             │
│ Progress: 423 / 1,247 comics (34%)          │
│ ████████████░░░░░░░░░░░░░░░░░░░░            │
│                                             │
│ Matched: 312 (74%)                          │
│ No Match: 111 (26%)                         │
│                                             │
│ Current: [Artist] Comic 423.cbz             │
│ Scanning with nhentai...                    │
│                                             │
│ [Pause]  [Cancel]                           │
└─────────────────────────────────────────────┘
```

After scanning:
```
┌─────────────────────────────────────────────┐
│ Scan Complete                               │
│                                             │
│ Total: 1,247 comics                         │
│ ✅ Matched: 892 (72%)                       │
│ ❌ No Match: 355 (28%)                      │
│                                             │
│ Confidence Breakdown:                        │
│   EXACT (95-100%):   534 comics             │
│   HIGH (75-94%):     243 comics             │
│   MEDIUM (50-74%):   115 comics             │
│   LOW (30-49%):      0 comics               │
│                                             │
│ [Review Results]  [Apply All]               │
└─────────────────────────────────────────────┘
```

#### C. Batch Review Page

```
┌─────────────────────────────────────────────────────────┐
│ Review Scanned Metadata (892 matches)                   │
│                                                         │
│ Filter: [All ▼]  Confidence: [All ▼]  Sort: [Name ▼]   │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☑  [Artist] Comic 1.cbz              85% (HIGH)     │ │
│ │    7 fields would be updated                        │ │
│ │    Title, Artist, Tags, Language...                 │ │
│ │                                       [Preview]      │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ ☑  [Artist] Comic 2.cbz              100% (EXACT)   │ │
│ │    5 fields would be updated                        │ │
│ │    Title, Artist, Tags...                           │ │
│ │                                       [Preview]      │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ ☑  [Artist] Comic 3.cbz              72% (MEDIUM)   │ │
│ │    6 fields would be updated                        │ │
│ │    Title, Artist, Genre...                          │ │
│ │                                       [Preview]      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Select: [All] [None] [HIGH+ only] [EXACT only]         │
│                                                         │
│ Apply to: ☑ Empty fields only  ☐ Overwrite existing    │
│                                                         │
│ Fields to apply:                                        │
│   ☑ Title      ☑ Artist      ☑ Tags                    │
│   ☑ Language   ☐ Characters  ☐ Genre                   │
│                                                         │
│ [Apply to 892 Comics]  [Cancel]                         │
└─────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core API ✅ (Partially Done)
- [x] Metadata schema
- [x] Metadata service
- [ ] Scan endpoints
- [ ] Preview endpoints
- [ ] Apply endpoints

### Phase 2: Database Schema
- [ ] Create scan_jobs table
- [ ] Create scan_results table
- [ ] Add migration script

### Phase 3: Background Jobs
- [ ] Job queue system (or simple threading)
- [ ] Progress tracking
- [ ] Job status API

### Phase 4: UI - Single Comic
- [ ] Scan button on comic details
- [ ] Preview modal
- [ ] Field selection
- [ ] Apply confirmation

### Phase 5: UI - Library Scan
- [ ] Scan all button
- [ ] Progress display
- [ ] Batch review page
- [ ] Bulk apply

## Example Usage Flow

### Single Comic Scan

**1. User clicks "Scan for Metadata" on comic**
```bash
POST /v2/scanners/comics/123/scan
Response: {
  "scan_result": {
    "confidence": 0.85,
    "metadata": {...},
    "preview": {
      "fields": [
        {"field": "title", "current": null, "new": "Comic Title", ...},
        ...
      ]
    }
  }
}
```

**2. User reviews preview, selects fields**
```
UI shows checkboxes for each field
User selects which ones to apply
```

**3. User applies**
```bash
POST /v2/scanners/comics/123/apply
{
  "confidence": 0.85,
  "metadata": {...},
  "overwrite": false,
  "selected_fields": ["title", "artist", "tags"]
}

Response: {
  "success": true,
  "fields_updated": ["title", "artist", "tags"]
}
```

### Library Bulk Scan

**1. User clicks "Scan All Comics"**
```bash
POST /v2/scanners/libraries/1/scan
Response: {
  "job_id": "scan_job_123",
  "status": "pending",
  "total_comics": 1247
}
```

**2. Poll for progress**
```bash
GET /v2/scanners/jobs/scan_job_123
Response: {
  "status": "running",
  "progress": {
    "total": 1247,
    "scanned": 423,
    "matched": 312,
    "percentage": 34
  }
}
```

**3. Job completes**
```bash
GET /v2/scanners/jobs/scan_job_123
Response: {
  "status": "completed",
  "results": {
    "total": 1247,
    "matched": 892,
    "no_match": 355
  },
  "scan_results_url": "/v2/scanners/jobs/scan_job_123/results"
}
```

**4. Review results**
```bash
GET /v2/scanners/jobs/scan_job_123/results
Response: {
  "results": [
    {
      "comic_id": 1,
      "filename": "comic1.cbz",
      "confidence": 0.85,
      "preview": {...}
    },
    ...
  ]
}
```

**5. Bulk apply**
```bash
POST /v2/scanners/libraries/1/apply-batch
{
  "scan_results": [
    {"comic_id": 1, "apply": true, "selected_fields": [...]},
    {"comic_id": 2, "apply": true, "selected_fields": [...]},
    ...
  ],
  "overwrite": false
}
```

## Scanner Capabilities System

Each scanner declares what it can provide:

```python
nhentai_capabilities = {
    "title": "primary",      # High confidence
    "artist": "primary",     # High confidence
    "tags": "primary",       # High confidence
    "genre": "secondary",    # Derived from tags
    "language": "secondary",
    "characters": "secondary",
    "page_count": "technical"
}
```

This allows the UI to:
1. Show which fields are available
2. Highlight high-confidence fields
3. Group fields by category
4. Show tooltips explaining what each field means

## Next Steps

1. **Implement scan endpoints** - Add POST endpoints for scanning
2. **Create database tables** - Add scan_jobs and scan_results
3. **Build preview UI** - Show metadata before applying
4. **Add apply endpoints** - Save metadata to comics
5. **Build bulk scan UI** - Scan entire libraries with progress

---

**Version:** 2.0.0
**Status:** In Progress
**Last Updated:** 2025-11-14
