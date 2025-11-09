# Administrative & Utility Tools

Admin and debugging tools for YACLib Enhanced.

## Available Tools

### `import_yacreader.py`

Import existing library data from YACReader.

**Usage:**
```bash
python tools/import_yacreader.py
```

**What it does:**
- Imports libraries from YACReader database
- Migrates metadata and reading progress
- Preserves folder structure
- Useful when migrating from YACReader

---

### `debug_folders.py`

Debug and validate folder relationships in the database.

**Usage:**
```bash
python tools/debug_folders.py
```

**What it checks:**
- Folder parent-child relationships
- Circular references
- Invalid parent IDs
- Self-referencing folders
- Orphaned folders

**When to use:**
- After bulk imports
- When folder navigation behaves oddly
- Database troubleshooting
- Verifying database integrity

**Output:**
```
Library: My Comics (ID: 1)
Total folders: 25

  Folder   1: Comics/                    | Parent: ROOT
  Folder   2: Marvel/                    | Parent: 1 (Comics)
  Folder   3: DC/                        | Parent: 1 (Comics)
  ...

✅ No folder relationship issues found in 'My Comics'
```

---

### `test_folder_api.py`

Test and debug folder API responses.

**Usage:**
```bash
python tools/test_folder_api.py <library_id> <folder_id>
```

**Arguments:**
- `library_id` - Library ID to test
- `folder_id` - Folder ID (use 0 for root)

**Example:**
```bash
# Test root folder of library 1
python tools/test_folder_api.py 1 0

# Test specific folder
python tools/test_folder_api.py 1 5
```

**What it shows:**
- Child folders in the specified folder
- Comics in the specified folder
- What the API would return
- Useful for debugging navigation issues

**Output:**
```
Testing: GET /v2/library/1/folder/0
Library: My Comics (ID: 1)
Folder ID: 0

Folders to return (3):
  - Marvel (ID: 2, parent: 1)
  - DC (ID: 3, parent: 1)
  - Image (ID: 4, parent: 1)

Comics to return (5):
  - standalone1.cbz (ID: 100, folder: 1)
  - standalone2.cbz (ID: 101, folder: 1)

Total items: 8
```

---

## Database Migrations

Migration scripts for updating the database schema.

### `migrations/migrate_to_yacreader_schema.py`

Migrate existing YACLib database to full YACReader compatibility.

**Usage:**
```bash
python tools/migrations/migrate_to_yacreader_schema.py
```

**What it does:**
- Creates `__ROOT__` folders for each library
- Updates folder parent relationships
- Assigns root-level comics to root folder
- Makes database YACReader-compatible

**When to run:**
- After upgrading from older YACLib versions
- When adding YACReader compatibility
- If folder navigation shows issues

**Safe to run multiple times** - it's idempotent.

---

### `migrations/apply_migration.py`

Apply raw SQL migration files.

**Usage:**
```bash
python tools/migrations/apply_migration.py <database_path>
```

**Example:**
```bash
python tools/migrations/apply_migration.py ~/.local/share/yaclib/yaclib.db
```

**What it does:**
- Applies SQL migrations from `migrations/*.sql`
- Adds new fields and tables
- Updates schema to latest version

---

### `migrations/apply_migration_v2.py`

Advanced migration script with SQLite compatibility handling.

**Usage:**
```bash
python tools/migrations/apply_migration_v2.py <database_path>
```

**Features:**
- Handles SQLite ALTER TABLE limitations
- Checks for existing columns before adding
- Table recreation when needed
- More robust than v1

**Use this if:**
- `apply_migration.py` fails
- You need careful migration handling
- Working with complex schema changes

---

## Database Location

Default database paths:
- **Linux:** `~/.local/share/yaclib/yaclib.db`
- **macOS:** `~/Library/Application Support/YACLib/yaclib.db`
- **Windows:** `%APPDATA%/YACLib/yaclib.db`

## When to Use These Tools

| Tool | When to Use |
|------|-------------|
| `import_yacreader.py` | Migrating from YACReader |
| `debug_folders.py` | Folder navigation issues, database validation |
| `test_folder_api.py` | API debugging, testing specific folders |
| `migrations/*.py` | Database upgrades, schema updates |

## See Also

- [scripts/](../scripts/) - Production library scanners
- [examples/](../examples/) - Example usage scripts
- [tests/](../tests/) - Test scripts
- [YACREADER_API_COMPATIBILITY.md](../YACREADER_API_COMPATIBILITY.md) - Compatibility docs
