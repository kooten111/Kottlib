<script>
	import { ChevronRight } from 'lucide-svelte';

	export let items = []; // Array of { label, href }
</script>

<nav aria-label="Breadcrumb" class="flex items-center space-x-2 text-sm">
	{#each items as item, i}
		{#if i > 0}
			<ChevronRight class="w-4 h-4 text-dark-text-secondary" />
		{/if}

		{#if i === items.length - 1}
			<span class="text-dark-text font-medium">
				{item.label}
			</span>
		{:else}
			<a
				href={item.href}
				class="text-dark-text-secondary hover:text-dark-text transition-colors"
			>
				{item.label}
			</a>
		{/if}
	{/each}
</nav>
