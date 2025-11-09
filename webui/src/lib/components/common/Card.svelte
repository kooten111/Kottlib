<script>
	export let padding = true;
	export let hover = false;
	export let clickable = false;

	const baseClasses = 'bg-dark-bg-secondary rounded-card shadow-lg';
	const hoverClasses = hover ? 'hover:shadow-xl hover:scale-105 transition-all duration-200' : '';
	const clickableClasses = clickable ? 'cursor-pointer' : '';
	const paddingClasses = padding ? 'p-4' : '';
</script>

<div
	class={`${baseClasses} ${hoverClasses} ${clickableClasses} ${paddingClasses}`}
	on:click
	on:keydown
	role={clickable ? 'button' : undefined}
	tabindex={clickable ? 0 : undefined}
>
	<slot />
</div>
