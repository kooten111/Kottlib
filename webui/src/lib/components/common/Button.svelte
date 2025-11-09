<script>
	export let variant = 'primary'; // primary, secondary, ghost, danger
	export let size = 'md'; // sm, md, lg
	export let disabled = false;
	export let type = 'button';
	export let href = null;

	const variants = {
		primary: 'bg-accent-orange text-white hover:bg-orange-600 disabled:bg-gray-600',
		secondary: 'bg-dark-bg-tertiary text-dark-text hover:bg-gray-600 disabled:bg-gray-700',
		ghost: 'bg-transparent text-dark-text hover:bg-dark-bg-tertiary disabled:opacity-50',
		danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-600'
	};

	const sizes = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2',
		lg: 'px-6 py-3 text-lg'
	};

	const baseClasses = 'rounded-button font-medium transition-colors focus-ring disabled:cursor-not-allowed';
	const classes = `${baseClasses} ${variants[variant]} ${sizes[size]}`;
</script>

{#if href}
	<a {href} class={classes} class:opacity-50={disabled}>
		<slot />
	</a>
{:else}
	<button {type} {disabled} class={classes} on:click>
		<slot />
	</button>
{/if}
