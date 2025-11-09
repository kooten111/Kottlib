<script>
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import LibraryCard from '$lib/components/comic/LibraryCard.svelte';
	import { getLibraries } from '$lib/api/libraries';

	let libraries = [];
	let isLoading = true;
	let error = null;

	onMount(async () => {
		try {
			const libsData = await getLibraries();
			libraries = libsData || [];
			isLoading = false;
		} catch (err) {
			console.error('Failed to load libraries:', err);
			error = err.message;
			isLoading = false;
		}
	});
</script>

<svelte:head>
	<title>Browse Libraries - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		<h1 class="page-title">Your Libraries</h1>

		{#if isLoading}
			<div class="loading-container">
				<div class="spinner" />
				<p class="text-gray-400 mt-4">Loading libraries...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="text-red-400">Failed to load libraries: {error}</p>
			</div>
		{:else if libraries.length > 0}
			<div class="libraries-list">
				{#each libraries as library}
					<LibraryCard {library} />
				{/each}
			</div>
		{:else}
			<div class="empty-state">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="64"
					height="64"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="text-gray-500 mb-4"
				>
					<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
				</svg>
				<p class="text-gray-400">No libraries found. Add a library to get started.</p>
			</div>
		{/if}
	</main>
</div>

<style>
	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin-bottom: 2rem;
	}

	.loading-container,
	.error-container,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
	}

	.spinner {
		width: 64px;
		height: 64px;
		border: 4px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.libraries-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	@media (max-width: 640px) {
		.page-title {
			font-size: 1.5rem;
		}
	}
</style>
