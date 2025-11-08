# Scanning Bottleneck Analysis

## Performance Profile

### Test File: Real Manga Volume (127 MB)

```
Total Time: 405ms per comic

Breakdown:
  Thumbnail generation:  217ms (54%)
  MD5 Hash calculation:  171ms (42%)
  Cover extraction:       11ms ( 3%)
  Open archive:            5ms ( 1%)
  Get page count:         <1ms
  Load metadata:          <1ms
```

### Current Performance

**Real Libraries (8 workers):**
- Comics (14 files): **8.4 comics/sec**
- Manga (25 files, ~127MB each): **8.2 comics/sec**

**The bottleneck is file I/O**, not threading!

---

## Root Causes

### 1. MD5 Hashing (42% of time)

**Current Implementation:**
```python
def calculate_file_hash(file_path: Path) -> str:
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):  # 8KB chunks
            md5.update(chunk)
    return md5.hexdigest()
```

**Problem:** Must read entire file (127MB) sequentially

**Impact:**
- 127MB file = 171ms
- 1000 comics @ 100MB avg = ~2.8 minutes just hashing!

---

### 2. Thumbnail Generation (54% of time)

**Current Implementation:**
```python
# Extract full-resolution cover from archive
cover_image = comic.extract_page_as_image(0)

# Resize to 300px (JPEG) and 400px (WebP)
generate_dual_thumbnails(cover_image, covers_dir, file_hash)
```

**Problem:** PIL image processing is CPU-intensive

**Impact:**
- 217ms per comic for dual thumbnails
- 1000 comics = ~3.6 minutes just thumbnail generation

---

## Potential Optimizations

### Option 1: Parallel Hashing (Easiest) ⚡

**Idea:** Hash files in parallel while scanning directories

```python
# Phase 1: Discover files + calculate hashes (parallel)
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(calculate_file_hash, f): f for f in comic_files}
    hash_map = {path: future.result() for path, future in futures.items()}

# Phase 2: Process comics with pre-calculated hashes
```

**Benefit:** Hash calculation happens concurrently with discovery
**Gain:** ~40% faster (hash becomes "free" during discovery)

---

### Option 2: Partial File Hashing ⚡⚡

**Idea:** Hash only first + last chunks instead of entire file

```python
def calculate_fast_hash(file_path: Path) -> str:
    """Hash first 1MB + last 1MB + file size"""
    size = file_path.stat().st_size
    md5 = hashlib.md5()

    with open(file_path, 'rb') as f:
        # First 1MB
        md5.update(f.read(min(1024*1024, size)))

        # Last 1MB (if file > 1MB)
        if size > 1024*1024:
            f.seek(-1024*1024, 2)
            md5.update(f.read(1024*1024))

        # Add file size to hash
        md5.update(str(size).encode())

    return md5.hexdigest()
```

**Benefit:** Only read 2MB instead of 127MB
**Risk:** Small chance of collision if files have identical start/end
**Gain:** 60-80x faster on large files (171ms → 2-3ms)

---

### Option 3: Use xxHash Instead of MD5 ⚡⚡⚡

**Idea:** xxHash is 10x faster than MD5

```python
import xxhash

def calculate_file_hash(file_path: Path) -> str:
    h = xxhash.xxh64()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):  # Larger chunks
            h.update(chunk)
    return h.hexdigest()
```

**Benefit:** 10x faster hashing
**Compatibility:** Can still use for duplicate detection
**Gain:** 171ms → 17ms (90% reduction)

---

### Option 4: Optimize PIL Thumbnail Generation ⚡

**Current:** Generate at full resolution, then resize

**Optimized:** Use PIL's thumbnail() method with LANCZOS

```python
def generate_thumbnail_optimized(image: Image.Image, max_size):
    """Optimized thumbnail generation"""
    # Create a copy and use in-place thumbnail
    thumb = image.copy()
    thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
    return thumb
```

**Already implemented!** Check if we're using it correctly.

---

### Option 5: Skip Duplicate Thumbnail Generation ✅

**Already implemented:**
```python
if thumbnail_exists(covers_dir, file_hash, 'JPEG'):
    return  # Skip if already exists
```

**Works perfectly:** Re-scans are 80x faster (1,603 comics/sec)

---

## Recommended Optimizations (Ranked)

### Quick Wins (Implement Now)

1. **Use xxHash instead of MD5** ⚡⚡⚡
   - Effort: Low (pip install xxhash)
   - Gain: 90% faster hashing
   - Risk: None (just for duplicate detection)
   - **Expected: 8 → 15 comics/sec**

2. **Increase hash chunk size** ⚡
   - Effort: Trivial (change 8192 → 65536)
   - Gain: 20-30% faster hashing
   - Risk: None
   - **Expected: 8 → 10 comics/sec**

### Medium Effort

3. **Optimize PIL operations** ⚡
   - Effort: Medium (review PIL usage)
   - Gain: 10-20% faster thumbnails
   - Risk: None
   - **Expected: +1-2 comics/sec**

4. **Parallel hashing during discovery** ⚡⚡
   - Effort: Medium (restructure scanner)
   - Gain: Hash becomes "free" (40%)
   - Risk: Higher memory usage
   - **Expected: 8 → 12 comics/sec**

### Advanced (Consider Later)

5. **Partial file hashing** ⚡⚡
   - Effort: Low
   - Gain: Massive on large files
   - Risk: Small collision chance
   - **Best for:** Initial scans only

6. **Process pool instead of thread pool** ⚡⚡
   - Effort: High (rewrite for multiprocessing)
   - Gain: Better CPU utilization
   - Risk: More complex, harder debugging
   - **Expected: 8 → 20+ comics/sec**

---

## Implementation Priority

### Phase 1: Quick Wins (30 minutes)

```bash
# 1. Install xxhash
pip install xxhash

# 2. Update hash function (10 lines)
# 3. Increase chunk size (1 line)
# 4. Test
```

**Expected result:** 8 → 15-18 comics/sec (2x improvement)

### Phase 2: Medium Effort (2-3 hours)

```bash
# 1. Parallel hash calculation
# 2. Optimize PIL thumbnail settings
# 3. Profile again
```

**Expected result:** 15 → 25 comics/sec (3x improvement)

### Phase 3: Advanced (Future)

- Process pool for true parallelism
- GPU-accelerated thumbnail generation
- Incremental scanning (only new/modified files)

---

## Real-World Impact

### Current Performance (8 comics/sec)

| Library Size | Current Time | With xxHash | With Parallel |
|--------------|--------------|-------------|---------------|
| 100 comics   | 12.5 sec     | 7 sec       | 5 sec         |
| 500 comics   | 62 sec       | 33 sec      | 20 sec        |
| 1,000 comics | 2.1 min      | 1.1 min     | 40 sec        |
| 5,000 comics | 10.4 min     | 5.5 min     | 3.3 min       |
| 10,000 comics| 20.8 min     | 11 min      | 6.7 min       |

---

## Why We're Slower Than Expected

**Initial estimate:** 137 comics/sec (with tiny 18KB test files)
**Reality:** 8 comics/sec (with real 127MB manga volumes)

**Reason:** File size matters!
- 18KB file: 22ms total (0.1ms hash + 16ms thumbnail)
- 127MB file: 405ms total (171ms hash + 217ms thumbnail)

**File size is 7,000x larger, processing is 18x slower**

This is actually pretty good! We're doing well considering:
- Must read entire files for hashing
- Must decompress images for thumbnails
- Storage I/O is the bottleneck, not CPU

---

## Conclusion

**Current performance is reasonable** for large files, but can be improved:

1. **Quick win:** xxHash → 2x faster
2. **Medium effort:** Parallel hashing → 1.5x faster
3. **Combined:** Could reach 20-30 comics/sec

**Is it worth it?**
- For 100 comics: Probably not (12s → 5s)
- For 10,000 comics: Definitely! (21min → 6-7min)

**Recommendation:**
- Implement xxHash optimization (easy, big win)
- Document the bottlenecks for users
- Consider parallel hashing for v2.0

---

## Testing Your Libraries

Based on your real manga volumes at ~127MB each:

```bash
# Test current performance
python examples/scan_library_fast.py tests/testlibs "Test" 8

# Expected:
# - 39 comics in ~5 seconds
# - Rate: 7-8 comics/sec
```

This is **normal and expected** for large files!

For comparison:
- Small files (18KB): 137 comics/sec
- Large files (127MB): 8 comics/sec
- **Ratio: 17x slower due to 7,000x file size**

The scanner is actually quite efficient! 💪
