# Testing Performance Improvements

Quick guide to test the performance optimizations implemented on 2025-11-11.

## Quick Start

```bash
# 1. Navigate to webui directory
cd webui

# 2. Install dependencies (if needed)
npm install

# 3. Build for production
npm run build

# 4. Start production preview server
npm run preview
```

The server should start on `http://localhost:4173` (or similar).

## What to Test

### 1. Initial Load Performance ⚡

**Before optimizations:** ~2.2 seconds
**Expected now:** < 1 second

**How to test:**
1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Check "Disable cache"
4. Hard refresh (Cmd+Shift+R or Ctrl+Shift+F5)
5. Look at the timeline to see when page becomes interactive

**What to look for:**
- ✅ Page shows skeleton loading screens immediately
- ✅ Content appears within 1 second
- ✅ No long blank white screen
- ✅ Fewer API requests on initial load

### 2. Server-Side Rendering (SSR) 🚀

**What was added:** Data loads on server before page renders

**How to test:**
1. View page source (right-click → View Page Source)
2. Look for data in the HTML (should see script tags with preloaded data)
3. Network tab should show fewer requests

**What to look for:**
- ✅ HTML includes data (not just empty divs)
- ✅ Faster initial render
- ✅ Series tree loads immediately

### 3. Progressive Loading 📦

**What was added:** Only first library loads initially, rest in background

**How to test:**
1. Open console (F12 → Console tab)
2. Refresh page
3. Watch for console logs:
   - `[Home] Using server-side rendered data`
   - `[Home] Loading remaining libraries data in background...`
   - `[Home] Remaining libraries loaded successfully`

**What to look for:**
- ✅ Page becomes interactive quickly
- ✅ First library data shows immediately
- ✅ Other libraries load in background
- ✅ No visible delay or loading spinners

### 4. Search Responsiveness 🔍

**What was changed:** Debounce increased from 300ms to 500ms

**How to test:**
1. Use the search box
2. Type quickly: "batman"
3. Watch the console for `[Home] Debounce timer fired`

**What to look for:**
- ✅ Search waits 500ms after you stop typing
- ✅ No lag during typing
- ✅ Smooth filtering when search triggers
- ✅ Fewer console logs (less filtering)

### 5. Skeleton Loading Screens 💀

**What was added:** Animated placeholders during loading

**How to test:**
1. Hard refresh with cache disabled
2. Watch the initial load

**What to look for:**
- ✅ Shimmer animation on cards while loading
- ✅ Layout matches final content
- ✅ No content jumping or layout shift
- ✅ Professional loading experience

### 6. Carousel Scroll Performance 🎠

**What was changed:** Throttled scroll events, passive listeners

**How to test:**
1. Scroll the "Continue Reading" carousel
2. Open DevTools Performance tab
3. Start recording
4. Scroll the carousel
5. Stop recording and analyze

**What to look for:**
- ✅ Smooth 60fps scrolling
- ✅ No janky/stuttering movement
- ✅ Scroll events throttled to ~16ms
- ✅ Low CPU usage during scroll

### 7. Repeat Visit Performance 🔄

**What was changed:** Better caching (15min stale, 30min gc time)

**How to test:**
1. Load page normally (don't disable cache)
2. Navigate away
3. Come back to home page within 30 minutes

**What to look for:**
- ✅ Near-instant load
- ✅ No API requests (served from cache)
- ✅ Content appears immediately
- ✅ No loading states

## Performance Metrics to Check

### Chrome DevTools Lighthouse

```bash
1. Open DevTools (F12)
2. Click "Lighthouse" tab
3. Select "Performance" category
4. Click "Generate report"
```

**Target scores:**
- Performance: > 90
- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Time to Interactive: < 3.8s
- Speed Index: < 3.4s

### Network Tab Analysis

**Check these metrics in Network tab:**

| Resource | Before | After | Target |
|----------|--------|-------|--------|
| series-tree | 1,061 KB / 1.39s | Same | < 1.5s |
| series?sort=recent | 947 KB / 2.19s | Fewer | < 1s |
| reading?limit=50 | 212 KB / 2.18s | Fewer | < 1s |
| Total initial | 2+ MB | < 1.5 MB | < 1.5 MB |
| Total requests | 20+ | < 15 | < 15 |

### Console Logs to Monitor

Enable verbose logging:

```javascript
// Check console for these messages:
✅ [Home] Using server-side rendered data
✅ [Home] Loading remaining libraries data in background...
✅ [Home] Remaining libraries loaded successfully
✅ [Home] Debounce timer fired, calling handleSearch
```

## Troubleshooting

### Issue: SSR not working (falls back to client-side)

**Symptoms:**
- Console shows: `[Home] Server data not available, loading client-side`
- Slow initial load

**Fix:**
1. Check that backend API is running on `http://localhost:8081`
2. Update `API_BASE_URL` in `+page.server.js` if using different port
3. Ensure build was successful: `npm run build`

### Issue: Skeleton screens not showing

**Symptoms:**
- Blank screen during loading
- No shimmer animation

**Fix:**
1. Check browser console for errors
2. Ensure `SkeletonCard.svelte` was created
3. Hard refresh to clear cache

### Issue: Progressive loading not working

**Symptoms:**
- All data loads at once
- Long wait before content appears

**Fix:**
1. Check console for background loading messages
2. Ensure you have multiple libraries (progressive loading only helps with 2+)
3. Check network tab to see if requests are sequential

### Issue: Carousel scroll is still janky

**Symptoms:**
- Stuttering during scroll
- High CPU usage

**Fix:**
1. Check if other extensions are interfering
2. Test in incognito mode
3. Check Performance tab for long tasks
4. Ensure HorizontalCarousel.svelte changes were applied

## Comparing Before/After

### Test Setup

```bash
# To test "before" optimizations:
git stash  # Stash the new changes
npm run build
npm run preview
# Test and record metrics

# To test "after" optimizations:
git stash pop  # Restore changes
npm run build
npm run preview
# Test and compare metrics
```

### Metrics to Compare

1. **Time to Interactive** (DevTools Performance tab)
2. **Total API payload** (Network tab, bottom right)
3. **Number of requests** (Network tab)
4. **Lighthouse Performance score**
5. **Perceived performance** (subjective, but important!)

## Expected Results Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Initial load | 2.2s | ~0.7s | 68% faster |
| Data transferred | 2+ MB | ~800 KB | 60% less |
| Repeat visit | 2.2s | <200ms | 90% faster |
| Search lag | Noticeable | Minimal | 40% better |
| Scroll FPS | 30-45 fps | 60 fps | Smooth |

## Production Testing

Before deploying to production:

1. **Test with throttling:**
   - DevTools → Network tab → Throttling: "Fast 3G"
   - Ensure page still loads in < 3 seconds

2. **Test on mobile:**
   - Use DevTools device emulation
   - Test on real mobile device if possible
   - Ensure touch scrolling works

3. **Test with large libraries:**
   - Test with 100+ series
   - Test with 10+ libraries
   - Ensure performance doesn't degrade

4. **Test error scenarios:**
   - Backend offline
   - Slow network
   - Empty libraries
   - Search with no results

## Questions?

Check these docs:
- `docs/PERFORMANCE_OPTIMIZATION_PLAN.md` - Full optimization plan
- `docs/PERFORMANCE_IMPROVEMENTS_SUMMARY.md` - Summary of changes
- `docs/ARCHITECTURE_UPDATE_2025.md` - Architecture overview

Or review the code:
- `webui/src/routes/+page.server.js` - SSR implementation
- `webui/src/routes/+page.svelte` - Progressive loading
- `webui/src/lib/components/common/SkeletonCard.svelte` - Loading UI
