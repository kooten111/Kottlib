<script>
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibraries, getContinueReading } from '$lib/api/libraries';
	import { BookOpen, Grid, List, SortAsc } from 'lucide-svelte';
	import { navigationContext } from '$lib/stores/library';

	let libraries = [];
	let continueReading = [];
	let filteredContinueReading = [];
	let isLoading = true;
	let error = null;
	let viewMode = 'grid';
	let sortBy = 'recent';

	// Read the current context value immediately
	let currentContext = { type: 'all' };
	const unsubscribeContext = navigationContext.subscribe(value => {
		currentContext = value;
	});

	onMount(async () => {
		console.log('Continue reading page mounted with context:', currentContext);
		await loadContinueReading();

		return () => {
			unsubscribeContext();
		};
	});

	// Reactively apply filter when context or data changes
	$: if (continueReading.length > 0 && currentContext) {
		console.log('Reactive update - context or data changed');
		applyFilter();
	}

	async function loadContinueReading() {
		try {
			isLoading = true;
			error = null;

			// Load libraries first
			libraries = await getLibraries();

			// Load continue reading from all libraries
			const continueResults = await Promise.all(
				libraries.map((lib) =>
					getContinueReading(lib.id, 100)
						.then((comics) =>
							comics
								.filter((comic) => comic && comic.currentPage > 0 && comic.currentPage < comic.numPages)
								.map((comic) => ({ ...comic, libraryId: lib.id }))
						)
						.catch(() => [])
				)
			);

			// Sort globally by last_time_opened timestamp after flattening all libraries
			continueReading = continueResults
				.flat()
				.sort((a, b) => {
					const aTime = a.last_time_opened ? new Date(a.last_time_opened).getTime() : 0;
					const bTime = b.last_time_opened ? new Date(b.last_time_opened).getTime() : 0;
					return bTime - aTime; // Most recent first
				});

			isLoading = false;
		} catch (err) {
			console.error('Failed to load continue reading:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function applyFilter() {
		if (!continueReading.length) {
			filteredContinueReading = [];
			return;
		}

		let filtered = continueReading;

		console.log('Applying filter with context:', currentContext);
		console.log('Total continue reading comics:', continueReading.length);
		console.log('Sample comic:', continueReading[0]);

		// Apply context-based filtering
		if (currentContext.seriesNames && currentContext.seriesNames.length > 0) {
			console.log('Filtering by series names:', currentContext.seriesNames);
			filtered = continueReading.filter(comic => {
				// Check if comic title contains any of the series names
				return currentContext.seriesNames.some(seriesName =>
					comic.title && comic.title.includes(seriesName)
				);
			});
			console.log('Filtered to', filtered.length, 'comics by series name matching');
		} else if (currentContext.type === 'library' && currentContext.libraryId) {
			console.log('Filtering by library:', currentContext.libraryId);
			filtered = continueReading.filter(comic => comic.libraryId === currentContext.libraryId);
			console.log('Filtered to', filtered.length, 'comics');
		} else if (currentContext.type === 'series' && currentContext.seriesName) {
			console.log('Filtering by series:', currentContext.seriesName, 'in library', currentContext.libraryId);
			filtered = continueReading.filter(comic => {
				const matchesLibrary = comic.libraryId === currentContext.libraryId;
				const matchesSeries = comic.series === currentContext.seriesName ||
				                      (comic.title && comic.title.includes(currentContext.seriesName));
				return matchesLibrary && matchesSeries;
			});
			console.log('Filtered to', filtered.length, 'comics');
		}

		filteredContinueReading = sortComics(filtered, sortBy);
	}

	function sortComics(comicsList, sortType) {
		const sorted = [...comicsList];
		switch (sortType) {
			case 'recent':
				return sorted.sort((a, b) => {
					const aTime = a.last_time_opened ? new Date(a.last_time_opened).getTime() : 0;
					const bTime = b.last_time_opened ? new Date(b.last_time_opened).getTime() : 0;
					return bTime - aTime;
				});
			case 'progress':
				return sorted.sort((a, b) => {
					const progressA = (a.currentPage / a.numPages) * 100;
					const progressB = (b.currentPage / b.numPages) * 100;
					return progressB - progressA;
				});
			case 'title':
				return sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
			case 'series':
				return sorted.sort((a, b) => (a.series || '').localeCompare(b.series || ''));
			default:
				return sorted;
		}
	}

	function toggleViewMode() {
		viewMode = viewMode === 'grid' ? 'list' : 'grid';
	}

	// Re-apply filter when sort changes
	$: if (sortBy && continueReading.length > 0) {
		applyFilter();
	}
</script>

<svelte:head>
	<title>Continue Reading - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		<!-- Page Header -->
		<div class="page-header">
			<div class="header-title-section">
				<div class="icon-wrapper">
					<BookOpen class="w-8 h-8 text-accent-orange" />
				</div>
				<div>
					<h1 class="page-title">Continue Reading</h1>
					{#if !isLoading}
						{#if currentContext.type === 'library'}
							<p class="page-subtitle">{filteredContinueReading.length} comics in progress (filtered by library)</p>
						{:else if currentContext.type === 'series'}
							<p class="page-subtitle">{filteredContinueReading.length} comics in progress (filtered by series)</p>
						{:else if continueReading.length > 0}
							<p class="page-subtitle">{filteredContinueReading.length} comics in progress</p>
						{/if}
					{/if}
				</div>
			</div>

			{#if filteredContinueReading.length > 0}
				<div class="view-controls">
					<!-- Sort Dropdown -->
					<select bind:value={sortBy} class="control-select">
						<option value="recent">Sort: Recently Read</option>
						<option value="progress">Sort: Progress</option>
						<option value="title">Sort: Title</option>
						<option value="series">Sort: Series</option>
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
				<p class="text-gray-400 mt-4">Loading in-progress comics...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="text-red-400">Failed to load comics: {error}</p>
				<button class="btn-primary mt-4" on:click={loadContinueReading}>Try Again</button>
			</div>
		{:else if filteredContinueReading.length > 0}
			<div class="comics-{viewMode}">
				{#each filteredContinueReading as comic}
					<ComicCard {comic} libraryId={comic.libraryId} variant={viewMode} showProgress={true} />
				{/each}
			</div>
		{:else}
			<div class="empty-state">
				<BookOpen class="w-16 h-16 text-gray-500 mb-4" />
				{#if currentContext.type === 'library'}
					<p class="text-gray-400 mb-4">No comics in progress for this library</p>
					<p class="text-gray-500 text-sm">
						Select "Libraries" to see all comics or start reading in this library
					</p>
				{:else if currentContext.type === 'series'}
					<p class="text-gray-400 mb-4">No comics in progress for this series</p>
					<p class="text-gray-500 text-sm">
						Select a different series or start reading from this series
					</p>
				{:else}
					<p class="text-gray-400 mb-4">No comics in progress</p>
					<p class="text-gray-500 text-sm">
						Start reading a comic to see it here
					</p>
				{/if}
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
