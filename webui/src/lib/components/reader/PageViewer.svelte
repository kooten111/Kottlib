<script>
	import { readerSettings } from '$lib/stores/reader';
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let imageSrc = '';
	export let pageNumber = 1;
	export let totalPages = 1;
	export let isLoading = false;
	export let nextPageSrc = '';
	export let prevPageSrc = '';
	// Continuous scroll mode props
	export let allPages = new Map(); // Map<pageNumber, imageUrl>
	// svelte-ignore export_let_unused - Reserved for future use
	export let libraryId = null;
	// svelte-ignore export_let_unused - Reserved for future use
	export let comicId = null;
	export let secondPageSrc = ''; // Second page for double-page spread mode
	export let onPageChange = null; // Callback function for page changes
	export let onPrefetchPage = null; // Callback function to prefetch a page
	
	// Watch for changes to allPages Map to trigger reactivity
	$: allPagesSize = allPages.size;
	$: allPagesKeys = Array.from(allPages.keys());

	let container;
	let img;
	let containerWidth = 0;
	let containerHeight = 0;
	let imageLoaded = false;
	let imageError = false;
	let mouseZone = null; // 'left', 'center', 'right', or null
	let canPanImage = false;
	let isMousePanning = false;
	let hasMousePanned = false;
	let panStartX = 0;
	let panStartY = 0;
	let panStartPanX = 0;
	let panStartPanY = 0;
	let panX = 0;
	let panY = 0;
	let maxPanX = 0;
	let maxPanY = 0;

	// Continuous scroll mode state
	let continuousScrollContainer;
	let pageElements = {}; // Object<pageNumber, HTMLElement>
	let scrollTimeout;
	let isScrolling = false;
	let scrollListenerAdded = false;
	let intersectionObserver = null;
	const PREFETCH_AHEAD = 3; // Number of pages to prefetch ahead
	const PREFETCH_BEHIND = 1; // Number of pages to keep loaded behind

	// Touch/swipe state
	let touchStartX = 0;
	let touchStartY = 0;
	let touchCurrentX = 0;
	let touchCurrentY = 0;
	let isSwiping = false;
	let swipeOffset = 0;
	let isTransitioning = false;
	const SWIPE_THRESHOLD = 0.3; // 30% of screen width
	const MIN_SWIPE_DISTANCE = 50; // minimum pixels to consider it a swipe
	const MIN_SWIPE_VISUAL_FEEDBACK = 10; // minimum pixels to show adjacent page
	const TRANSITION_DURATION_MS = 300; // duration of swipe animations in milliseconds

	$: fitClass = getFitClass($readerSettings.fitMode);
	$: isContinuousMode = $readerSettings.readingMode === 'continuous';
	$: isDoubleMode = $readerSettings.readingMode === 'double';
	$: isRTL = $readerSettings.readingDirection === 'rtl';

	function getFitClass(fitMode) {
		switch (fitMode) {
			case 'fit-width':
				return 'fit-width';
			case 'fit-height':
				return 'fit-height';
			case 'original':
				return 'original';
			default:
				return 'fit-width';
		}
	}

	function handleImageLoad() {
		imageLoaded = true;
		isLoading = false;
		imageError = false;
		requestAnimationFrame(updatePanAvailability);
	}

	function handleImageError() {
		imageError = true;
		isLoading = false;
		imageLoaded = false;
	}

	let justLoadedPage = false;
	let secondImageLoaded = false;

	// Reset state when image source changes
	$: if (imageSrc) {
		imageLoaded = false;
		imageError = false;
		isLoading = true;
		canPanImage = false;
		panX = 0;
		panY = 0;
		justLoadedPage = true;
	}

	// Reset second page state when second page source changes
	$: if (secondPageSrc !== undefined) {
		secondImageLoaded = false;
	}

	function updatePanAvailability() {
		if (!container || !img || isContinuousMode || isDoubleMode || !imageLoaded) {
			canPanImage = false;
			maxPanX = 0;
			maxPanY = 0;
			panX = 0;
			panY = 0;
			return;
		}

		// Use offsetWidth/Height which report the element's layout size
		// even when clipped by overflow:hidden on the parent
		const overflowX = img.offsetWidth - container.clientWidth;
		const overflowY = img.offsetHeight - container.clientHeight;

		maxPanX = Math.max(0, overflowX);
		maxPanY = Math.max(0, overflowY);
		canPanImage = maxPanX > 1 || maxPanY > 1;

		if (!canPanImage) {
			panX = 0;
			panY = 0;
			justLoadedPage = false;
		} else {
			clampPan();
			// On fresh page load, align to top for fit-width and original modes
			if (justLoadedPage && maxPanY > 1) {
				const fm = $readerSettings.fitMode;
				if (fm === 'fit-width' || fm === 'original') {
					panY = maxPanY / 2;
				}
			}
			justLoadedPage = false;
		}
	}

	function clampPan() {
		panX = Math.max(-maxPanX / 2, Math.min(maxPanX / 2, panX));
		panY = Math.max(-maxPanY / 2, Math.min(maxPanY / 2, panY));
	}

	// Handle click navigation with three zones
	function handlePageClick(e) {
		if (hasMousePanned) {
			e.preventDefault();
			return;
		}

		const { clientX } = e;
		const { left, width } = container.getBoundingClientRect();
		const clickPosition = (clientX - left) / width;

		const leftZone = 0.33;
		const rightZone = 0.67;

		if (clickPosition < leftZone) {
			// Left third: Previous page (respects RTL)
			dispatch('navigate', { direction: 'previous' });
		} else if (clickPosition > rightZone) {
			// Right third: Next page (respects RTL)
			dispatch('navigate', { direction: 'next' });
		} else {
			// Middle third: Toggle menu
			dispatch('toggleMenu');
		}
	}

	// Update mouse zone for cursor styling
	function handleMouseMove(e) {
		if (canPanImage && isMousePanning) {
			const deltaX = e.clientX - panStartX;
			const deltaY = e.clientY - panStartY;

			if (!hasMousePanned && (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2)) {
				hasMousePanned = true;
			}

			panX = panStartPanX + deltaX;
			panY = panStartPanY + deltaY;
			clampPan();
			return;
		}

		if (canPanImage) {
			mouseZone = null;
			return;
		}

		const { clientX } = e;
		const { left, width } = container.getBoundingClientRect();
		const mousePosition = (clientX - left) / width;

		const leftZone = 0.33;
		const rightZone = 0.67;

		if (mousePosition < leftZone) {
			mouseZone = 'left';
		} else if (mousePosition > rightZone) {
			mouseZone = 'right';
		} else {
			mouseZone = 'center';
		}
	}

	function handleMouseLeave() {
		if (isMousePanning) {
			handleMouseUp();
		}
		mouseZone = null;
	}

	function handleMouseDown(e) {
		if (!canPanImage || e.button !== 0) return;

		isMousePanning = true;
		hasMousePanned = false;
		panStartX = e.clientX;
		panStartY = e.clientY;
		panStartPanX = panX;
		panStartPanY = panY;
	}

	function handleMouseUp() {
		if (!isMousePanning) return;

		isMousePanning = false;
		setTimeout(() => {
			hasMousePanned = false;
		}, 0);
	}

	// Get effective container width with fallback
	function getEffectiveWidth() {
		return containerWidth || container?.offsetWidth || window.innerWidth;
	}

	// Touch event handlers
	function handleWheel(e) {
		if (!canPanImage) return;

		e.preventDefault();
		panX -= e.deltaX;
		panY -= e.deltaY;
		clampPan();
	}

	function handleTouchStart(e) {
		if (canPanImage) {
			if (e.touches.length === 1) {
				isMousePanning = true;
				hasMousePanned = false;
				panStartX = e.touches[0].clientX;
				panStartY = e.touches[0].clientY;
				panStartPanX = panX;
				panStartPanY = panY;
			}
			return;
		}

		// Only handle single touch
		if (e.touches.length !== 1) return;

		touchStartX = e.touches[0].clientX;
		touchStartY = e.touches[0].clientY;
		touchCurrentX = touchStartX;
		touchCurrentY = touchStartY;
		isSwiping = false;
		swipeOffset = 0;
	}

	function handleTouchMove(e) {
		if (canPanImage && isMousePanning) {
			if (e.touches.length !== 1) return;
			const deltaX = e.touches[0].clientX - panStartX;
			const deltaY = e.touches[0].clientY - panStartY;

			if (!hasMousePanned && (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2)) {
				hasMousePanned = true;
			}

			panX = panStartPanX + deltaX;
			panY = panStartPanY + deltaY;
			clampPan();
			e.preventDefault();
			return;
		}
		if (canPanImage) return;

		if (e.touches.length !== 1) return;

		touchCurrentX = e.touches[0].clientX;
		touchCurrentY = e.touches[0].clientY;

		const deltaX = touchCurrentX - touchStartX;
		const deltaY = touchCurrentY - touchStartY;

		// Check if this is a horizontal swipe (more horizontal than vertical)
		if (!isSwiping && Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
			isSwiping = true;
			// Prevent default to stop page scrolling
			e.preventDefault();
		}

		if (isSwiping) {
			e.preventDefault();
			swipeOffset = deltaX;
		}
	}

	function handleTouchEnd(e) {
		if (canPanImage) {
			if (isMousePanning) {
				isMousePanning = false;
				setTimeout(() => { hasMousePanned = false; }, 0);
			}
			return;
		}

		if (!isSwiping) {
			// If no swipe was detected, this is a tap - handle as click
			if (e.changedTouches.length === 1) {
				const touch = e.changedTouches[0];
				handlePageClick({ clientX: touch.clientX });
			}
			return;
		}

		const deltaX = touchCurrentX - touchStartX;
		const effectiveWidth = getEffectiveWidth();
		const swipeRatio = Math.abs(deltaX) / effectiveWidth;
		const isRTL = $readerSettings.readingDirection === 'rtl';

		// Determine if swipe threshold was met
		if (swipeRatio >= SWIPE_THRESHOLD && Math.abs(deltaX) >= MIN_SWIPE_DISTANCE) {
			// Complete the swipe navigation
			isTransitioning = true;
			
			// In LTR: swipe right = previous (deltaX > 0), swipe left = next (deltaX < 0)
			// In RTL: swipe right = next (deltaX > 0), swipe left = previous (deltaX < 0)
			const direction = isRTL 
				? (deltaX > 0 ? 'next' : 'previous')
				: (deltaX > 0 ? 'previous' : 'next');

			// Animate to full width
			swipeOffset = deltaX > 0 ? effectiveWidth : -effectiveWidth;

			// Wait for animation, then dispatch navigation
			setTimeout(() => {
				dispatch('navigate', { direction });
				resetSwipeState();
			}, TRANSITION_DURATION_MS);
		} else {
			// Snap back - swipe didn't meet threshold
			isTransitioning = true;
			swipeOffset = 0;
			setTimeout(() => {
				resetSwipeState();
			}, TRANSITION_DURATION_MS);
		}
	}

	function resetSwipeState() {
		isSwiping = false;
		isTransitioning = false;
		swipeOffset = 0;
		touchStartX = 0;
		touchStartY = 0;
		touchCurrentX = 0;
		touchCurrentY = 0;
	}

	// Get the adjacent page source based on swipe direction
	// In LTR: swipe right (deltaX > 0) = go to previous page
	// In RTL: swipe right (deltaX > 0) = go to next page
	$: adjacentPageSrc = (() => {
		const isRTL = $readerSettings.readingDirection === 'rtl';
		if (isRTL) {
			return swipeOffset > 0 ? nextPageSrc : prevPageSrc;
		} else {
			return swipeOffset > 0 ? prevPageSrc : nextPageSrc;
		}
	})();
	$: showAdjacentPage = (isSwiping || isTransitioning) && adjacentPageSrc && Math.abs(swipeOffset) > MIN_SWIPE_VISUAL_FEEDBACK;

	// Calculate transform for adjacent page
	$: adjacentPageTransform = (() => {
		const effectiveWidth = getEffectiveWidth();
		const offset = swipeOffset > 0 
			? swipeOffset - effectiveWidth 
			: swipeOffset + effectiveWidth;
		return `translateX(${offset}px)`;
	})();

	$: adjacentPagePosition = swipeOffset > 0 ? 'left: 0;' : 'right: 0;';

	// Continuous scroll mode functions
	function handleContinuousScroll() {
		if (!continuousScrollContainer || !isContinuousMode) return;

		// Mark that user is manually scrolling
		isUserScrolling = true;
		isScrolling = true;
		
		if (scrollTimeout) {
			clearTimeout(scrollTimeout);
		}
		if (userScrollTimeout) {
			clearTimeout(userScrollTimeout);
		}

		// Debounce page change detection - update during scroll but not too frequently
		scrollTimeout = setTimeout(() => {
			updateCurrentPageFromScroll();
			isScrolling = false;
		}, 200); // Update every 200ms while scrolling

		// Reset user scrolling flag after scroll stops
		userScrollTimeout = setTimeout(() => {
			isUserScrolling = false;
		}, 300);
	}

	function updateCurrentPageFromScroll() {
		if (!continuousScrollContainer || !isContinuousMode) return;

		const scrollTop = continuousScrollContainer.scrollTop;
		const containerHeight = continuousScrollContainer.clientHeight;
		const viewportCenter = scrollTop + containerHeight / 2;

		// Find which page is currently in the center of the viewport
		let currentPage = 1;
		let minDistance = Infinity;

		// Get page order based on reading direction
		const pageOrder = isRTL 
			? Array.from({ length: totalPages }, (_, i) => totalPages - i)
			: Array.from({ length: totalPages }, (_, i) => i + 1);

		for (const pageNum of pageOrder) {
			const element = pageElements[pageNum];
			if (!element) continue;

			const rect = element.getBoundingClientRect();
			const containerRect = continuousScrollContainer.getBoundingClientRect();
			const elementTop = rect.top - containerRect.top + scrollTop;
			const elementBottom = elementTop + rect.height;
			const elementCenter = (elementTop + elementBottom) / 2;

			const distance = Math.abs(viewportCenter - elementCenter);
			if (distance < minDistance) {
				minDistance = distance;
				currentPage = pageNum;
			}
		}

		// Only update if page actually changed (not just small scroll movements)
		if (currentPage !== pageNumber && onPageChange) {
			lastScrollTrackedPage = currentPage; // Track that this came from scroll
			onPageChange(currentPage);
		}
	}

	function scrollToPage(pageNum) {
		if (!continuousScrollContainer || !isContinuousMode) return;

		const element = pageElements[pageNum];
		if (!element) {
			// If element not ready, try again after a short delay
			setTimeout(() => scrollToPage(pageNum), 100);
			return;
		}

		const containerRect = continuousScrollContainer.getBoundingClientRect();
		const elementRect = element.getBoundingClientRect();
		const scrollTop = continuousScrollContainer.scrollTop;
		const elementTop = elementRect.top - containerRect.top + scrollTop;

		// Scroll to center the page in the viewport
		const targetScroll = elementTop - (containerRect.height / 2) + (elementRect.height / 2);
		
		// Use instant scroll (no animation) to avoid interfering with user scrolling
		continuousScrollContainer.scrollTo({
			top: Math.max(0, targetScroll),
			behavior: 'auto' // Instant scroll, no animation
		});
	}


	onMount(() => {
		// Observe container resize
		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				containerWidth = entry.contentRect.width;
				containerHeight = entry.contentRect.height;
				requestAnimationFrame(updatePanAvailability);
			}
		});

		if (container) {
			resizeObserver.observe(container);
		}

		return () => {
			resizeObserver.disconnect();
			if (continuousScrollContainer && scrollListenerAdded) {
				continuousScrollContainer.removeEventListener('scroll', handleContinuousScroll);
				scrollListenerAdded = false;
			}
			if (intersectionObserver) {
				intersectionObserver.disconnect();
				intersectionObserver = null;
			}
			if (scrollTimeout) {
				clearTimeout(scrollTimeout);
			}
			if (userScrollTimeout) {
				clearTimeout(userScrollTimeout);
			}
		};
	});

	// Setup intersection observer for prefetching
	function setupIntersectionObserver() {
		if (!isContinuousMode || !continuousScrollContainer || intersectionObserver) return;

		// Create intersection observer to detect pages coming into view
		intersectionObserver = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					const pageNum = parseInt(entry.target.dataset.page);
					if (!pageNum) continue;

					// If page is intersecting (visible or near viewport), prefetch nearby pages
					if (entry.isIntersecting || entry.intersectionRatio > 0) {
						prefetchNearbyPages(pageNum);
					}
				}
			},
			{
				root: continuousScrollContainer,
				rootMargin: '200% 0px', // Prefetch when page is 2 viewport heights away
				threshold: [0, 0.1, 0.5, 1.0]
			}
		);

		// Observe all page elements
		Object.values(pageElements).forEach((element) => {
			if (element) {
				intersectionObserver.observe(element);
			}
		});
	}

	// Prefetch pages near the given page number
	function prefetchNearbyPages(currentPage) {
		if (!onPrefetchPage || !totalPages) return;

		const isRTL = $readerSettings.readingDirection === 'rtl';
		const prefetchCount = $readerSettings.preloadPages || PREFETCH_AHEAD;

		// Determine which pages to prefetch based on reading direction
		for (let i = 1; i <= prefetchCount; i++) {
			// Pages ahead (in reading direction)
			const aheadPage = isRTL ? currentPage - i : currentPage + i;
			if (aheadPage >= 1 && aheadPage <= totalPages && !allPages.has(aheadPage)) {
				onPrefetchPage(aheadPage);
			}

			// Pages behind (in reading direction) - keep a few loaded
			if (i <= PREFETCH_BEHIND) {
				const behindPage = isRTL ? currentPage + i : currentPage - i;
				if (behindPage >= 1 && behindPage <= totalPages && !allPages.has(behindPage)) {
					onPrefetchPage(behindPage);
				}
			}
		}
	}

	// Watch for page elements to setup intersection observer
	$: if (isContinuousMode && Object.keys(pageElements).length > 0 && continuousScrollContainer) {
		// Setup observer after a short delay to ensure DOM is ready
		setTimeout(() => {
			setupIntersectionObserver();
		}, 100);
	}

	// Watch for continuous mode activation to setup scroll listener and initial scroll
	$: if (isContinuousMode && continuousScrollContainer && !scrollListenerAdded) {
		// Setup scroll listener with passive option for better performance
		continuousScrollContainer.addEventListener('scroll', handleContinuousScroll, { passive: true });
		scrollListenerAdded = true;
	}

	// Track if user is manually scrolling to prevent auto-scroll interference
	let isUserScrolling = false;
	let userScrollTimeout;
	
	// Flag to prevent auto-scroll when page number changes from scroll tracking
	let lastScrollTrackedPage = 0;

	// Prefetch pages when scroll position changes
	$: if (isContinuousMode && pageNumber && onPrefetchPage) {
		prefetchNearbyPages(pageNumber);
	}

	$: if (!isContinuousMode && container && imageLoaded && imageSrc && $readerSettings.fitMode) {
		// Reset pan when fit mode changes
		panX = 0;
		panY = 0;
		requestAnimationFrame(updatePanAvailability);
	}

	$: if (canPanImage && mouseZone !== null) {
		mouseZone = null;
	}
	
	// Only scroll to page if it's NOT from scroll tracking (i.e., from keyboard navigation)
	// We detect this by checking if the page number changed but we didn't just track it from scroll
	$: if (isContinuousMode && pageNumber && continuousScrollContainer && pageNumber !== lastScrollTrackedPage && !isUserScrolling) {
		// This is likely from keyboard navigation, so scroll to it
		requestAnimationFrame(() => {
			setTimeout(() => {
				scrollToPage(pageNumber);
				lastScrollTrackedPage = 0; // Reset after scrolling
			}, 50);
		});
	}
</script>

{#if isContinuousMode}
	<!-- Continuous Scroll Mode -->
	<div
		bind:this={continuousScrollContainer}
		class="continuous-scroll-container"
		style="background-color: {$readerSettings.backgroundColor}"
	>
		<div class="continuous-pages">
			{#each (isRTL 
				? Array.from({ length: totalPages }, (_, i) => totalPages - i)
				: Array.from({ length: totalPages }, (_, i) => i + 1)
			) as pageNum}
				{@const pageUrl = allPages.get(pageNum)}
				<div
					bind:this={pageElements[pageNum]}
					class="continuous-page"
					data-page={pageNum}
				>
					{#if pageUrl}
						<img
							src={pageUrl}
							alt="Page {pageNum}"
							class="page-image {fitClass}"
							loading="lazy"
							on:load={() => {
								// Update pageElements map when image loads
								if (continuousScrollContainer) {
									updateCurrentPageFromScroll();
								}
								// Setup intersection observer if not already done
								if (intersectionObserver && pageElements[pageNum]) {
									intersectionObserver.observe(pageElements[pageNum]);
								}
							}}
						/>
					{:else}
						<div class="loading-placeholder">
							<div class="spinner"></div>
							<p>Loading page {pageNum}...</p>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
{:else}
	<!-- Single/Double Page Mode -->
<div
	bind:this={container}
	class="page-viewer zone-{mouseZone || 'none'}"
	class:pannable={canPanImage}
	style="background-color: {$readerSettings.backgroundColor}"
	on:click={handlePageClick}
	on:keydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			dispatch('toggleMenu');
		}
	}}
	on:mousemove={handleMouseMove}
	on:mousedown={handleMouseDown}
	on:mouseup={handleMouseUp}
	on:mouseleave={handleMouseLeave}
	on:wheel|nonpassive={handleWheel}
	on:touchstart|passive={handleTouchStart}
	on:touchmove|nonpassive={handleTouchMove}
	on:touchend={handleTouchEnd}
	role="button"
	tabindex="0"
>
	<!-- Main page container with transform for swipe effect -->
	<div 
		class="page-container" 
		class:transitioning={isTransitioning}
		style="transform: translateX({swipeOffset}px)"
	>
		{#if isLoading}
			<div class="loading-spinner">
				<div class="spinner"></div>
				<p class="text-gray-400 mt-4">Loading page {pageNumber} of {totalPages}...</p>
			</div>
		{/if}

		{#if imageError}
			<div class="error-message">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="64"
					height="64"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="text-red-500"
				>
					<circle cx="12" cy="12" r="10" />
					<line x1="12" y1="8" x2="12" y2="12" />
					<line x1="12" y1="16" x2="12.01" y2="16" />
				</svg>
				<p class="text-red-400 mt-4">Failed to load page {pageNumber}</p>
			</div>
		{/if}

		{#if isDoubleMode}
			<!-- Double Page Spread -->
			<div class="double-page-spread" class:rtl={isRTL}>
				<!-- In RTL, page order is visually reversed via flex-direction in CSS -->
				<div class="double-page-slot">
					{#if imageSrc}
						<img
							src={imageSrc}
							alt="Page {pageNumber}"
							class="double-page-image"
							class:hidden={!imageLoaded}
							on:load={() => { imageLoaded = true; isLoading = false; }}
							on:error={handleImageError}
						/>
					{/if}
				</div>
				<div class="double-page-slot">
					{#if secondPageSrc}
						<img
							src={secondPageSrc}
							alt="Page {pageNumber + 1}"
							class="double-page-image"
							class:hidden={!secondImageLoaded}
							on:load={() => { secondImageLoaded = true; }}
						/>
					{/if}
				</div>
			</div>
		{:else}
			{#if imageSrc}
				<img
					bind:this={img}
					src={imageSrc}
					alt="Page {pageNumber}"
					class="page-image {fitClass}"
					class:hidden={!imageLoaded}
					style={canPanImage ? `transform: translate(${panX}px, ${panY}px)` : ''}
					on:load={handleImageLoad}
					on:error={handleImageError}
				/>
			{/if}
		{/if}
	</div>

	<!-- Adjacent page for swipe transition -->
	{#if showAdjacentPage}
		<div
			class="adjacent-page"
			class:transitioning={isTransitioning}
			style="transform: {adjacentPageTransform}; {adjacentPagePosition}"
		>
			{#if adjacentPageSrc}
				<img
					src={adjacentPageSrc}
					alt="Adjacent page"
					class="page-image {fitClass}"
				/>
			{:else}
				<div class="debug-indicator">No adjacent page loaded</div>
			{/if}
		</div>
	{/if}

	<!-- Debug info -->
	{#if isSwiping}
		<div class="debug-info">
			<div>Swiping: {swipeOffset}px</div>
			<div>Adjacent src: {adjacentPageSrc ? 'loaded' : 'NOT loaded'}</div>
			<div>Show adjacent: {showAdjacentPage ? 'yes' : 'no'}</div>
			<div>Next: {nextPageSrc ? 'loaded' : 'empty'}</div>
			<div>Prev: {prevPageSrc ? 'loaded' : 'empty'}</div>
		</div>
	{/if}
</div>
{/if}

<style>
	.page-viewer {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		position: relative;
		cursor: default;
		touch-action: pan-y; /* Allow vertical scrolling but not horizontal */
	}

	.page-viewer.pannable {
		cursor: grab;
	}

	.page-viewer.pannable:active {
		cursor: grabbing;
	}

	/* Cursor styles for navigation zones */
	.page-viewer.zone-left {
		cursor: w-resize;
	}

	.page-viewer.zone-right {
		cursor: e-resize;
	}

	.page-viewer.zone-center {
		cursor: pointer;
	}

	.page-container {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		position: relative;
		will-change: transform;
	}

	.page-container.transitioning {
		/* Duration matches TRANSITION_DURATION_MS constant (300ms) */
		/* Smooth swipe animations for single/double page modes */
		transition: transform 0.3s ease-out;
	}

	.adjacent-page {
		position: absolute;
		top: 0;
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		will-change: transform;
		pointer-events: none;
	}

	.adjacent-page.transitioning {
		/* Duration matches TRANSITION_DURATION_MS constant (300ms) */
		/* Smooth swipe animations for single/double page modes */
		transition: transform 0.3s ease-out;
	}

	.page-image {
		display: block;
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
		user-select: none;
		-webkit-user-drag: none;
	}

	.page-image.fit-width {
		width: 100%;
		height: auto;
		max-height: none;
	}

	.page-image.fit-height {
		width: auto;
		height: 100%;
		max-width: none;
	}

	.page-image.original {
		max-width: none;
		max-height: none;
		width: auto;
		height: auto;
	}

	.loading-spinner {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	.spinner {
		width: 64px;
		height: 64px;
		border: 4px solid rgba(255, 255, 255, 0.1);
		border-top-color: #ff6740;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.error-message {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	.hidden {
		display: none;
	}

	.debug-info {
		position: fixed;
		top: 10px;
		left: 10px;
		background: rgba(0, 0, 0, 0.8);
		color: white;
		padding: 10px;
		font-family: monospace;
		font-size: 12px;
		z-index: 1000;
		border-radius: 4px;
	}

	.debug-indicator {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		color: red;
		font-size: 24px;
		background: rgba(255, 0, 0, 0.1);
	}

	/* Continuous Scroll Mode Styles */
	.continuous-scroll-container {
		width: 100%;
		height: 100%;
		overflow-y: auto;
		overflow-x: hidden;
		position: relative;
		/* No scroll animations in continuous mode - instant scrolling only */
		scroll-behavior: auto;
		-webkit-overflow-scrolling: touch;
		overscroll-behavior: contain;
		will-change: scroll-position;
	}

	.continuous-pages {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0;
		padding: 0;
		width: 100%;
	}

	.continuous-page {
		width: 100%;
		display: flex;
		justify-content: center;
		align-items: flex-start;
		padding: 0;
		margin: 0;
	}

	.continuous-page .page-image {
		display: block;
		width: 100%;
		height: auto;
		object-fit: contain;
		user-select: none;
		-webkit-user-drag: none;
		margin: 0;
		padding: 0;
	}

	.continuous-page .page-image.fit-width {
		width: 100%;
		height: auto;
		max-height: none;
	}

	.continuous-page .page-image.fit-height {
		width: auto;
		max-width: 100%;
		height: auto;
	}

	.continuous-page .page-image.original {
		max-width: 100%;
		width: auto;
		height: auto;
	}

	.loading-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 50vh;
		width: 100%;
		color: var(--color-text-secondary);
		padding: 2rem;
	}

	.loading-placeholder p {
		margin-top: 1rem;
		font-size: 0.875rem;
	}

	/* ── Double-page spread ── */
	.double-page-spread {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		gap: 0;
	}

	/* In RTL mode the right page (lower page number) comes first visually */
	.double-page-spread.rtl {
		flex-direction: row-reverse;
	}

	.double-page-slot {
		flex: 1 1 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		min-width: 0; /* allow flex shrink below content size */
		overflow: hidden;
	}

	.double-page-image {
		max-width: 100%;
		max-height: 100%;
		width: auto;
		height: 100%;
		object-fit: contain;
		display: block;
		user-select: none;
		-webkit-user-drag: none;
	}

	.double-page-image.hidden {
		visibility: hidden;
	}
</style>
