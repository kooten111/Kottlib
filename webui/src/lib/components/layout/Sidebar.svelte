<script>
	export let open = true;

	import { Filter, X } from 'lucide-svelte';
</script>

<div class="relative">
	<!-- Toggle Button (Mobile) -->
	<button
		on:click={() => (open = !open)}
		class="lg:hidden fixed bottom-4 right-4 z-50 btn-primary rounded-full p-4 shadow-lg"
		aria-label="Toggle filters"
	>
		{#if open}
			<X class="w-6 h-6" />
		{:else}
			<Filter class="w-6 h-6" />
		{/if}
	</button>

	<!-- Sidebar -->
	<aside
		class="fixed lg:static inset-y-0 left-0 z-40 w-64 bg-dark-bg-secondary border-r border-gray-700 transform transition-transform duration-300 lg:transform-none"
		class:translate-x-0={open}
		class:-translate-x-full={!open}
	>
		<div class="h-full overflow-y-auto p-4">
			<slot />
		</div>
	</aside>

	<!-- Overlay for mobile -->
	{#if open}
		<div
			class="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
			on:click={() => (open = false)}
			on:keydown={(e) => e.key === 'Escape' && (open = false)}
			role="button"
			tabindex="0"
			aria-label="Close sidebar"
		/>
	{/if}
</div>
