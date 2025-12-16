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

	let container;
	let img;
	let containerWidth = 0;
	let containerHeight = 0;
	let imageLoaded = false;
	let imageError = false;
	let mouseZone = null; // 'left', 'center', 'right', or null

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
	}

	function handleImageError() {
		imageError = true;
		isLoading = false;
		imageLoaded = false;
	}

	// Reset state when image source changes
	$: if (imageSrc) {
		imageLoaded = false;
		imageError = false;
		isLoading = true;
	}

	// Handle click navigation with three zones
	function handlePageClick(e) {
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
		mouseZone = null;
	}

	// Touch event handlers
	function handleTouchStart(e) {
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
		if (!isSwiping) {
			// If no swipe was detected, this is a tap - handle as click
			if (e.changedTouches.length === 1) {
				const touch = e.changedTouches[0];
				handlePageClick({ clientX: touch.clientX });
			}
			return;
		}

		const deltaX = touchCurrentX - touchStartX;
		const effectiveWidth = containerWidth || container?.offsetWidth || window.innerWidth;
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
	$: showAdjacentPage = isSwiping && adjacentPageSrc && Math.abs(swipeOffset) > MIN_SWIPE_VISUAL_FEEDBACK;

	// Calculate transform for adjacent page
	$: adjacentPageTransform = (() => {
		const effectiveWidth = containerWidth || window.innerWidth;
		const offset = swipeOffset > 0 
			? swipeOffset - effectiveWidth 
			: swipeOffset + effectiveWidth;
		return `translateX(${offset}px)`;
	})();

	$: adjacentPagePosition = swipeOffset > 0 ? 'left: 0;' : 'right: 0;';

	onMount(() => {
		// Observe container resize
		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				containerWidth = entry.contentRect.width;
				containerHeight = entry.contentRect.height;
			}
		});

		if (container) {
			resizeObserver.observe(container);
		}

		return () => {
			resizeObserver.disconnect();
		};
	});
</script>

<div
	bind:this={container}
	class="page-viewer zone-{mouseZone || 'none'}"
	style="background-color: {$readerSettings.backgroundColor}"
	on:click={handlePageClick}
	on:mousemove={handleMouseMove}
	on:mouseleave={handleMouseLeave}
	on:touchstart={handleTouchStart}
	on:touchmove={handleTouchMove}
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
				<div class="spinner" />
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

		{#if imageSrc}
			<img
				bind:this={img}
				src={imageSrc}
				alt="Page {pageNumber}"
				class="page-image {fitClass}"
				class:hidden={!imageLoaded}
				on:load={handleImageLoad}
				on:error={handleImageError}
			/>
		{/if}
	</div>

	<!-- Adjacent page for swipe transition -->
	{#if showAdjacentPage}
		<div 
			class="adjacent-page" 
			class:transitioning={isTransitioning}
			style="transform: {adjacentPageTransform}; {adjacentPagePosition}"
		>
			<img
				src={adjacentPageSrc}
				alt="Adjacent page"
				class="page-image {fitClass}"
			/>
		</div>
	{/if}
</div>

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
</style>
