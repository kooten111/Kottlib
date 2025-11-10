<script>
	import { readerSettings } from '$lib/stores/reader';
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let imageSrc = '';
	export let pageNumber = 1;
	export let totalPages = 1;
	export let isLoading = false;

	let container;
	let img;
	let containerWidth = 0;
	let containerHeight = 0;
	let imageLoaded = false;
	let imageError = false;
	let mouseZone = null; // 'left', 'center', 'right', or null

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
	role="button"
	tabindex="0"
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

<style>
	.page-viewer {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: auto;
		position: relative;
		cursor: default;
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
