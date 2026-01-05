<script>
	import { createEventDispatcher, onMount, onDestroy, tick } from "svelte";

	const dispatch = createEventDispatcher();

	export let threshold = 800; // Increased distance from bottom to trigger load earlier
	export let hasMore = true;
	export let isLoading = false;

	let container;
	let observer;
	let sentinelElement;

	onMount(() => {
		// Create intersection observer for the sentinel
		observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];

				// Add debounce check - only trigger if not already loading and hasMore is true
				if (entry.isIntersecting && hasMore && !isLoading) {
					// Slight delay to prevent double-triggering
					setTimeout(() => {
						if (hasMore && !isLoading) {
							dispatch("loadMore");
						}
					}, 50);
				}
			},
			{
				rootMargin: `${threshold}px`,
				threshold: 0.1, // Trigger when 10% visible
			},
		);
	});

	// Reactively observe the sentinel whenever it changes or hasMore changes
	$: if (observer && container && hasMore) {
		tick().then(() => {
			const sentinel = container.querySelector(
				".infinite-scroll-sentinel",
			);

			if (sentinel && sentinel !== sentinelElement) {
				// Disconnect previous observation
				if (sentinelElement) {
					observer.unobserve(sentinelElement);
				}
				// Observe new sentinel
				observer.observe(sentinel);
				sentinelElement = sentinel;
			} else if (!sentinel && sentinelElement) {
				// Sentinel was removed, clean up
				observer.unobserve(sentinelElement);
				sentinelElement = null;
			}
		});
	}

	// Clean up when hasMore becomes false
	$: if (!hasMore && sentinelElement && observer) {
		observer.unobserve(sentinelElement);
		sentinelElement = null;
	}

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
		}
	});
</script>

<div bind:this={container} class="infinite-scroll-container">
	<slot />

	{#if hasMore}
		<div class="infinite-scroll-sentinel">
			{#if isLoading}
				<div class="loading-spinner">
					<div class="spinner" />
					<p class="loading-text">Loading more...</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.infinite-scroll-container {
		width: 100%;
	}

	.infinite-scroll-sentinel {
		width: 100%;
		min-height: 40px;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem 0;
	}

	.loading-spinner {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.loading-text {
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		margin: 0;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
