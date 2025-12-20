<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibraries } from '$lib/api/libraries';
	import { searchComics } from '$lib/api/search';
	import { Filter, SortAsc, Grid, List } from 'lucide-svelte';

	$: searchQuery = $page.url.searchParams.get('q') || '';

	let libraries = [];
	let searchResults = [];
	let isLoading = false;
	let error = null;
	let sidebarOpen = false;
	let viewMode = 'grid';
	let sortBy = 'relevance';

	// Filters
	let filters = {
		libraries: [],
		series: [],
		publishers: [],
		years: [],
		tags: [],
		status: [] // 'unread', 'reading', 'completed'
	};

	onMount(async () => {
		try {
			// Load libraries
			libraries = await getLibraries();

			// If there's a search query, perform search
			if (searchQuery) {
				await performSearch();
			}
		} catch (err) {
			console.error('Failed to initialize search:', err);
			error = err.message;
		}
	});

	// Watch for query changes
	$: if (searchQuery) {
		performSearch();
	}

	async function performSearch() {
		if (!searchQuery.trim()) {
			searchResults = [];
			return;
		}

		try {
			isLoading = true;
			error = null;

			// Search across all libraries
			const results = await Promise.all(
				libraries.map((lib) =>
					searchComics(lib.id, searchQuery)
						.then(comics => comics.map(comic => ({
							...comic,
							libraryId: lib.id,
							libraryName: lib.name
						})))
						.catch((err) => {
							console.error(`Search failed for library ${lib.id}:`, err);
							return [];
						})
				)
			);

			// Combine and flatten results
			searchResults = results.flat().map((comic, index) => ({
				...comic,
				_searchScore: index // Simple relevance score based on order
			}));

			// Apply filters
			searchResults = applyFilters(searchResults);

			// Apply sorting
			searchResults = sortResults(searchResults, sortBy);

			isLoading = false;
		} catch (err) {
			console.error('Search failed:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function applyFilters(results) {
		let filtered = [...results];

		// Filter by libraries
		if (filters.libraries.length > 0) {
			filtered = filtered.filter((comic) =>
				filters.libraries.includes(comic.libraryId)
			);
		}

		// Filter by status
		if (filters.status.length > 0) {
			filtered = filtered.filter((comic) => {
				if (filters.status.includes('unread') && (!comic.currentPage || comic.currentPage === 0)) {
					return true;
				}
				if (filters.status.includes('reading') && comic.currentPage > 0 && comic.currentPage < comic.numPages) {
					return true;
				}
				if (filters.status.includes('completed') && comic.currentPage >= comic.numPages) {
					return true;
				}
				return false;
			});
		}

		// TODO: Add more filter logic for series, publishers, years, tags

		return filtered;
	}

	function sortResults(results, sortType) {
		const sorted = [...results];
		switch (sortType) {
			case 'relevance':
				return sorted.sort((a, b) => a._searchScore - b._searchScore);
			case 'title':
				return sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
			case 'date':
				return sorted.sort((a, b) => (b.year || 0) - (a.year || 0));
			case 'recent':
				return sorted.sort((a, b) => (b.dateAdded || 0) - (a.dateAdded || 0));
			default:
				return sorted;
		}
	}

	function toggleViewMode() {
		viewMode = viewMode === 'grid' ? 'list' : 'grid';
	}

	function handleFilterChange() {
		// Re-apply filters when they change
		if (searchQuery) {
			performSearch();
		}
	}
</script>

<svelte:head>
	<title>Search: {searchQuery || 'Comics'} - Kottlib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<div class="flex flex-1">
		<!-- Sidebar with Filters -->
		<Sidebar bind:open={sidebarOpen}>
			<div class="sidebar-content">
				<h3 class="filter-section-title">Filters</h3>

				<!-- Library Filter -->
				{#if libraries.length > 1}
					<div class="filter-section">
						<h4 class="filter-label">Libraries</h4>
						<div class="filter-options">
							{#each libraries as library}
								<label class="filter-checkbox">
									<input
										type="checkbox"
										bind:group={filters.libraries}
										value={library.id}
										on:change={handleFilterChange}
									/>
									<span>{library.name}</span>
								</label>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Reading Status Filter -->
				<div class="filter-section">
					<h4 class="filter-label">Status</h4>
					<div class="filter-options">
						<label class="filter-checkbox">
							<input
								type="checkbox"
								bind:group={filters.status}
								value="unread"
								on:change={handleFilterChange}
							/>
							<span>Unread</span>
						</label>
						<label class="filter-checkbox">
							<input
								type="checkbox"
								bind:group={filters.status}
								value="reading"
								on:change={handleFilterChange}
							/>
							<span>Reading</span>
						</label>
						<label class="filter-checkbox">
							<input
								type="checkbox"
								bind:group={filters.status}
								value="completed"
								on:change={handleFilterChange}
							/>
							<span>Completed</span>
						</label>
					</div>
				</div>

				<!-- Clear Filters -->
				<button
					class="btn-secondary w-full mt-4"
					on:click={() => {
						filters = { libraries: [], series: [], publishers: [], years: [], tags: [], status: [] };
						handleFilterChange();
					}}
				>
					Clear All Filters
				</button>
			</div>
		</Sidebar>

		<!-- Main Content Area -->
		<main class="flex-1 overflow-y-auto">
			<div class="container mx-auto px-4 py-8 max-w-content">
				<!-- Search Header -->
				<div class="search-header">
					<div>
						<h1 class="search-title">
							{#if searchQuery}
								Search Results for "{searchQuery}"
							{:else}
								Search Comics
							{/if}
						</h1>
						{#if searchResults.length > 0}
							<p class="search-subtitle">Found {searchResults.length} results</p>
						{/if}
					</div>

					<!-- View Controls -->
					<div class="view-controls">
						<!-- Sort Dropdown -->
						<select bind:value={sortBy} on:change={handleFilterChange} class="control-select">
							<option value="relevance">Sort: Relevance</option>
							<option value="title">Sort: Title</option>
							<option value="date">Sort: Year</option>
							<option value="recent">Sort: Recently Added</option>
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

						<!-- Filter Toggle (Mobile) -->
						<button
							class="control-button lg:hidden"
							on:click={() => (sidebarOpen = !sidebarOpen)}
							aria-label="Toggle filters"
						>
							<Filter class="w-5 h-5" />
						</button>
					</div>
				</div>

				<!-- Active Filters Display -->
				{#if filters.status.length > 0 || filters.libraries.length > 0}
					<div class="active-filters">
						<span class="filter-label">Active filters:</span>
						<div class="filter-chips">
							{#each filters.status as status}
								<span class="filter-chip">
									{status}
									<button
										class="chip-remove"
										on:click={() => {
											filters.status = filters.status.filter((s) => s !== status);
											handleFilterChange();
										}}
									>
										×
									</button>
								</span>
							{/each}
							{#each filters.libraries as libraryId}
								{@const library = libraries.find((l) => l.id === libraryId)}
								{#if library}
									<span class="filter-chip">
										{library.name}
										<button
											class="chip-remove"
											on:click={() => {
												filters.libraries = filters.libraries.filter((id) => id !== libraryId);
												handleFilterChange();
											}}
										>
											×
										</button>
									</span>
								{/if}
							{/each}
						</div>
					</div>
				{/if}

				<!-- Loading State -->
				{#if isLoading}
					<div class="loading-container">
						<div class="spinner" />
						<p class="text-gray-400 mt-4">Searching...</p>
					</div>
				{:else if error}
					<!-- Error State -->
					<div class="error-container">
						<p class="text-red-400">Search failed: {error}</p>
					</div>
				{:else if searchQuery && searchResults.length === 0}
					<!-- No Results -->
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
							<circle cx="11" cy="11" r="8" />
							<path d="m21 21-4.35-4.35" />
						</svg>
						<p class="text-gray-400 mb-2">No comics found for "{searchQuery}"</p>
						<p class="text-gray-500 text-sm">Try a different search term or adjust your filters</p>
					</div>
				{:else if searchResults.length > 0}
					<!-- Results Grid -->
					<div class="comics-{viewMode}">
						{#each searchResults as comic}
							<ComicCard {comic} libraryId={comic.libraryId} variant={viewMode} />
						{/each}
					</div>
				{:else}
					<!-- Initial State -->
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
							<circle cx="11" cy="11" r="8" />
							<path d="m21 21-4.35-4.35" />
						</svg>
						<p class="text-gray-400">Enter a search term to find comics</p>
					</div>
				{/if}
			</div>
		</main>
	</div>
</div>

<style>
	.search-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 2rem;
		gap: 2rem;
	}

	.search-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0 0 0.5rem 0;
	}

	.search-subtitle {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0;
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

	.active-filters {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.filter-label {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text-secondary);
	}

	.filter-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.filter-chip {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.75rem;
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-accent);
		border-radius: 9999px;
		font-size: 0.875rem;
		color: var(--color-text);
	}

	.chip-remove {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.1);
		border: none;
		color: var(--color-text);
		cursor: pointer;
		font-size: 1.25rem;
		line-height: 1;
		transition: background 0.2s;
	}

	.chip-remove:hover {
		background: rgba(255, 255, 255, 0.2);
	}

	.sidebar-content {
		padding: 1.5rem;
	}

	.filter-section-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 1.5rem;
	}

	.filter-section {
		margin-bottom: 1.5rem;
	}

	.filter-options {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.filter-checkbox {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--color-text);
		cursor: pointer;
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
		.search-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.search-title {
			font-size: 1.5rem;
		}

		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}
	}
</style>
