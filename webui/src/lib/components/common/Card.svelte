<script>
	export let padding = true;
	export let hover = false;
	export let clickable = false;

	const baseClasses = 'bg-dark-bg-secondary rounded-card shadow-lg border transition-all duration-200';
	const hoverClasses = hover ? 'hover:shadow-xl hover:scale-105 border-gray-700 hover:border-gray-600' : 'border-gray-700';
	const clickableClasses = clickable ? 'cursor-pointer' : '';
	const paddingClasses = padding ? 'p-4' : '';
</script>

{#if clickable}
	<div
		class={`${baseClasses} ${hoverClasses} ${clickableClasses} ${paddingClasses}`}
		style="border-color: var(--color-border);"
		on:click
		on:keydown
		role="button"
		tabindex="0"
	>
		<slot />
	</div>
{:else}
	<div
		class={`${baseClasses} ${hoverClasses} ${paddingClasses}`}
		style="border-color: var(--color-border);"
	>
		<slot />
	</div>
{/if}
