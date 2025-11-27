# Scanner Scan Level Configuration

## Overview

Each scanner now explicitly defines its **scan level** in its configuration file, which determines how the scanner operates and what UI options are available to users.

## Scan Levels

### FILE Level
- **Operates on**: Individual files/volumes
- **Example Scanner**: nhentai
- **UI Behavior**: Shows "Scan Files" button, scans each comic file individually
- **Use Case**: Doujinshi, one-shots, individual releases

### SERIES Level
- **Operates on**: Entire manga/comic series
- **Example Scanner**: AniList
- **UI Behavior**: Shows "Scan Series" button, scans series metadata
- **Use Case**: Manga series, light novels, ongoing comics

## Configuration Files

### nhentai (`scanners/nhentai/config.json`)
```json
{
  "scanner_name": "nhentai",
  "scan_level": "FILE",
  "scanning_mode": "individual_files",
  ...
}
```

### AniList (`scanners/AniList/config.json`)
```json
{
  "scanner_name": "AniList",
  "scan_level": "SERIES",
  "scanning_mode": "by_series",
  ...
}
```

## How It Works

1. **Scanner Definition**: Each scanner's `scan_level` property in `base_scanner.py` defines whether it's FILE or SERIES level

2. **API Response**: The `/v2/scanners/libraries` endpoint returns each library's configuration including the `scan_level` of its configured scanner

3. **UI Adaptation**: The `LibraryScannerPanel` component reads the `scan_level` and adjusts its display:
   - Button text: "Scan Files" vs "Scan Series"
   - Confirmation dialog: "individual files" vs "series"
   - Info display: "(Individual Files)" vs "(By Series)"

## Example User Experience

### Library with nhentai Scanner (FILE level)
```
Scanner: nhentai (Individual Files)
[Scan Files] [Clear Metadata]
```
When clicked: "Scan all individual files in library?"

### Library with AniList Scanner (SERIES level)
```
Scanner: AniList (By Series)
[Scan Series] [Clear Metadata]
```
When clicked: "Scan all series in library?"

## Benefits

1. **Clear User Intent**: Users immediately understand what type of scanning will happen
2. **Appropriate Expectations**: FILE scanners process each file, SERIES scanners process by series name
3. **Extensible**: Easy to add new scanners with their appropriate scan level
4. **Type Safety**: Scan level is part of the scanner's API contract

## API Changes

### ScannerInfo Model
```python
class ScannerInfo(BaseModel):
    name: str
    scan_level: ScanLevelEnum  # "file" or "series"
    description: Optional[str]
    ...
```

### LibraryScannerConfig Model
```python
class LibraryScannerConfig(BaseModel):
    library_id: int
    library_name: str
    primary_scanner: Optional[str]
    scan_level: Optional[ScanLevelEnum]  # Derived from scanner
    ...
```

## Future Scanners

When adding a new scanner:

1. Set `scan_level` in the scanner class:
   ```python
   @property
   def scan_level(self) -> ScanLevel:
       return ScanLevel.SERIES  # or ScanLevel.FILE
   ```

2. Add to `config.json`:
   ```json
   {
     "scanner_name": "YourScanner",
     "scan_level": "SERIES",  # or "FILE"
     "scanning_mode": "by_series"  # or "individual_files"
   }
   ```

3. The UI will automatically adapt based on the scan level!
