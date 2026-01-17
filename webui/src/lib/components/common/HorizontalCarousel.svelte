<script>
	import { onMount, onDestroy } from "svelte";
	import { ChevronLeft, ChevronRight } from "lucide-svelte";

	export let itemWidth = 180; // Width of each item in pixels
	export let gap = 24; // Gap between items in pixels

	let container;
	let scrollContainer;
	let isDragging = false;
	let startX = 0;
	let scrollLeft = 0;
	let showLeftButton = false;
	let showRightButton = false;
	let scrollThrottleTimer = null;
	let resizeThrottleTimer = null;

	function updateButtonVisibility() {
		if (!scrollContainer) return;

		showLeftButton = scrollContainer.scrollLeft > 0;
		showRightButton =
			scrollContainer.scrollLeft <
			scrollContainer.scrollWidth - scrollContainer.clientWidth - 10;
	}

	// Throttled scroll handler for better performance (16ms = 60fps)
	function throttledUpdateButtonVisibility() {
		if (scrollThrottleTimer) return;

		scrollThrottleTimer = setTimeout(() => {
			updateButtonVisibility();
			scrollThrottleTimer = null;
		}, 16);
	}

	// Throttled resize handler (100ms debounce)
	function throttledResizeHandler() {
		if (resizeThrottleTimer) clearTimeout(resizeThrottleTimer);

		resizeThrottleTimer = setTimeout(() => {
			updateButtonVisibility();
		}, 100);
	}

	function scroll(direction) {
		if (!scrollContainer) return;

		const scrollAmount = (itemWidth + gap) * 3; // Scroll 3 items at a time
		const newScrollLeft =
			scrollContainer.scrollLeft +
			(direction === "left" ? -scrollAmount : scrollAmount);

		scrollContainer.scrollTo({
			left: newScrollLeft,
			behavior: "smooth",
		});
	}

	function handleMouseDown(e) {
		isDragging = true;
		startX = e.pageX - scrollContainer.offsetLeft;
		scrollLeft = scrollContainer.scrollLeft;
		scrollContainer.style.cursor = "grabbing";
	}

	function handleMouseMove(e) {
		if (!isDragging) return;
		e.preventDefault();

		const x = e.pageX - scrollContainer.offsetLeft;
		const walk = (x - startX) * 2; // Multiply by 2 for faster scrolling
		scrollContainer.scrollLeft = scrollLeft - walk;
	}

	function handleMouseUp() {
		isDragging = false;
		scrollContainer.style.cursor = "grab";
	}

	function handleMouseLeave() {
		isDragging = false;
		scrollContainer.style.cursor = "grab";
	}

	// Touch events for mobile
	let touchStartX = 0;
	let touchScrollLeft = 0;

	function handleTouchStart(e) {
		touchStartX = e.touches[0].pageX;
		touchScrollLeft = scrollContainer.scrollLeft;
	}

	function handleTouchMove(e) {
		const touchX = e.touches[0].pageX;
		const walk = (touchStartX - touchX) * 1.5;
		scrollContainer.scrollLeft = touchScrollLeft + walk;
	}

	onMount(() => {
		if (scrollContainer) {
			updateButtonVisibility();

			// Update button visibility on scroll with throttling for better performance
			scrollContainer.addEventListener(
				"scroll",
				throttledUpdateButtonVisibility,
				{ passive: true },
			);

			// Update on resize with debouncing
			window.addEventListener("resize", throttledResizeHandler);
		}
	});

	onDestroy(() => {
		// Clean up timers
		if (scrollThrottleTimer) clearTimeout(scrollThrottleTimer);
		if (resizeThrottleTimer) clearTimeout(resizeThrottleTimer);

		// Remove event listeners
		if (scrollContainer) {
			scrollContainer.removeEventListener(
				"scroll",
				throttledUpdateButtonVisibility,
			);
		}
		if (typeof window !== "undefined") {
			window.removeEventListener("resize", throttledResizeHandler);
		}
	});
</script>

<div class="carousel-wrapper" bind:this={container}>
	{#if showLeftButton}
		<button
			class="carousel-button carousel-button-left"
			on:click={() => scroll("left")}
		>
			<ChevronLeft class="w-6 h-6" />
		</button>
	{/if}

	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="carousel-container"
		bind:this={scrollContainer}
		on:mousedown={handleMouseDown}
		on:mousemove={handleMouseMove}
		on:mouseup={handleMouseUp}
		on:mouseleave={handleMouseLeave}
		on:touchstart={handleTouchStart}
		on:touchmove={handleTouchMove}
		style="--item-width: {itemWidth}px; --gap: {gap}px;"
		role="region"
		aria-label="Scrollable carousel"
	>
		<slot />
	</div>

	{#if showRightButton}
		<button
			class="carousel-button carousel-button-right"
			on:click={() => scroll("right")}
		>
			<ChevronRight class="w-6 h-6" />
		</button>
	{/if}
</div>

<style>
	.carousel-wrapper {
		position: relative;
		width: 100%;
	}

	.carousel-container {
		display: flex;
		gap: var(--gap);
		overflow-x: auto;
		overflow-y: hidden;
		scroll-behavior: smooth;
		cursor: grab;
		user-select: none;
		-webkit-overflow-scrolling: touch;
		scrollbar-width: none; /* Firefox */
		-ms-overflow-style: none; /* IE and Edge */
		padding: 0.5rem 0; /* Prevent shadow clipping */
	}

	.carousel-container::-webkit-scrollbar {
		display: none; /* Chrome, Safari, Opera */
	}

	.carousel-container:active {
		cursor: grabbing;
	}

	.carousel-button {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		z-index: 10;
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.8);
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 50%;
		color: white;
		cursor: pointer;
		transition: all 0.2s;
		backdrop-filter: blur(8px);
	}

	.carousel-button:hover {
		background: rgba(255, 103, 64, 0.9);
		border-color: var(--color-accent);
		transform: translateY(-50%) scale(1.1);
	}

	.carousel-button-left {
		left: -24px;
	}

	.carousel-button-right {
		right: -24px;
	}

	@media (max-width: 768px) {
		.carousel-button {
			width: 36px;
			height: 36px;
		}

		.carousel-button-left {
			left: 8px;
		}

		.carousel-button-right {
			right: 8px;
		}
	}
</style>
