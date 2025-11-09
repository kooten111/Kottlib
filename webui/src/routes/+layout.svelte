<script>
	import '../app.css';
	import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
	import { themeStore } from '$stores/theme';
	import { onMount } from 'svelte';

	// Initialize TanStack Query client
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 1000 * 60 * 5, // 5 minutes
				cacheTime: 1000 * 60 * 10, // 10 minutes
				refetchOnWindowFocus: false
			}
		}
	});

	// Apply theme class to html element
	onMount(() => {
		const unsubscribe = themeStore.subscribe((theme) => {
			if (theme === 'dark') {
				document.documentElement.classList.add('dark');
			} else {
				document.documentElement.classList.remove('dark');
			}
		});

		return unsubscribe;
	});
</script>

<QueryClientProvider client={queryClient}>
	<div class="min-h-screen bg-dark-bg text-dark-text">
		<slot />
	</div>
</QueryClientProvider>
