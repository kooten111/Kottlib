<script>
	import '../app.css';
	import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
	import { themeStore } from '$stores/theme';
	import { onMount } from 'svelte';

	// Initialize TanStack Query client with optimized cache settings
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 1000 * 60 * 15, // 15 minutes - increased for better performance
				gcTime: 1000 * 60 * 30, // 30 minutes (gcTime replaces cacheTime in newer versions)
				refetchOnWindowFocus: false,
				refetchOnReconnect: false, // Don't refetch on reconnect for better UX
				retry: 1, // Only retry failed requests once
				retryDelay: 1000 // Wait 1 second before retrying
			}
		}
	});

	// Apply theme class to html element and warm cache
	onMount(async () => {
		const unsubscribe = themeStore.subscribe((theme) => {
			if (theme === 'dark') {
				document.documentElement.classList.add('dark');
			} else {
				document.documentElement.classList.remove('dark');
			}
		});

		// Warm cache in the background after initial page load
		// This pre-loads data for subsequent visits
		if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
			requestIdleCallback(
				async () => {
					const { scheduleCacheWarming } = await import('$lib/utils/cacheWarmer');
					scheduleCacheWarming();
				},
				{ timeout: 5000 }
			);
		}

		return unsubscribe;
	});
</script>

<QueryClientProvider client={queryClient}>
	<div class="min-h-screen bg-dark-bg text-dark-text">
		<slot />
	</div>
</QueryClientProvider>
