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
	let preloadedPages = new Map();
	let showReaderMenu = false;

	// Get adjacent page sources for swipe transitions
	$: nextPageSrc = getAdjacentPageSrc("next");
	$: prevPageSrc = getAdjacentPageSrc("previous");

	function getAdjacentPageSrc(direction) {
		const isRTL = $readerSettings.readingDirection === "rtl";
		let targetPage;

		if (direction === "next") {
			targetPage = isRTL ? currentPage - 1 : currentPage + 1;
		} else {
			targetPage = isRTL ? currentPage + 1 : currentPage - 1;
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

			// Setup keyboard shortcuts
			if (typeof document !== "undefined") {
				document.addEventListener("keydown", handleKeyPress);
				document.addEventListener("mousemove", handleMouseMove);
			}
		} catch (error) {
			console.error("Failed to load comic:", error);
		}
	});

	onDestroy(() => {
		if (typeof document !== "undefined") {
			document.removeEventListener("keydown", handleKeyPress);
			document.removeEventListener("mousemove", handleMouseMove);
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

	// Save reading progress (debounced)
	let progressTimeout;
	function saveProgress(pageNum) {
		if (progressTimeout) {
			clearTimeout(progressTimeout);
		}
		progressTimeout = setTimeout(async () => {
			try {
				await updateReadingProgress(libraryId, comicId, pageNum);
			} catch (error) {
				console.error("Failed to save progress:", error);
			}
		}, 1000);
	}

	// Navigate to previous page
	function goToPreviousPage() {
		const isRTL = $readerSettings.readingDirection === "rtl";
		const newPage = isRTL ? currentPage + 1 : currentPage - 1;
		if (newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			loadPage(currentPage);
		}
	}

	// Navigate to next page
	function goToNextPage() {
		const isRTL = $readerSettings.readingDirection === "rtl";
		const newPage = isRTL ? currentPage - 1 : currentPage + 1;
		if (newPage >= 1 && newPage <= totalPages) {
			currentPage = newPage;
			loadPage(currentPage);
		}
	}

	// Jump to specific page
	function goToPage(pageNum) {
		if (pageNum >= 1 && pageNum <= totalPages && pageNum !== currentPage) {
			currentPage = pageNum;
			loadPage(currentPage);
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
		pageNumber={currentPage}
		{totalPages}
		bind:isLoading
		{nextPageSrc}
		{prevPageSrc}
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

	<ReaderSettings show={showSettings} on:close={handleCloseSettings} />

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
