<script>
	import { ArrowLeft } from 'lucide-svelte';
	import { goto } from '$app/navigation';

	export let href = '/';
	export let label = 'Back';

	function handleClick(e) {
		e.preventDefault();
		goto(href);
	}
</script>

<button class="back-button" on:click={handleClick}>
	<ArrowLeft class="w-5 h-5" />
	<span>{label}</span>
</button>

<style>
	.back-button {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
		margin-bottom: 1.5rem;
	}

	.back-button:hover {
		background: rgba(255, 255, 255, 0.1);
		border-color: var(--color-accent);
		color: var(--color-accent);
		transform: translateX(-4px);
	}

	.back-button:active {
		transform: translateX(-2px);
	}
</style>
