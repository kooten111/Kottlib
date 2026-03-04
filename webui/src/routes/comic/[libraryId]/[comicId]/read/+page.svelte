<script>
	import { onMount, onDestroy } from "svelte";
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import { readerSettings } from "$lib/stores/reader";
	import {
		getComic,
		getComicPage,
		updateReadingProgress,
	} from "$lib/api/comics";
	import PageViewer from "$lib/components/reader/PageViewer.svelte";
	import ReaderControls from "$lib/components/reader/ReaderControls.svelte";
	import ReaderSettings from "$lib/components/reader/ReaderSettings.svelte";
	import ReaderMenu from "$lib/components/reader/ReaderMenu.svelte";

	// Extract route parameters
	$: libraryId = parseInt($page.params.libraryId);
	$: comicId = parseInt($page.params.comicId);
	$: startPage = parseInt($page.url.searchParams.get("page") || "1") || 1;

	// Component state
	let comic = null;
	let currentPage = 1; // Start with page 1, will be updated in onMount
	let totalPages = 0;
	let isLoading = true;
	let isFullscreen = false;
	let showSettings = false;
	let showControls = true;
	let controlsTimeout;
	let currentPageImage = "";
	let secondPageImage = "";
	let preloadedPages = new Map();
	let showReaderMenu = false;

	// Reactive helpers
	$: isDoubleMode = $readerSettings.readingMode === 'double';

	// Get adjacent page sources for swipe transitions
	$: nextPageSrc = getAdjacentPageSrc("next");
	$: prevPageSrc = getAdjacentPageSrc("previous");

	function getAdjacentPageSrc(direction) {
		const isRTL = $readerSettings.readingDirection === "rtl";
		const step = isDoubleMode ? 2 : 1;
		let targetPage;

		if (direction === "next") {
			targetPage = isRTL ? currentPage - step : currentPage + step;
		} else {
			targetPage = isRTL ? currentPage + step : currentPage - step;
		}

		if (
			targetPage >= 1 &&
			targetPage <= totalPages &&
			preloadedPages.has(targetPage)
		) {
			return preloadedPages.get(targetPage);
		}
		return "";
	}

	// Load comic data
	onMount(async () => {
		try {
			// Load library-specific reader settings
			await readerSettings.loadForLibrary(libraryId);

			comic = await getComic(libraryId, comicId);
			totalPages = comic.num_pages || comic.numPages || 0;

			// Set initial page
			if (startPage && startPage > 0) {
				// User explicitly specified a page in URL
				currentPage = startPage;
			} else if ((comic.current_page || comic.currentPage || 0) > 0) {
				// Restore reading progress
				currentPage = comic.current_page || comic.currentPage;
			} else {
				// Start from beginning
				currentPage = 1;
			}

					// Load initial page
			await loadPage(currentPage);

			// If continuous mode, load initial pages around current page
			if ($readerSettings.readingMode === 'continuous') {
				await loadInitialPages();
			}

			// Setup keyboard shortcuts and beforeunload handler
			if (typeof document !== "undefined") {
				document.addEventListener("keydown", handleKeyPress);
				document.addEventListener("mousemove", handleMouseMove);
				document.addEventListener("beforeunload", handleBeforeUnload);
			}
		} catch (error) {
			console.error("Failed to load comic:", error);
		}
	});

	onDestroy(() => {
		// Save progress immediately before cleanup
		saveFinalProgress();
		
		if (typeof document !== "undefined") {
			document.removeEventListener("keydown", handleKeyPress);
			document.removeEventListener("mousemove", handleMouseMove);
			document.removeEventListener("beforeunload", handleBeforeUnload);
		}
		if (controlsTimeout) {
			clearTimeout(controlsTimeout);
		}
		if (progressTimeout) {
			clearTimeout(progressTimeout);
		}
	});

	// Load page image
	async function loadPage(pageNum) {
		try {
			isLoading = true;

			// Check if already preloaded
			if (preloadedPages.has(pageNum)) {
				currentPageImage = preloadedPages.get(pageNum);
				isLoading = false;
			} else {
				const blob = await getComicPage(libraryId, comicId, pageNum);
				const url = URL.createObjectURL(blob);
				currentPageImage = url;
				preloadedPages.set(pageNum, url);
				isLoading = false;
			}

			// Load the paired second page in double-page mode
			if (isDoubleMode) {
				const secondPageNum = pageNum + 1;
				if (secondPageNum >= 1 && secondPageNum <= totalPages) {
					if (preloadedPages.has(secondPageNum)) {
						secondPageImage = preloadedPages.get(secondPageNum);
					} else {
						try {
							const blob2 = await getComicPage(libraryId, comicId, secondPageNum);
							const url2 = URL.createObjectURL(blob2);
							preloadedPages.set(secondPageNum, url2);
							secondPageImage = url2;
						} catch (e) {
							secondPageImage = '';
						}
					}
				} else {
					secondPageImage = ''; // Last page of odd-length comic
				}
			} else {
				secondPageImage = '';
			}

			// Preload adjacent pages
			preloadAdjacentPages(pageNum);

			// Save reading progress (debounced)
			saveProgress(pageNum);
		} catch (error) {
			console.error("Failed to load page:", pageNum, error);
			isLoading = false;
		}
	}

	// Preload adjacent pages
	async function preloadAdjacentPages(pageNum) {
		const preloadCount = $readerSettings.preloadPages;
		const isRTL = $readerSettings.readingDirection === "rtl";

		// Immediately preload the very next and previous pages (for swipe transitions)
		const immediateNext = isRTL ? pageNum - 1 : pageNum + 1;
		const immediatePrev = isRTL ? pageNum + 1 : pageNum - 1;

		// Preload immediate neighbors with priority
		const priorityPromises = [];
		if (
			immediateNext >= 1 &&
			immediateNext <= totalPages &&
			!preloadedPages.has(immediateNext)
		) {
			priorityPromises.push(preloadPage(immediateNext));
		}
		if (
			immediatePrev >= 1 &&
			immediatePrev <= totalPages &&
			!preloadedPages.has(immediatePrev)
		) {
			priorityPromises.push(preloadPage(immediatePrev));
		}

		// Wait for immediate neighbors to load before continuing
		await Promise.all(priorityPromises);

		// Then preload the rest in the background
		for (let i = 2; i <= preloadCount; i++) {
			const nextPage = isRTL ? pageNum - i : pageNum + i;
			const prevPage = isRTL ? pageNum + i : pageNum - i;

			if (
				nextPage >= 1 &&
				nextPage <= totalPages &&
				!preloadedPages.has(nextPage)
			) {
				preloadPage(nextPage);
			}
			if (
				prevPage >= 1 &&
				prevPage <= totalPages &&
				!preloadedPages.has(prevPage)
			) {
				preloadPage(prevPage);
			}
		}
	}

	// Preload a single page
	async function preloadPage(pageNum) {
		try {
			const blob = await getComicPage(libraryId, comicId, pageNum);
			const url = URL.createObjectURL(blob);
			preloadedPages.set(pageNum, url);
			preloadedPages = preloadedPages; // Force Svelte reactivity
		} catch (error) {
			console.error(`Failed to preload page ${pageNum}:`, error);
		}
	}

	// Load initial pages for continuous scroll mode (around current page)
	async function loadInitialPages() {
		if (totalPages === 0) return;

		const preloadCount = $readerSettings.preloadPages || 3;
		const isRTL = $readerSettings.readingDirection === "rtl";
		
		// Load current page and nearby pages
		const pagesToLoad = [];
		
		// Always load current page
		if (!preloadedPages.has(currentPage)) {
			pagesToLoad.push(currentPage);
		}
		
		// Load pages ahead and behind
		for (let i = 1; i <= preloadCount * 2; i++) {
			// Pages ahead (in reading direction)
			const aheadPage = isRTL ? currentPage - i : currentPage + i;
			if (aheadPage >= 1 && aheadPage <= totalPages && !preloadedPages.has(aheadPage)) {
				pagesToLoad.push(aheadPage);
			}
			
			// Pages behind
			const behindPage = isRTL ? currentPage + i : currentPage - i;
			if (behindPage >= 1 && behindPage <= totalPages && !preloadedPages.has(behindPage)) {
				pagesToLoad.push(behindPage);
			}
		}
		
		// Load pages in parallel (but limit concurrent requests)
		const batchSize = 5;
		for (let i = 0; i < pagesToLoad.length; i += batchSize) {
			const batch = pagesToLoad.slice(i, i + batchSize);
			await Promise.all(batch.map(pageNum => preloadPage(pageNum)));
			// Force reactivity update after each batch
			preloadedPages = preloadedPages;
		}
	}

	// Handle page change from continuous scroll
	function handleContinuousPageChange(newPage) {
		if (newPage !== currentPage && newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			// Save progress in background without blocking
			saveProgress(newPage);
		}
	}

	// Handle prefetch request from PageViewer
	async function handlePrefetchPage(pageNum) {
		if (pageNum < 1 || pageNum > totalPages || preloadedPages.has(pageNum)) {
			return; // Already loaded or invalid
		}

		// Prefetch the page in the background
		preloadPage(pageNum);
	}

	// Watch for reading mode changes
	$: if ($readerSettings.readingMode === 'continuous' && totalPages > 0) {
		// Load initial pages around current page when switching to continuous mode
		loadInitialPages();
	}

	// When switching to double-page mode, snap current page to an odd page (spread start)
	// and reload to ensure the second page is also fetched.
	// Isolate currentPage/totalPages inside a function so this block only re-runs
	// when readingMode itself changes, not on every page turn.
	$: if ($readerSettings.readingMode === 'double') {
		handleDoubleModeActivation();
	}

	function handleDoubleModeActivation() {
		if (totalPages <= 0 || currentPage <= 0) return;
		const snapped = currentPage % 2 === 0 ? Math.max(1, currentPage - 1) : currentPage;
		if (snapped !== currentPage) {
			currentPage = snapped;
		}
		loadPage(currentPage);
	}

	// Save reading progress (debounced and non-blocking)
	let progressTimeout;
	let lastSavedPage = 0;
	let pendingSave = null;
	
	function saveProgress(pageNum) {
		// Don't save if it's the same page we just saved
		if (pageNum === lastSavedPage) {
			return;
		}

		// Cancel any pending save
		if (progressTimeout) {
			clearTimeout(progressTimeout);
			progressTimeout = null;
		}
		if (pendingSave && typeof cancelIdleCallback !== 'undefined') {
			cancelIdleCallback(pendingSave);
			pendingSave = null;
		}

		// Use shorter debounce (1 second instead of 3) for more responsive updates
		progressTimeout = setTimeout(() => {
			lastSavedPage = pageNum;
			progressTimeout = null;
			
			// Use requestIdleCallback if available for truly non-blocking saves
			if (typeof requestIdleCallback !== 'undefined') {
				pendingSave = requestIdleCallback(() => {
					// Fire and forget - don't await
					updateReadingProgress(libraryId, comicId, pageNum).catch(error => {
						// Silently fail - don't log to console during scrolling
						if (error.message && !error.message.includes('Failed to save progress')) {
							console.error("Failed to save progress:", error);
						}
					});
					pendingSave = null;
				}, { timeout: 1500 });
			} else {
				// Fallback: use setTimeout with 0 delay to make it async
				setTimeout(() => {
					updateReadingProgress(libraryId, comicId, pageNum).catch(error => {
						// Silently fail
					});
				}, 0);
			}
		}, 1000); // Save every 1 second max, and only when page changes
	}
	
	// Save final progress immediately (for beforeunload and onDestroy)
	function saveFinalProgress() {
		// Cancel any pending debounced save
		if (progressTimeout) {
			clearTimeout(progressTimeout);
			progressTimeout = null;
		}
		if (pendingSave && typeof cancelIdleCallback !== 'undefined') {
			cancelIdleCallback(pendingSave);
			pendingSave = null;
		}
		
		// Save immediately if page has changed since last save
		if (currentPage !== lastSavedPage && currentPage > 0) {
			lastSavedPage = currentPage;
			// Use sendBeacon for reliability during page unload, fallback to sync fetch
			const data = `currentPage:${Math.max(0, currentPage - 1)}`;
			const url = `/api/libraries/${libraryId}/comics/${comicId}/progress`;
			
			if (navigator.sendBeacon) {
				// sendBeacon is more reliable during page unload
				const blob = new Blob([JSON.stringify({ current_page: Math.max(0, currentPage - 1) })], { type: 'application/json' });
				navigator.sendBeacon(url, blob);
			} else {
				// Fallback to synchronous fetch (less reliable but better than nothing)
				fetch(url, {
					method: 'POST',
					credentials: 'include',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ current_page: Math.max(0, currentPage - 1) }),
					keepalive: true
				}).catch(() => {
					// Ignore errors during unload
				});
			}
		}
	}
	
	// Handle page unload to save final progress
	function handleBeforeUnload(event) {
		saveFinalProgress();
	}

	// Navigate to previous page
	function goToPreviousPage() {
		const isRTL = $readerSettings.readingDirection === "rtl";
		const step = isDoubleMode ? 2 : 1;
		const newPage = isRTL ? currentPage + step : currentPage - step;
		const clampedPage = Math.max(1, Math.min(totalPages, newPage));
		if (clampedPage !== currentPage) {
			currentPage = clampedPage;
			if ($readerSettings.readingMode === 'continuous') {
				if (!preloadedPages.has(clampedPage)) {
					preloadPage(clampedPage);
				}
			} else {
				loadPage(currentPage);
			}
		}
	}

	// Navigate to next page
	function goToNextPage() {
		const isRTL = $readerSettings.readingDirection === "rtl";
		const step = isDoubleMode ? 2 : 1;
		const newPage = isRTL ? currentPage - step : currentPage + step;
		const clampedPage = Math.max(1, Math.min(totalPages, newPage));
		if (clampedPage !== currentPage) {
			currentPage = clampedPage;
			if ($readerSettings.readingMode === 'continuous') {
				if (!preloadedPages.has(clampedPage)) {
					preloadPage(clampedPage);
				}
			} else {
				loadPage(currentPage);
			}
		}
	}

	// Jump to specific page
	function goToPage(pageNum) {
		// In double-page mode, snap to the nearest spread start (odd page)
		if (isDoubleMode && pageNum % 2 === 0) {
			pageNum = Math.max(1, pageNum - 1);
		}
		if (pageNum >= 1 && pageNum <= totalPages && pageNum !== currentPage) {
			currentPage = pageNum;
			if ($readerSettings.readingMode === 'continuous') {
				if (!preloadedPages.has(pageNum)) {
					preloadPage(pageNum);
				}
			} else {
				loadPage(currentPage);
			}
		}
	}

	// Keyboard navigation
	function handleKeyPress(event) {
		// Don't handle if typing in input
		if (event.target.tagName === "INPUT") {
			return;
		}

		switch (event.key) {
			case "ArrowLeft":
				event.preventDefault();
				goToPreviousPage();
				break;
			case "ArrowRight":
				event.preventDefault();
				goToNextPage();
				break;
			case " ":
				event.preventDefault();
				if (event.shiftKey) {
					goToPreviousPage();
				} else {
					goToNextPage();
				}
				break;
			case "f":
			case "F":
				event.preventDefault();
				toggleFullscreen();
				break;
			case "s":
			case "S":
				event.preventDefault();
				showSettings = !showSettings;
				break;
			case "m":
			case "M":
				event.preventDefault();
				showReaderMenu = !showReaderMenu;
				break;
			case "Escape":
				event.preventDefault();
				if (isFullscreen) {
					exitFullscreen();
				} else if (showSettings) {
					showSettings = false;
				} else {
					exitReader();
				}
				break;
			case "PageDown":
				event.preventDefault();
				if ($readerSettings.readingDirection === "rtl") {
					goToPreviousPage();
				} else {
					goToNextPage();
				}
				break;
			case "PageUp":
				event.preventDefault();
				if ($readerSettings.readingDirection === "rtl") {
					goToNextPage();
				} else {
					goToPreviousPage();
				}
				break;
			case "Home":
				event.preventDefault();
				goToPage(1);
				break;
			case "End":
				event.preventDefault();
				goToPage(totalPages);
				break;
			default:
				// Handle number keys 1-9 for percentage jumps
				if (event.key >= "1" && event.key <= "9") {
					event.preventDefault();
					const percent = parseInt(event.key) / 10;
					const targetPage = Math.floor(totalPages * percent);
		// Save progress immediately before exiting
		saveFinalProgress();
					goToPage(Math.max(1, targetPage));
				}
				break;
		}
	}

	// Auto-hide controls
	function handleMouseMove() {
		if (!$readerSettings.autoHideControls) {
			return;
		}

		showControls = true;

		if (controlsTimeout) {
			clearTimeout(controlsTimeout);
		}

		controlsTimeout = setTimeout(() => {
			if (!showSettings) {
				showControls = false;
			}
		}, $readerSettings.autoHideDelay);
	}

	// Toggle fullscreen
	function toggleFullscreen() {
		if (!document.fullscreenElement) {
			document.documentElement.requestFullscreen();
			isFullscreen = true;
		} else {
			exitFullscreen();
		}
	}

	function exitFullscreen() {
		if (document.fullscreenElement) {
			document.exitFullscreen();
		}
		isFullscreen = false;
	}

	// Exit reader - navigate back to previous page (context aware)
	function exitReader() {
		history.back();
	}

	// Event handlers
	function handlePrevious() {
		goToPreviousPage();
	}

	function handleNext() {
		goToNextPage();
	}

	function handlePageChange(event) {
		goToPage(event.detail);
	}

	function handleToggleFullscreen() {
		toggleFullscreen();
	}

	function handleToggleSettings() {
		showSettings = !showSettings;
	}

	function handleExit() {
		exitReader();
	}

	function handleCloseSettings() {
		showSettings = false;
	}

	// Handle PageViewer navigation events
	function handleNavigate(event) {
		const { direction } = event.detail;
		const isRTL = $readerSettings.readingDirection === "rtl";

		if (direction === "previous") {
			if (isRTL) {
				goToNextPage();
			} else {
				goToPreviousPage();
			}
		} else if (direction === "next") {
			if (isRTL) {
				goToPreviousPage();
			} else {
				goToNextPage();
			}
		}
	}

	function handleToggleMenu() {
		showReaderMenu = !showReaderMenu;
	}

	function handleCloseMenu() {
		showReaderMenu = false;
	}

	function handleMenuPageChange(event) {
		goToPage(event.detail);
	}
</script>

<svelte:head>
	<title
		>{comic
			? comic.title ||
				comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, "")
			: "Loading..."} - Kottlib Reader</title
	>
</svelte:head>

<div class="reader-container" class:fullscreen={isFullscreen}>
	<PageViewer
		imageSrc={currentPageImage}
		secondPageSrc={secondPageImage}
		pageNumber={currentPage}
		{totalPages}
		bind:isLoading
		{nextPageSrc}
		{prevPageSrc}
		allPages={preloadedPages}
		{libraryId}
		{comicId}
		onPageChange={handleContinuousPageChange}
		onPrefetchPage={handlePrefetchPage}
		on:navigate={handleNavigate}
		on:toggleMenu={handleToggleMenu}
	/>

	{#if showControls || showSettings}
		<ReaderControls
			{currentPage}
			{totalPages}
			{isFullscreen}
			{showSettings}
			on:previous={handlePrevious}
			on:next={handleNext}
			on:pageChange={handlePageChange}
			on:toggleFullscreen={handleToggleFullscreen}
			on:toggleSettings={handleToggleSettings}
			on:exit={handleExit}
		/>
	{/if}

	<ReaderSettings show={showSettings} libraryId={libraryId} on:close={handleCloseSettings} />

	<ReaderMenu
		bind:show={showReaderMenu}
		{currentPage}
		{totalPages}
		chapters={[]}
		on:pageChange={handleMenuPageChange}
		on:close={handleCloseMenu}
	/>
</div>

<style>
	.reader-container {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: #1a1a1a;
		z-index: 100;
	}

	.reader-container.fullscreen {
		z-index: 9999;
	}

	:global(body:has(.reader-container)) {
		overflow: hidden;
	}
</style>
