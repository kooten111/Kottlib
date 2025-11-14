<script>
	export let variant = 'primary'; // primary, secondary, ghost, danger
	export let size = 'md'; // sm, md, lg
	export let disabled = false;
	export let type = 'button';
	export let href = null;

	const variants = {
		primary: 'bg-accent-orange text-white hover:bg-accent-orange-hover disabled:bg-gray-600 shadow-sm hover:shadow-md',
		secondary: 'bg-dark-bg-tertiary text-dark-text hover:bg-gray-600 disabled:bg-gray-700 border border-gray-600 hover:border-gray-500',
		ghost: 'bg-dark-bg-secondary text-dark-text hover:bg-dark-bg-tertiary disabled:opacity-50 border border-gray-600 hover:border-gray-400',
		danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-600 shadow-sm hover:shadow-md'
	};

	const sizes = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2',
		lg: 'px-6 py-3 text-lg'
	};

	const baseClasses = 'rounded-button font-medium transition-all duration-200 focus-ring disabled:cursor-not-allowed';
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
