<script>
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import HomeSidebar from '$lib/components/layout/HomeSidebar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getFavorites } from '$lib/api/favorites';
	import { getLibraries, getLibrariesSeriesTree } from '$lib/api/libraries';
	import { Heart, Grid, List } from 'lucide-svelte';

	let favorites = [];
	let isLoading = true;
	let error = null;
	let viewMode = 'grid';
	let sortBy = 'recent';

	// Sidebar data
	let libraries = [];
	let seriesTree = [];

	onMount(async () => {
		await Promise.all([loadFavorites(), loadSidebarData()]);
	});

	async function loadSidebarData() {
		try {
			const [libs, tree] = await Promise.all([
				getLibraries(),
				getLibrariesSeriesTree()
			]);
			libraries = libs || [];
			seriesTree = tree || [];
		} catch (err) {
			console.error('Failed to load sidebar data:', err);
		}
	}

	async function loadFavorites() {
		try {
			isLoading = true;
			error = null;
			const raw = await getFavorites();
			favorites = sortFavorites(raw || [], sortBy);
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
				return sorted.sort((a, b) => (b.favoriteDate || b.createdAt || 0) - (a.favoriteDate || a.createdAt || 0));
			case 'title':
				return sorted.sort((a, b) => (a.title || a.name || '').localeCompare(b.title || b.name || ''));
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

	function encodePath(path) {
		if (!path) return '';
		return path
			.split('/')
			.map((segment) => encodeURIComponent(segment))
			.join('/');
	}

	function getFavoriteHref(comic) {
		const libId = comic.libraryId || comic.library_id;
		const rawPath =
			comic.browse_path ||
			comic.browsePath ||
			comic.name ||
			comic.title ||
			comic.series ||
			comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '');

		if (libId && rawPath) {
			return `/library/${libId}/browse/${encodePath(rawPath)}`;
		}

		return `/comic/${libId}/${comic.id}/read`;
	}

	$: sortedFavorites = sortFavorites(favorites, sortBy);
</script>

<svelte:head>
	<title>Favorites - Kottlib</title>
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]">
	<Navbar />

	<div class="flex-1 flex overflow-hidden">
		<HomeSidebar
			{libraries}
			{seriesTree}
			currentFilter={{ type: 'favorites' }}
		/>

		<main class="flex-1 overflow-y-auto px-4 pb-8 scrollbar-thin scrollbar-thumb-[var(--color-border)] scrollbar-track-transparent">
			<div class="w-full pt-4">
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
				<div class="spinner"></div>
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
					<ComicCard
						{comic}
						libraryId={comic.libraryId || comic.library_id}
						variant={viewMode}
						href={getFavoriteHref(comic)}
					/>
				{/each}
			</div>
		{:else}
			<div class="empty-state">
				<Heart class="w-16 h-16 text-gray-500 mb-4" />
				<p class="text-gray-400 mb-4">You haven't added any favorites yet</p>
				<p class="text-gray-500 text-sm mb-6">
					Tap the heart icon on any comic to add it to your favorites
				</p>
				<a href="/library/all/browse" class="btn-primary">Go to Home</a>
			</div>
		{/if}
			</div>
		</main>
	</div>
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
