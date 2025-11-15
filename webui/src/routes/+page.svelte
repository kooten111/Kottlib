<script>
	import { onMount } from 'svelte';
	import Navbar from '$components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import SeriesTree from '$lib/components/layout/SeriesTree.svelte';
	import InfiniteScroll from '$lib/components/common/InfiniteScroll.svelte';
	import HorizontalCarousel from '$lib/components/common/HorizontalCarousel.svelte';
	import SkeletonCard from '$lib/components/common/SkeletonCard.svelte';
	import { getLibraries, getSeries, getContinueReading, getLibrariesSeriesTree } from '$lib/api/libraries';
	import { searchComics } from '$lib/api/search';
	import { BookOpen, Library, TrendingUp, Grid, List, SlidersHorizontal } from 'lucide-svelte';
	import { navigationContext, currentFilterStore } from '$lib/stores/library';
	import { searchStore } from '$lib/stores/search';
	import { preferencesStore } from '$lib/stores/preferences';

	// Receive server-side loaded data
	export let data;

	let libraries = [];
	let continueReading = [];
	let filteredContinueReading = [];
	let allSeries = [];
	let displayedSeries = [];
	let isLoading = true;
	let isLoadingMore = false;
	let error = null;
	let seriesTree = [];
	let currentFilter = $currentFilterStore;
	let searchQuery = '';
	let searchResults = [];
	let hasMoreSeries = true;
	let seriesPageSize = 50;
	let filteredSeriesTree = [];
	let lastSearchQuery = '';
	let searchDebounceTimer;
	let showSizeSlider = false;

	// React to search store changes with debounce (increased from 300ms to 500ms)
	$: if (!isLoading) {
		const newQuery = $searchStore.query || '';
		console.log('[Home] Search store changed. New query:', newQuery, 'Last query:', lastSearchQuery, 'isLoading:', isLoading);
		if (newQuery !== lastSearchQuery) {
			console.log('[Home] Query changed, setting up debounce timer');
			if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
			searchDebounceTimer = setTimeout(() => {
				console.log('[Home] Debounce timer fired, calling handleSearch with:', newQuery);
				lastSearchQuery = newQuery;
				handleSearch(newQuery);
			}, 500); // Increased from 300ms for better performance
		}
	}

	onMount(async () => {
		await loadHomeData();

		// Restore filter from persistent store if present
		if ($currentFilterStore) {
			console.log('[Home] Restoring filter from store:', $currentFilterStore);
			await restoreFilter($currentFilterStore);
		}

		// Restore search from URL if present
		if (typeof window !== 'undefined') {
			const url = new URL(window.location.href);
			const queryParam = url.searchParams.get('q');
			if (queryParam) {
				searchQuery = queryParam;
				await handleSearch(queryParam);
			}
		}
	});

	async function loadHomeData() {
		try {
			isLoading = true;
			error = null;

			// Use server-side data if available (SSR), otherwise load client-side
			if (data?.libraries && data?.seriesTree && data?.firstLibrary) {
				console.log('[Home] Using server-side rendered data');
				libraries = data.libraries;
				seriesTree = data.seriesTree;

				// Use SSR data directly - all data pre-loaded on server
				continueReading = data.firstLibrary.continueReading || [];
				allSeries = data.firstLibrary.recentSeries || [];
				displayedSeries = allSeries.slice(0, seriesPageSize);
				hasMoreSeries = allSeries.length > seriesPageSize;

				console.log('[Home] SSR data loaded:', {
					totalSeries: allSeries.length,
					displayedSeries: displayedSeries.length,
					seriesPageSize,
					hasMoreSeries
				});

				// Initialize filtered tree
				filteredSeriesTree = seriesTree;
				isLoading = false;
			} else {
				// Fallback to client-side loading if SSR data not available
				console.log('[Home] Server data not available, loading client-side');
				await loadClientSide();
			}
		} catch (err) {
			console.error('Failed to load data:', err);
			error = err.message;
			isLoading = false;
		}
	}

	// Client-side loading function as fallback (loads all data at once)
	async function loadClientSide() {
		try {
			// Load libraries and series tree
			[libraries, seriesTree] = await Promise.all([
				getLibraries(),
				getLibrariesSeriesTree()
			]);

			if (!libraries || libraries.length === 0) {
				isLoading = false;
				return;
			}

			// Load continue reading and series for ALL libraries
			const [continueReadingResults, allSeriesResults] = await Promise.all([
				// Continue reading
				Promise.all(
					libraries.map(async (lib) => {
						try {
							const comics = await getContinueReading(lib.id, 50);
							return comics.map(comic => ({ ...comic, libraryId: lib.id }));
						} catch {
							return [];
						}
					})
				),
				// All series
				Promise.all(
					libraries.map(async (lib) => {
						try {
							const series = await getSeries(lib.id, 'recent');
							return series.map(s => ({ ...s, libraryId: lib.id }));
						} catch (err) {
							console.error(`Failed to fetch series for library ${lib.id}:`, err);
							return [];
						}
					})
				)
			]);

			continueReading = continueReadingResults.flat().slice(0, 20);

			// Interleave series from different libraries
			const maxLength = Math.max(...allSeriesResults.map(r => r.length));
			allSeries = [];
			for (let i = 0; i < maxLength; i++) {
				for (const libraryResults of allSeriesResults) {
					if (i < libraryResults.length) {
						allSeries.push(libraryResults[i]);
					}
				}
			}

			displayedSeries = allSeries.slice(0, seriesPageSize);
			hasMoreSeries = allSeries.length > seriesPageSize;

			console.log('[Home] Client-side data loaded:', {
				totalSeries: allSeries.length,
				displayedSeries: displayedSeries.length,
				seriesPageSize,
				hasMoreSeries
			});

			// Initialize filtered tree
			filteredSeriesTree = seriesTree;
			isLoading = false;
		} catch (err) {
			console.error('Failed to load client-side data:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function handleTreeFilter(event) {
		const { type, libraryId, folderId, folderName, comicId, libraryName } = event.detail;

		currentFilter = event.detail;
		// Persist filter to localStorage
		currentFilterStore.set(event.detail);

		// Update navigation context for continue reading filtering
		if (type === 'all') {
			navigationContext.set({ type: 'all', seriesNames: [] });
			// Show all series from all libraries
			displayedSeries = allSeries.slice(0, seriesPageSize);
			hasMoreSeries = allSeries.length > seriesPageSize;
		} else if (type === 'library') {
			const librarySeries = allSeries.filter(s => s.libraryId === libraryId);
			navigationContext.set({
				type: 'library',
				libraryId,
				libraryName,
				seriesNames: librarySeries.map(s => s.series_name)
			});
			// Filter to show only series from selected library with pagination
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;
		} else if (type === 'folder') {
			// Navigate to series view page
			// The folder name corresponds to the series name
			window.location.href = `/series/${libraryId}/${encodeURIComponent(folderName)}`;
		} else if (type === 'comic') {
			// Navigate to comic reader
			window.location.href = `/comic/${libraryId}/${comicId}/read`;
		}
	}

	function resetFilter() {
		currentFilter = null;
		// Clear persisted filter
		currentFilterStore.set(null);
		navigationContext.set({ type: 'all' });
		displayedSeries = allSeries.slice(0, seriesPageSize);
		hasMoreSeries = allSeries.length > seriesPageSize;
	}

	async function restoreFilter(filter) {
		if (!filter) return;

		console.log('[Home] Restoring filter:', filter);
		currentFilter = filter;

		// Apply the filter based on its type
		if (filter.type === 'all') {
			navigationContext.set({ type: 'all', seriesNames: [] });
			displayedSeries = allSeries.slice(0, seriesPageSize);
			hasMoreSeries = allSeries.length > seriesPageSize;
		} else if (filter.type === 'library') {
			const librarySeries = allSeries.filter(s => s.libraryId === filter.libraryId);
			navigationContext.set({
				type: 'library',
				libraryId: filter.libraryId,
				libraryName: filter.libraryName,
				seriesNames: librarySeries.map(s => s.series_name)
			});
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;
		} else if (filter.type === 'folder') {
			const librarySeries = allSeries.filter(s =>
				s.libraryId === filter.libraryId && s.series_name === filter.folderName
			);
			navigationContext.set({
				type: 'folder',
				libraryId: filter.libraryId,
				folderName: filter.folderName,
				seriesNames: librarySeries.map(s => s.series_name)
			});
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;
		}
	}

	async function loadMoreSeries() {
		if (isLoadingMore || !hasMoreSeries) {
			console.log('[Home] loadMoreSeries blocked:', { isLoadingMore, hasMoreSeries });
			return;
		}

		console.log('[Home] loadMoreSeries triggered');
		isLoadingMore = true;

		// Use requestAnimationFrame to ensure smooth UI updates
		await new Promise(resolve => requestAnimationFrame(resolve));

		const currentLength = displayedSeries.length;

		// Determine the base source based on current filters
		let baseSource;
		if (searchQuery) {
			// If searching, use search results
			baseSource = searchResults;
		} else if (currentFilter?.type === 'library') {
			// If library filter is active, filter allSeries by library
			baseSource = allSeries.filter(s => s.libraryId === currentFilter.libraryId);
		} else {
			// Otherwise use all series
			baseSource = allSeries;
		}

		const nextBatch = baseSource.slice(currentLength, currentLength + seriesPageSize);

		console.log('[Home] Loading more:', {
			currentLength,
			baseSourceLength: baseSource.length,
			nextBatchLength: nextBatch.length,
			seriesPageSize,
			filterType: currentFilter?.type,
			libraryId: currentFilter?.libraryId
		});

		if (nextBatch.length > 0) {
			displayedSeries = [...displayedSeries, ...nextBatch];
			hasMoreSeries = displayedSeries.length < baseSource.length;
			console.log('[Home] Added batch. New displayedSeries length:', displayedSeries.length, 'hasMore:', hasMoreSeries);
		} else {
			hasMoreSeries = false;
			console.log('[Home] No more items to load');
		}

		// Small delay to prevent rapid fire loading
		await new Promise(resolve => setTimeout(resolve, 100));
		isLoadingMore = false;
	}

	async function handleSearch(query) {
		const trimmedQuery = query?.trim() || '';
		searchQuery = trimmedQuery;

		console.log('[Home] handleSearch called with query:', query, 'trimmed:', trimmedQuery);

		// Update URL without adding to history
		if (typeof window !== 'undefined') {
			const url = new URL(window.location.href);
			if (trimmedQuery) {
				url.searchParams.set('q', trimmedQuery);
			} else {
				url.searchParams.delete('q');
			}
			window.history.replaceState({}, '', url);
		}

		// Clear search if query is empty (allow 1 character searches)
		if (!trimmedQuery) {
			console.log('[Home] Empty query, clearing search results');
			// Clear search - show original filtered data
			displayedSeries = currentFilter?.type === 'library'
				? allSeries.filter(s => s.libraryId === currentFilter.libraryId).slice(0, seriesPageSize)
				: allSeries.slice(0, seriesPageSize);
			hasMoreSeries = (currentFilter?.type === 'library'
				? allSeries.filter(s => s.libraryId === currentFilter.libraryId)
				: allSeries).length > seriesPageSize;
			searchResults = [];
			filteredSeriesTree = seriesTree; // Reset tree filter
			searchStore.update(s => ({ ...s, isSearching: false }));
			filterContinueReadingBySeries();
			return;
		}

		console.log('[Home] Performing search for:', trimmedQuery);
		searchStore.update(s => ({ ...s, isSearching: true }));

		try {
			// Filter allSeries by series name instead of API search
			const lowerQuery = trimmedQuery.toLowerCase();
			console.log('[Home] Filtering', allSeries.length, 'series by name containing:', lowerQuery);

			searchResults = allSeries.filter(series =>
				series.series_name && series.series_name.toLowerCase().includes(lowerQuery)
			);
			console.log('[Home] Found', searchResults.length, 'matching series');

			// Filter based on current library selection
			let filteredResults = searchResults;
			if (currentFilter?.type === 'library') {
				filteredResults = searchResults.filter(s => s.libraryId === currentFilter.libraryId);
			}

			displayedSeries = filteredResults.slice(0, seriesPageSize);
			hasMoreSeries = filteredResults.length > seriesPageSize;
			console.log('[Home] Displaying', displayedSeries.length, 'series, hasMore:', hasMoreSeries);

			// Filter sidebar tree based on search results
			filterSidebarTree();

			// Filter continue reading to match search results
			filterContinueReadingBySeries();

			searchStore.update(s => ({ ...s, isSearching: false }));
		} catch (err) {
			console.error('[Home] Search failed:', err);
			searchStore.update(s => ({ ...s, isSearching: false }));
		}
	}

	function filterSidebarTree() {
		if (!searchQuery || !searchResults.length) {
			filteredSeriesTree = seriesTree;
			return;
		}

		// Get unique series names from search results
		const matchingSeriesNames = new Set(searchResults.map(s => s.series_name));

		// Filter tree to only show libraries/folders that contain matching series
		filteredSeriesTree = seriesTree.map(library => {
			const filteredChildren = filterTreeNodesBySearch(library.children || [], matchingSeriesNames);

			if (filteredChildren.length > 0) {
				return {
					...library,
					children: filteredChildren
				};
			}
			return null;
		}).filter(Boolean);
	}

	function filterTreeNodesBySearch(nodes, matchingSeriesNames) {
		return nodes.map(node => {
			// Check if this folder name matches any series name
			const nodeMatches = matchingSeriesNames.has(node.name);

			if (node.children && node.children.length > 0) {
				const filteredChildren = filterTreeNodesBySearch(node.children, matchingSeriesNames);

				if (filteredChildren.length > 0 || nodeMatches) {
					return {
						...node,
						children: filteredChildren
					};
				}
			} else if (nodeMatches) {
				return node;
			}

			return null;
		}).filter(Boolean);
	}

	// Reactively filter continue reading based on displayed series
	$: if (displayedSeries && continueReading) {
		filterContinueReadingBySeries();
	}

	function filterContinueReadingBySeries() {
		if (!continueReading.length) {
			return;
		}

		// If searching, filter by search results
		if (searchQuery && searchResults.length) {
			const searchSeriesNames = new Set(searchResults.map(s => s.series_name).filter(Boolean));
			filteredContinueReading = continueReading.filter(comic =>
				Array.from(searchSeriesNames).some(seriesName =>
					comic.title && seriesName && comic.title.toLowerCase().includes(seriesName.toLowerCase())
				)
			);
			return;
		}

		// If no filter or "all" filter, show everything
		if (!currentFilter || currentFilter.type === 'all') {
			filteredContinueReading = continueReading;
			return;
		}

		// If library filter, filter by library
		if (currentFilter.type === 'library') {
			filteredContinueReading = continueReading.filter(c => c.libraryId === currentFilter.libraryId);
			return;
		}

		// For folder/series filters, filter by displayed series names
		if (displayedSeries.length > 0) {
			const displayedSeriesNames = new Set(displayedSeries.map(s => s.series_name));

			filteredContinueReading = continueReading.filter(comic => {
				// Check if comic title contains any of the displayed series names
				return Array.from(displayedSeriesNames).some(seriesName =>
					comic.title && comic.title.includes(seriesName)
				);
			});
		} else {
			// No displayed series, show nothing for folder filters
			filteredContinueReading = [];
		}
	}
</script>

<svelte:head>
	<title>Home - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<div class="flex flex-1 overflow-hidden">
		<!-- Left Sidebar -->
		<aside class="sidebar">
			<div class="sidebar-header">
				<Library class="w-5 h-5 text-accent-orange" />
				<h3 class="sidebar-title">Libraries</h3>
				{#if currentFilter}
					<button class="reset-button" on:click={resetFilter} title="Show all">
						✕
					</button>
				{/if}
			</div>

			{#if seriesTree.length > 0}
				<div class="tree-container">
					<SeriesTree tree={filteredSeriesTree} on:filter={handleTreeFilter} />
				</div>
			{:else}
				<p class="sidebar-empty">No libraries</p>
			{/if}
		</aside>

		<!-- Main Content -->
		<main class="flex-1 overflow-y-auto">
			<div class="container mx-auto px-4 py-8 max-w-content">
				{#if isLoading}
					<!-- Skeleton loading state for better UX -->
					<section class="section">
						<div class="section-header">
							<h2 class="section-title">
								<BookOpen class="w-6 h-6" />
								Continue Reading
							</h2>
						</div>
						<div class="flex gap-6 overflow-hidden">
							{#each Array(5) as _, i}
								<SkeletonCard width={180} height={270} />
							{/each}
						</div>
					</section>

					<section class="section mt-12">
						<div class="section-header">
							<h2 class="section-title">
								<TrendingUp class="w-6 h-6" />
								Recent Series
							</h2>
						</div>
						<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
							{#each Array(12) as _, i}
								<SkeletonCard width={180} height={270} />
							{/each}
						</div>
					</section>
				{:else if error}
					<div class="error-container">
						<p class="text-red-400">Failed to load: {error}</p>
					</div>
				{:else}
					{#if filteredContinueReading.length > 0}
						<section class="section">
							<div class="section-header">
								<h2 class="section-title">
									<BookOpen class="w-6 h-6" />
									Continue Reading
								</h2>
							</div>
							<HorizontalCarousel itemWidth={180} gap={24}>
								{#each filteredContinueReading as comic}
									<div class="carousel-item">
										<ComicCard {comic} libraryId={comic.libraryId} />
									</div>
								{/each}
							</HorizontalCarousel>
						</section>
					{/if}

					{#if displayedSeries.length > 0}
						<section class="section">
							<div class="section-header">
								<h2 class="section-title">
									<TrendingUp class="w-6 h-6" />
									{#if searchQuery}
										Search Results
									{:else if currentFilter?.type === 'all'}
										All Series
									{:else if currentFilter?.type === 'library'}
										{currentFilter.libraryName}
									{:else if currentFilter?.type === 'folder'}
										{currentFilter.folderName}
									{:else}
										All Series
									{/if}
								</h2>
								<div class="view-controls">
									<button
										class="control-btn"
										class:active={showSizeSlider}
										on:click={() => (showSizeSlider = !showSizeSlider)}
										title="Adjust cover size"
									>
										<SlidersHorizontal class="w-5 h-5" />
									</button>
									<button
										class="control-btn"
										class:active={$preferencesStore.viewMode === 'grid'}
										on:click={() => preferencesStore.setViewMode('grid')}
										title="Grid view"
									>
										<Grid class="w-5 h-5" />
									</button>
									<button
										class="control-btn"
										class:active={$preferencesStore.viewMode === 'list'}
										on:click={() => preferencesStore.setViewMode('list')}
										title="List view"
									>
										<List class="w-5 h-5" />
									</button>
								</div>
							</div>
							{#if showSizeSlider}
								<div class="size-slider-container">
									<label for="cover-size-slider" class="slider-label">
										<span>Cover Size</span>
										<span class="slider-value">{Math.round($preferencesStore.gridCoverSize * 100)}%</span>
									</label>
									<input
										id="cover-size-slider"
										type="range"
										min="0.5"
										max="2"
										step="0.1"
										value={$preferencesStore.gridCoverSize}
										on:input={(e) => preferencesStore.setGridCoverSize(parseFloat(e.target.value))}
										class="size-slider"
									/>
								</div>
							{/if}
							<InfiniteScroll
								hasMore={hasMoreSeries}
								isLoading={isLoadingMore}
								on:loadMore={loadMoreSeries}
							>
								<div class="comics-grid" class:list-view={$preferencesStore.viewMode === 'list'} style="--cover-size-multiplier: {$preferencesStore.gridCoverSize};">
									{#if currentFilter?.type === 'folder'}
										<!-- Show individual comics when folder is selected -->
										{#each displayedSeries[0]?.volumes || [] as comic}
											<a href="/comic/{currentFilter.libraryId}/{comic.id}/read">
												<ComicCard
													comic={{
														id: comic.id,
														title: comic.name,
														hash: comic.hash,
														currentPage: comic.currentPage,
														totalPages: comic.totalPages
													}}
													libraryId={currentFilter.libraryId}
													showProgress={true}
													variant={$preferencesStore.viewMode}
													coverSizeMultiplier={$preferencesStore.gridCoverSize}
												/>
											</a>
										{/each}
									{:else}
										<!-- Show series cards -->
										{#each displayedSeries as series}
											<ComicCard
												comic={{
													id: series.first_comic_id,
													title: series.series_name,
													hash: series.cover_hash,
													itemCount: series.total_issues
												}}
												libraryId={series.libraryId}
												showProgress={false}
												isFolder={true}
												itemCount={series.total_issues}
												isStandalone={series.is_standalone}
												href={series.is_standalone ? `/comic/${series.libraryId}/${series.first_comic_id}` : `/series/${series.libraryId}/${encodeURIComponent(series.series_name)}`}
												variant={$preferencesStore.viewMode}
												coverSizeMultiplier={$preferencesStore.gridCoverSize}
											/>
										{/each}
									{/if}
								</div>
							</InfiniteScroll>
						</section>
					{/if}

					{#if continueReading.length === 0 && allSeries.length === 0}
						<div class="empty-state">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="64"
								height="64"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								class="text-gray-500 mb-4"
							>
								<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
								<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
							</svg>
							<p class="text-gray-400 mb-4">No comics yet!</p>
							<a href="/browse" class="btn-primary">Browse Libraries</a>
						</div>
					{/if}
				{/if}
			</div>
		</main>
	</div>
</div>

<style>
	.sidebar {
		width: 280px;
		background: var(--color-secondary-bg);
		border-right: 1px solid rgba(255, 255, 255, 0.05);
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		overflow-y: auto;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1.5rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
	}

	.sidebar-title {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
		flex: 1;
	}

	.reset-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		padding: 0;
		background: rgba(255, 255, 255, 0.1);
		border: none;
		border-radius: 4px;
		color: var(--color-text);
		cursor: pointer;
		transition: background 0.2s;
		font-size: 14px;
	}

	.reset-button:hover {
		background: rgba(255, 255, 255, 0.2);
	}

	.tree-container {
		flex: 1;
		padding: 0.5rem;
		overflow-y: auto;
	}

	.libraries-nav {
		flex: 1;
		padding: 0.5rem;
		overflow-y: auto;
	}

	.library-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		border-radius: 6px;
		text-decoration: none;
		color: var(--color-text);
		transition: background 0.2s;
		margin-bottom: 0.25rem;
	}

	.library-item:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.library-item-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: rgba(255, 103, 64, 0.1);
		border-radius: 6px;
		color: var(--color-accent);
		flex-shrink: 0;
	}

	.library-item-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.library-item-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.library-item-count {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.sidebar-footer {
		padding: 1rem;
		border-top: 1px solid rgba(255, 255, 255, 0.05);
	}

	.sidebar-link {
		display: block;
		text-align: center;
		padding: 0.5rem;
		color: var(--color-accent);
		text-decoration: none;
		font-size: 0.875rem;
		transition: opacity 0.2s;
	}

	.sidebar-link:hover {
		opacity: 0.8;
	}

	.sidebar-empty {
		padding: 1rem;
		text-align: center;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
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
		to {transform: rotate(360deg);}
	}

	.section {
		margin-bottom: 3rem;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.5rem;
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
	}

	.view-controls {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.control-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		padding: 0;
		background: var(--color-secondary-bg);
		border: 2px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.control-btn:hover {
		background: rgba(255, 255, 255, 0.05);
		border-color: rgba(255, 255, 255, 0.2);
		color: var(--color-text);
	}

	.control-btn.active {
		background: var(--color-accent);
		border-color: var(--color-accent);
		color: white;
	}

	.size-slider-container {
		margin-bottom: 1.5rem;
		padding: 1rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
		border: 1px solid rgba(255, 255, 255, 0.05);
	}

	.slider-label {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
		font-size: 0.875rem;
		color: var(--color-text);
		font-weight: 500;
	}

	.slider-value {
		color: var(--color-accent);
		font-weight: 600;
	}

	.size-slider {
		width: 100%;
		height: 6px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 3px;
		outline: none;
		-webkit-appearance: none;
		appearance: none;
	}

	.size-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 20px;
		height: 20px;
		background: var(--color-accent);
		border-radius: 50%;
		cursor: pointer;
		transition: all 0.2s;
	}

	.size-slider::-webkit-slider-thumb:hover {
		transform: scale(1.2);
		box-shadow: 0 0 0 4px rgba(255, 103, 64, 0.2);
	}

	.size-slider::-moz-range-thumb {
		width: 20px;
		height: 20px;
		background: var(--color-accent);
		border: none;
		border-radius: 50%;
		cursor: pointer;
		transition: all 0.2s;
	}

	.size-slider::-moz-range-thumb:hover {
		transform: scale(1.2);
		box-shadow: 0 0 0 4px rgba(255, 103, 64, 0.2);
	}

	.see-all {
		font-size: 0.875rem;
		color: var(--color-accent);
		text-decoration: none;
		transition: opacity 0.2s;
	}

	.see-all:hover {
		opacity: 0.8;
	}

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(calc(160px * var(--cover-size-multiplier, 1)), 1fr));
		gap: 1.5rem;
	}

	.comics-grid.list-view {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.carousel-item {
		flex-shrink: 0;
		width: 180px;
	}

	.search-container {
		margin-bottom: 2rem;
		position: sticky;
		top: 0;
		z-index: 20;
		background: var(--color-bg);
		padding: 1rem 0;
		margin: -1rem 0 2rem 0;
	}

	.search-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		width: 100%;
		max-width: 600px;
		margin: 0 auto;
	}

	.search-icon {
		position: absolute;
		left: 1rem;
		width: 20px;
		height: 20px;
		color: var(--color-text-secondary);
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		padding: 0.875rem 3rem 0.875rem 3rem;
		background: var(--color-secondary-bg);
		border: 2px solid rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		color: var(--color-text);
		font-size: 1rem;
		transition: all 0.2s;
	}

	.search-input:focus {
		outline: none;
		border-color: var(--color-accent);
		background: rgba(255, 255, 255, 0.05);
	}

	.search-input::placeholder {
		color: var(--color-text-secondary);
	}

	.search-clear {
		position: absolute;
		right: 0.75rem;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		padding: 0;
		background: rgba(255, 255, 255, 0.1);
		border: none;
		border-radius: 50%;
		color: var(--color-text);
		cursor: pointer;
		transition: all 0.2s;
	}

	.search-clear:hover {
		background: rgba(255, 255, 255, 0.2);
		transform: scale(1.1);
	}

	.search-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		margin-top: 0.75rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.spinner-small {
		width: 16px;
		height: 16px;
		border: 2px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@media (max-width: 768px) {
		.sidebar {
			display: none;
		}

		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}

		.section-title {
			font-size: 1.25rem;
		}

		.carousel-item {
			width: 140px;
		}

		.search-input-wrapper {
			max-width: 100%;
		}
	}
</style>
