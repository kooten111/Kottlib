<script>
	import "../app.css";
	import { themeStore } from "$stores/theme";
	import { onMount } from "svelte";

	// Apply theme and warm cache
	onMount(async () => {
		// Initialize theme application
		themeStore.init();

		// Warm cache in the background after initial page load
		// This pre-loads data for subsequent visits
		if (typeof window !== "undefined" && "requestIdleCallback" in window) {
			requestIdleCallback(
				async () => {
					const { scheduleCacheWarming } = await import(
						"$lib/utils/cacheWarmer"
					);
					scheduleCacheWarming();
				},
				{ timeout: 5000 },
			);
		}
	});
</script>

<div class="min-h-screen bg-dark-bg text-dark-text">
	<slot />
</div>
