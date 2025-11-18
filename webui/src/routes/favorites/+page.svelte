<script>
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibraries } from '$lib/api/libraries';
	import { getFavorites } from '$lib/api/favorites';
	import { Heart, Grid, List, SortAsc } from 'lucide-svelte';

	let libraries = [];
	let favorites = [];
	let isLoading = true;
	let error = null;
	let viewMode = 'grid';
	let sortBy = 'recent';

	onMount(async () => {
		await loadFavorites();
	});

	async function loadFavorites() {
		try {
			isLoading = true;
			error = null;

			// Load libraries first
			libraries = await getLibraries();

			// Load favorites from all libraries
			const favResults = await Promise.all(
				libraries.map((lib) =>
					getFavorites(lib.id)
						.then((comics) => comics.map((comic) => ({ ...comic, libraryId: lib.id })))
						.catch(() => [])
				)
			);

			favorites = favResults.flat();
			favorites = sortFavorites(favorites, sortBy);

			isLoading = false;
		} catch (err) {
			console.error('Failed to load favorites:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function sortFavorites(favList, sortType) {
		const sorted = [...favList];
		switch (sortType) {
			case 'recent':
				return sorted.sort((a, b) => (b.favoriteDate || 0) - (a.favoriteDate || 0));
			case 'title':
				return sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
			case 'series':
				return sorted.sort((a, b) => (a.series || '').localeCompare(b.series || ''));
			case 'year':
				return sorted.sort((a, b) => (b.year || 0) - (a.year || 0));
			default:
				return sorted;
		}
	}

	function toggleViewMode() {
		viewMode = viewMode === 'grid' ? 'list' : 'grid';
	}

	$: sortedFavorites = sortFavorites(favorites, sortBy);
</script>

<svelte:head>
	<title>Favorites - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		<!-- Page Header -->
		<div class="page-header">
			<div class="header-title-section">
				<div class="icon-wrapper">
					<Heart class="w-8 h-8 text-accent-orange" fill="currentColor" />
				</div>
				<div>
					<h1 class="page-title">Favorites</h1>
					{#if !isLoading && favorites.length > 0}
						<p class="page-subtitle">{favorites.length} favorite comics</p>
					{/if}
				</div>
			</div>

			{#if favorites.length > 0}
				<div class="view-controls">
					<!-- Sort Dropdown -->
					<select bind:value={sortBy} class="control-select">
						<option value="recent">Sort: Recently Added</option>
						<option value="title">Sort: Title</option>
						<option value="series">Sort: Series</option>
						<option value="year">Sort: Year</option>
					</select>

					<!-- View Toggle -->
					<button
						class="control-button"
						on:click={toggleViewMode}
						aria-label="Toggle view mode"
					>
						{#if viewMode === 'grid'}
							<Grid class="w-5 h-5" />
						{:else}
							<List class="w-5 h-5" />
						{/if}
					</button>
				</div>
			{/if}
		</div>

		<!-- Content -->
		{#if isLoading}
			<div class="loading-container">
				<div class="spinner" />
				<p class="text-gray-400 mt-4">Loading favorites...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="text-red-400">Failed to load favorites: {error}</p>
				<button class="btn-primary mt-4" on:click={loadFavorites}>Try Again</button>
			</div>
		{:else if sortedFavorites.length > 0}
			<div class="comics-{viewMode}">
				{#each sortedFavorites as comic}
					<ComicCard {comic} libraryId={comic.libraryId} variant={viewMode} />
				{/each}
			</div>
		{:else}
			<div class="empty-state">
				<Heart class="w-16 h-16 text-gray-500 mb-4" />
				<p class="text-gray-400 mb-4">You haven't added any favorites yet</p>
				<p class="text-gray-500 text-sm mb-6">
					Tap the heart icon on any comic to add it to your favorites
				</p>
				<a href="/browse" class="btn-primary">Browse Comics</a>
			</div>
		{/if}
	</main>
</div>

<style>
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 2rem;
		gap: 2rem;
	}

	.header-title-section {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.icon-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 56px;
		height: 56px;
		background: var(--color-secondary-bg);
		border-radius: 12px;
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.page-subtitle {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0.25rem 0 0 0;
	}

	.view-controls {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.control-select {
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		background: var(--color-secondary-bg);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 4px;
		color: var(--color-text);
		cursor: pointer;
	}

	.control-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: 4px;
		background: var(--color-secondary-bg);
		border: 1px solid transparent;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.control-button:hover {
		border-color: var(--color-accent);
		color: var(--color-text);
	}

	.loading-container,
	.error-container,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
		text-align: center;
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

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
	}

	.comics-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	@media (max-width: 768px) {
		.page-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.page-title {
			font-size: 1.5rem;
		}

		.icon-wrapper {
			width: 48px;
			height: 48px;
		}

		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}
	}
</style>
