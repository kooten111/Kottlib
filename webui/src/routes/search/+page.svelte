<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibraries } from '$lib/api/libraries';
	import { searchComics, getSearchFacetValues } from '$lib/api/search';
	import { Filter, Grid, List, Search } from 'lucide-svelte';

	let searchText = '';

	// Sync from URL on navigation (e.g. navbar search)
	$: {
		const urlQ = $page.url.searchParams.get('q') || '';
		if (urlQ && urlQ !== searchText) {
			searchText = urlQ;
		}
	}

	let libraries = [];
	let searchResults = [];
	let isLoading = false;
	let error = null;
	let sidebarOpen = false;
	let viewMode = 'grid';
	let sortBy = 'relevance';
	let isReady = false;
	let selectedFacetFields = ['tags', 'genre'];

	let facets = {
		tags: [],
		genre: []
	};
	let tagsInput = '';
	let tagSuggestions = [];
	let loadingTagSuggestions = false;
	let lastSearchStateKey = '';
	let lastFacetScopeKey = '';

	// Filters
	let filters = {
		libraries: [],
		series: [],
		publishers: [],
		years: [],
		tags: [],
		genre: [],
		status: [] // 'unread', 'reading', 'completed'
	};

	$: queryPreview = buildEffectiveQuery();

	$: if (isReady) {
		const currentStateKey = JSON.stringify({
			searchText,
			libraries: [...filters.libraries].sort(),
			tags: [...filters.tags].sort(),
			genre: [...filters.genre].sort(),
			status: [...filters.status].sort(),
			sortBy,
			librariesLoaded: libraries.map((library) => library.id).sort()
		});

		if (currentStateKey !== lastSearchStateKey) {
			lastSearchStateKey = currentStateKey;
			performSearch();
		}
	}

	onMount(async () => {
		try {
			// Load libraries, excluding hidden ones
			const allLibraries = await getLibraries();
			libraries = allLibraries.filter(lib => !lib.exclude_from_webui);
			await loadFacetValues();
			isReady = true;
		} catch (err) {
			console.error('Failed to initialize search:', err);
			error = err.message;
		}
	});

	$: if (isReady) {
		const facetScopeKey = JSON.stringify({
			libraries: [...filters.libraries].sort(),
			libraryPool: libraries.map((library) => library.id).sort()
		});
		if (facetScopeKey !== lastFacetScopeKey) {
			lastFacetScopeKey = facetScopeKey;
			loadFacetValues();
		}
	}

	async function performSearch() {
		const effectiveQuery = queryPreview;
		if (!effectiveQuery.trim()) {
			searchResults = [];
			return;
		}

		try {
			isLoading = true;
			error = null;

			const scopedLibraries = filters.libraries.length > 0
				? libraries.filter((lib) => filters.libraries.includes(lib.id))
				: libraries;

			if (scopedLibraries.length === 0) {
				searchResults = [];
				isLoading = false;
				return;
			}

			// Search across selected libraries
			const results = await Promise.all(
				scopedLibraries.map((lib) =>
					searchComics(lib.id, effectiveQuery)
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

	async function loadFacetValues() {
		if (!libraries.length) {
			facets = { tags: [], genre: [] };
			return;
		}

		const scopedLibraries = filters.libraries.length > 0
			? libraries.filter((lib) => filters.libraries.includes(lib.id))
			: libraries;

		if (!scopedLibraries.length) {
			facets = { tags: [], genre: [] };
			return;
		}

		try {
			const responses = await Promise.all(
				scopedLibraries.map((library) =>
					getSearchFacetValues({
						libraryId: library.id,
						fields: selectedFacetFields,
						limit: 25
					})
				)
			);

			const merged = mergeFacetValues(responses.map((response) => response.values || {}));
			facets = {
				tags: merged.tags || [],
				genre: merged.genre || []
			};
			refreshTagSuggestions();
		} catch (err) {
			console.error('Failed to load facet values:', err);
		}
	}

	function mergeFacetValues(valueMaps) {
		const buckets = {};
		for (const valueMap of valueMaps) {
			for (const [field, values] of Object.entries(valueMap || {})) {
				if (!buckets[field]) {
					buckets[field] = new Map();
				}

				for (const value of values) {
					const normalized = `${value.name || ''}`.trim();
					if (!normalized) continue;
					const key = normalized.toLowerCase();
					const previous = buckets[field].get(key) || { name: normalized, count: 0 };
					previous.count += Number(value.count || 0);
					buckets[field].set(key, previous);
				}
			}
		}

		const merged = {};
		for (const [field, valuesMap] of Object.entries(buckets)) {
			merged[field] = Array.from(valuesMap.values())
				.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
		}

		return merged;
	}

	function buildEffectiveQuery() {
		const parts = [];
		const normalizedText = (searchText || '').trim();
		if (normalizedText) {
			parts.push(normalizedText);
		}

		for (const tag of filters.tags) {
			parts.push(formatFieldQuery('tags', tag));
		}

		for (const genre of filters.genre) {
			parts.push(formatFieldQuery('genre', genre));
		}

		return parts.join(' ').trim();
	}

	function formatFieldQuery(field, value) {
		const trimmed = `${value || ''}`.trim();
		if (!trimmed) return '';
		const needsQuotes = /\s/.test(trimmed);
		return `${field}:${needsQuotes ? `"${trimmed}"` : trimmed}`;
	}

	function applyFilters(results) {
		let filtered = [...results];

		// Filter by status
		if (filters.status.length > 0) {
			filtered = filtered.filter((comic) => {
				const currentPage = comic.currentPage ?? comic.current_page ?? 0;
				const numPages = comic.numPages ?? comic.num_pages ?? 0;
				if (filters.status.includes('unread') && currentPage === 0) {
					return true;
				}
				if (filters.status.includes('reading') && currentPage > 0 && currentPage < numPages) {
					return true;
				}
				if (filters.status.includes('completed') && numPages > 0 && currentPage >= numPages) {
					return true;
				}
				return false;
			});
		}

		// TODO: Add more filter logic for series, publishers, years, tags

		if (filters.genre.length > 0) {
			const expectedGenres = filters.genre.map((genre) => genre.toLowerCase());
			filtered = filtered.filter((comic) => {
				const comicGenre = `${comic.genre || ''}`.toLowerCase();
				return expectedGenres.some((genre) => comicGenre.includes(genre));
			});
		}

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
		loadFacetValues();
	}

	function refreshTagSuggestions() {
		const normalized = tagsInput.trim().toLowerCase();
		if (!normalized) {
			tagSuggestions = facets.tags
				.filter((tag) => !filters.tags.includes(tag.name))
				.slice(0, 8);
			return;
		}

		tagSuggestions = facets.tags
			.filter((tag) => !filters.tags.includes(tag.name))
			.filter((tag) => tag.name.toLowerCase().includes(normalized))
			.slice(0, 8);
	}

	function addTag(tagName) {
		const normalized = `${tagName || ''}`.trim();
		if (!normalized || filters.tags.includes(normalized)) {
			return;
		}
		filters.tags = [...filters.tags, normalized];
		tagsInput = '';
		refreshTagSuggestions();
	}

	function removeTag(tagName) {
		filters.tags = filters.tags.filter((tag) => tag !== tagName);
		refreshTagSuggestions();
	}

	function toggleGenre(genreName) {
		if (filters.genre.includes(genreName)) {
			filters.genre = filters.genre.filter((genre) => genre !== genreName);
			return;
		}
		filters.genre = [...filters.genre, genreName];
	}

	function clearAdvancedFilters() {
		filters = {
			...filters,
			tags: [],
			genre: [],
			status: [],
			libraries: []
		};
		tagsInput = '';
		tagSuggestions = [];
	}

	function handleTagInputChange() {
		loadingTagSuggestions = true;
		refreshTagSuggestions();
		loadingTagSuggestions = false;
	}

	function handleTagInputKeydown(event) {
		if (event.key !== 'Enter' && event.key !== ',') {
			return;
		}
		event.preventDefault();
		addTag(tagsInput);
	}
</script>

<svelte:head>
	<title>Search: {searchText || 'Comics'} - Kottlib</title>
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
						filters = { libraries: [], series: [], publishers: [], years: [], tags: [], genre: [], status: [] };
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
					<div class="search-header-left">
						<div class="search-input-wrapper">
							<Search class="search-input-icon" />
							<input
								type="text"
								class="search-input"
								placeholder="Search comics..."
								bind:value={searchText}
							/>
						</div>
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

				<div class="advanced-filters-panel">
					<div class="advanced-filters-head">
						<h2>Advanced Filters</h2>
						<button class="btn-secondary" on:click={clearAdvancedFilters}>Reset</button>
					</div>

					<div class="advanced-filters-grid">
						<div class="advanced-field">
							<p class="field-heading">Libraries</p>
							<div class="selectable-list">
								{#each libraries as library}
									<button
										type="button"
										class="selectable-pill"
										class:selected={filters.libraries.includes(library.id)}
										on:click={() => {
											if (filters.libraries.includes(library.id)) {
												filters.libraries = filters.libraries.filter((id) => id !== library.id);
											} else {
												filters.libraries = [...filters.libraries, library.id];
											}
											handleFilterChange();
										}}
									>
										{library.name}
									</button>
								{/each}
							</div>
						</div>

						<div class="advanced-field">
							<label for="search-loose-tags">Loose Tags</label>
							<input
								id="search-loose-tags"
								type="text"
								placeholder="Type tag, press Enter"
								bind:value={tagsInput}
								on:input={handleTagInputChange}
								on:keydown={handleTagInputKeydown}
								class="advanced-input"
							/>
							{#if loadingTagSuggestions}
								<p class="hint-text">Loading tags...</p>
							{:else if tagSuggestions.length > 0}
								<div class="selectable-list compact">
									{#each tagSuggestions as tag}
										<button type="button" class="selectable-pill" on:click={() => addTag(tag.name)}>
											{tag.name} <span>({tag.count})</span>
										</button>
									{/each}
								</div>
							{/if}
						</div>

						<div class="advanced-field">
							<p class="field-heading">Genre</p>
							<div class="selectable-list compact">
								{#each facets.genre.slice(0, 20) as genre}
									<button
										type="button"
										class="selectable-pill"
										class:selected={filters.genre.includes(genre.name)}
										on:click={() => toggleGenre(genre.name)}
									>
										{genre.name} <span>({genre.count})</span>
									</button>
								{/each}
							</div>
						</div>
					</div>

					<p class="query-preview">Query: {queryPreview || '(empty)'}</p>
				</div>

				<!-- Active Filters Display -->
				{#if filters.status.length > 0 || filters.libraries.length > 0 || filters.tags.length > 0 || filters.genre.length > 0}
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
							{#each filters.tags as tag}
								<span class="filter-chip">
									tags:{tag}
									<button class="chip-remove" on:click={() => removeTag(tag)}>×</button>
								</span>
							{/each}
							{#each filters.genre as genre}
								<span class="filter-chip">
									genre:{genre}
									<button class="chip-remove" on:click={() => toggleGenre(genre)}>×</button>
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
					<div class="spinner"></div>
					<p class="text-gray-400 mt-4">Searching...</p>
				</div>
				{:else if error}
					<!-- Error State -->
					<div class="error-container">
						<p class="text-red-400">Search failed: {error}</p>
					</div>
				{:else if queryPreview && searchResults.length === 0}
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
						<p class="text-gray-400 mb-2">No comics found for "{queryPreview}"</p>
						<p class="text-gray-500 text-sm">Try a different search term or adjust your filters</p>
					</div>
				{:else if searchResults.length > 0}
					<!-- Results Grid -->
					<div class="comics-{viewMode}">
						{#each searchResults as comic}
							<ComicCard
								{comic}
								libraryId={comic.libraryId}
								variant={viewMode}
								isFolder={comic.type === 'series' || comic.type === 'folder' || comic.item_type === 'folder'}
								itemCount={comic.comic_count || comic.item_count || 0}
								href={comic.browse_path || ((comic.type === 'series' || comic.type === 'folder' || comic.item_type === 'folder')
									? `/library/${comic.libraryId}/browse/${comic.id}`
									: null)}
							/>
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

	.search-header-left {
		flex: 1;
		min-width: 0;
	}

	.search-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-input-wrapper :global(.search-input-icon) {
		position: absolute;
		left: 0.75rem;
		width: 1.25rem;
		height: 1.25rem;
		color: var(--color-text-muted);
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		padding: 0.75rem 0.75rem 0.75rem 2.5rem;
		font-size: 1.125rem;
		font-weight: 500;
		background: var(--color-secondary-bg);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		color: var(--color-text);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.search-input::placeholder {
		color: var(--color-text-muted);
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

	.advanced-filters-panel {
		background: color-mix(in srgb, var(--color-secondary-bg) 85%, transparent);
		border: 1px solid rgba(255, 255, 255, 0.08);
		border-radius: 12px;
		padding: 1rem;
		margin-bottom: 1.25rem;
	}

	.advanced-filters-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.advanced-filters-head h2 {
		font-size: 1rem;
		font-weight: 700;
		margin: 0;
	}

	.advanced-filters-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 1rem;
	}

	.advanced-field {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.advanced-field label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--color-text-secondary);
	}

	.field-heading {
		margin: 0;
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--color-text-secondary);
	}

	.advanced-input {
		background: var(--color-secondary-bg);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		padding: 0.5rem 0.625rem;
		color: var(--color-text);
	}

	.advanced-input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.selectable-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.selectable-list.compact {
		max-height: 180px;
		overflow-y: auto;
	}

	.selectable-pill {
		padding: 0.35rem 0.625rem;
		border-radius: 999px;
		border: 1px solid rgba(255, 255, 255, 0.1);
		background: var(--color-secondary-bg);
		color: var(--color-text);
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.selectable-pill span {
		opacity: 0.7;
		font-size: 0.75rem;
	}

	.selectable-pill.selected {
		border-color: var(--color-accent);
		background: color-mix(in srgb, var(--color-accent) 12%, transparent);
	}

	.query-preview {
		margin: 0.75rem 0 0;
		font-size: 0.8125rem;
		color: var(--color-text-secondary);
		word-break: break-word;
	}

	.hint-text {
		margin: 0;
		font-size: 0.8125rem;
		color: var(--color-text-secondary);
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

		.advanced-filters-grid {
			grid-template-columns: 1fr;
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
