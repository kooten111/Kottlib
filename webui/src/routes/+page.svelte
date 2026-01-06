<script>
	import { onMount } from "svelte";
	import { browser } from "$app/environment";
	import Navbar from "$components/layout/Navbar.svelte";
	import FolderCard from "$lib/components/library/FolderCard.svelte";
	import ComicCard from "$lib/components/comic/ComicCard.svelte";
	import SeriesTree from "$lib/components/layout/SeriesTree.svelte";
	import InfiniteScroll from "$lib/components/common/InfiniteScroll.svelte";
	import HorizontalCarousel from "$lib/components/common/HorizontalCarousel.svelte";
	import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
	import {
		getLibraries,
		getSeries,
		getContinueReading,
		getContinueReadingAll,
		getLibrariesSeriesTree,
		browseAllLibraries,
	} from "$lib/api/libraries";
	import HomeSidebar from "$lib/components/layout/HomeSidebar.svelte";
	import { getFavorites } from "$lib/api/favorites";
	import { searchComics } from "$lib/api/search";
	import {
		BookOpen,
		Library,
		TrendingUp,
		Grid,
		List,
		SlidersHorizontal,
	} from "lucide-svelte";
	import { navigationContext, currentFilterStore } from "$lib/stores/library";
	import { searchStore } from "$lib/stores/search";
	import { preferencesStore } from "$lib/stores/preferences";

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
	let currentView = "home"; // 'home', 'favorites', 'continue'
	let favorites = [];
	let isLoadingFavorites = false;
	let searchQuery = "";
	let searchResults = [];
	let hasMoreSeries = true;
	let seriesPageSize = 50;
	let filteredSeriesTree = [];
	let lastSearchQuery = "";
	let searchDebounceTimer;
	let showSizeSlider = false;
	let initialFilterRestored = false; // Track if initial filter has been restored
	let initialSortApplied = false; // Track if initial sort has been applied
	let sortBy = $preferencesStore.sortBy || "name";

	// PERFORMANCE OPTIMIZATION: Cache for tree filtering
	let treeFilterCache = new Map();
	let filterDebounceTimer;

	// React to filter store changes - sync currentFilter with store
	$: if (!isLoading && initialFilterRestored) {
		const filterChanged =
			JSON.stringify(currentFilter) !==
			JSON.stringify($currentFilterStore);
		if (filterChanged) {
			if ($currentFilterStore === null && currentFilter !== null) {
				// Filter was cleared externally (e.g., from Navbar)
				currentFilter = null;
				navigationContext.set({ type: "all" });
				displayedSeries = allSeries.slice(0, seriesPageSize);
				hasMoreSeries = allSeries.length > seriesPageSize;
			} else if ($currentFilterStore !== null) {
				restoreFilter($currentFilterStore);
			}
		}
	}

	// Get current library ID from filter
	$: currentLibraryId =
		currentFilter?.type === "library" ? currentFilter.libraryId : null;

	// Sync sortBy from preferences store (library-specific or global)
	$: {
		if (currentLibraryId !== null) {
			// Use library-specific sort if available
			sortBy = preferencesStore.getSortBy(currentLibraryId);
		} else {
			// Use global sort for "all libraries" view
			sortBy = $preferencesStore.sortBy || "name";
		}
	}

	// Apply sort when sortBy changes (after initial load)
	$: if (
		sortBy &&
		!isLoading &&
		initialFilterRestored &&
		initialSortApplied
	) {
		applySorting();
	}

	// React to search store changes with debounce (increased from 300ms to 500ms)
	$: if (!isLoading) {
		const newQuery = $searchStore.query || "";

		if (newQuery !== lastSearchQuery) {
			if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
			searchDebounceTimer = setTimeout(() => {
				lastSearchQuery = newQuery;
				handleSearch(newQuery);
			}, 500); // Increased from 300ms for better performance
		}
	}

	// Update the CSS variable on documentElement when cover size changes
	$: if (browser && $preferencesStore.gridCoverSize) {
		document.documentElement.style.setProperty(
			"--cover-size-multiplier",
			String($preferencesStore.gridCoverSize),
		);
	}

	onMount(async () => {
		await loadHomeData();

		// Restore filter from persistent store if present
		if ($currentFilterStore) {
			await restoreFilter($currentFilterStore);
		}

		// Mark that initial filter restoration is complete
		// This prevents reactive statements from interfering
		initialFilterRestored = true;

		// Apply saved sort preference after initial load is complete
		// This ensures the correct sort order is displayed on page load
		// Use library-specific or global sort based on current filter
		const savedSort = preferencesStore.getSortBy(currentLibraryId);

		if (savedSort && savedSort !== "name") {
			await applySorting();
			initialSortApplied = true; // Mark that initial sort is complete
		} else {
			initialSortApplied = true; // Still mark as applied to allow reactive changes
		}

		// Restore search from URL if present
		if (typeof window !== "undefined") {
			const url = new URL(window.location.href);
			const queryParam = url.searchParams.get("q");
			if (queryParam) {
				searchQuery = queryParam;
				await handleSearch(queryParam);
			}
		}

		// PERFORMANCE OPTIMIZATION: Load remaining libraries in background
		// after initial page is interactive
		if (data?.isPartialLoad && libraries.length > 1) {
			// Small delay to ensure page is interactive first
			setTimeout(() => {
				loadRemainingLibraries();
			}, 100);
		}
	});

	async function loadHomeData() {
		try {
			isLoading = true;
			error = null;

			// Use server-side data if available (SSR), otherwise load client-side
			if (data?.libraries && data?.seriesTree && data?.firstLibrary) {
				libraries = data.libraries;
				seriesTree = data.seriesTree;

				// Use SSR data directly - all data pre-loaded on server
				continueReading = data.firstLibrary.continueReading || [];
				allSeries = data.firstLibrary.folders || [];
				// Only set displayedSeries if there's no filter to restore
				// This prevents showing all series before filter restoration
				if (!$currentFilterStore) {
					displayedSeries = allSeries.slice(0, seriesPageSize);
					hasMoreSeries = allSeries.length > seriesPageSize;
				}

				// Initialize filtered tree
				filteredSeriesTree = seriesTree;
				isLoading = false;
			} else {
				// Fallback to client-side loading if SSR data not available

				await loadClientSide();
			}
		} catch (err) {
			console.error("Failed to load data:", err);
			error = err.message;
			isLoading = false;
		}
	}

	// Client-side loading function as fallback
	async function loadClientSide() {
		try {
			// Load libraries and series tree
			[libraries, seriesTree] = await Promise.all([
				getLibraries(),
				getLibrariesSeriesTree(),
			]);

			if (!libraries || libraries.length === 0) {
				isLoading = false;
				return;
			}

			// Load continue reading
			const continueReadingData = await getContinueReadingAll(50).catch(
				() => [],
			);
			continueReading = continueReadingData.slice(0, 20);

			// Load initial content for "All" view (Server-side paginated)
			const contentStats = await browseAllLibraries(
				sortBy,
				0,
				seriesPageSize,
			);
			const items = (contentStats.items || []).map((i) => ({
				...i,
				libraryId: i.library_id,
			}));

			// Set displayedSeries directly
			displayedSeries = items;
			// For client-side compatibility if needed by other functions,
			// but for "All" view we rely on displayedSeries + Pagination
			allSeries = items;

			// Use total from response to determine if more available
			hasMoreSeries = items.length < (contentStats.total || 0);

			// Initialize filtered tree
			filteredSeriesTree = seriesTree;
			isLoading = false;
		} catch (err) {
			console.error("Failed to load client-side data:", err);
			error = err.message;
			isLoading = false;
		}
	}

	// Load data for a specific library (used when user clicks before background loading completes)
	async function loadLibraryData(libraryId) {
		const lib = libraries.find((l) => l.id === libraryId);
		if (!lib) {
			console.error("[Home] Library not found:", libraryId);
			return;
		}

		try {
			// For client-side sorts, load with 'name' sort from backend, then apply client sort
			// For backend sorts, use the sort parameter directly
			const backendSort =
				sortBy === "shuffle" || sortBy === "recent-read-client"
					? "name"
					: sortBy;

			const [contReading, seriesData] = await Promise.all([
				getContinueReading(libraryId, 50).catch(() => []),
				getSeries(libraryId, backendSort).catch(() => ({ items: [] })),
			]);

			const series = seriesData.items || [];

			// Merge into existing data
			const newContinueReading = contReading.map((c) => ({
				...c,
				libraryId: libraryId,
			}));
			const newSeries = series.map((s) => ({
				...s,
				libraryId: libraryId,
			}));

			// Remove any existing data for this library (in case of reload)
			continueReading = continueReading.filter(
				(c) => c.libraryId !== libraryId,
			);
			allSeries = allSeries.filter((s) => s.libraryId !== libraryId);

			// Add new data
			continueReading = [...continueReading, ...newContinueReading];
			allSeries = [...allSeries, ...newSeries];

			// Apply client-side sort if needed
			if (sortBy === "shuffle" || sortBy === "recent-read-client") {
				await applySorting();
			} else {
				// Update display with backend-sorted data
				updateDisplayedSeries();
			}
		} catch (err) {
			console.error(`[Home] Failed to load library ${libraryId}:`, err);
		}
	}

	// PERFORMANCE OPTIMIZATION: Load remaining libraries in background
	async function loadRemainingLibraries() {
		const remainingLibs = libraries.slice(1);

		// Load libraries one at a time to avoid overwhelming the browser
		for (const lib of remainingLibs) {
			try {
				const [contReading, seriesData] = await Promise.all([
					getContinueReading(lib.id, 50).catch(() => []),
					getSeries(lib.id, sortBy).catch(() => ({ items: [] })),
				]);

				const series = seriesData.items || [];

				// Merge into existing data
				const newContinueReading = contReading.map((c) => ({
					...c,
					libraryId: lib.id,
				}));
				const newSeries = series.map((s) => ({
					...s,
					libraryId: lib.id,
				}));

				continueReading = [...continueReading, ...newContinueReading];
				allSeries = [...allSeries, ...newSeries];

				// Update display if we're showing all libraries
				if (!currentFilter || currentFilter.type === "all") {
					displayedSeries = allSeries.slice(
						0,
						Math.max(displayedSeries.length, seriesPageSize),
					);
					hasMoreSeries = allSeries.length > displayedSeries.length;
				} else if (
					currentFilter.type === "library" &&
					currentFilter.libraryId === lib.id
				) {
					// We just loaded the library we are currently filtering by!

					// Apply sorting to ensure correct order is displayed
					await applySorting();
				}
			} catch (err) {
				console.error(`[Home] Failed to load library ${lib.id}:`, err);
			}
		}

		// Reapply sorting after all libraries are loaded to ensure correct order
		if (sortBy && sortBy !== "name") {
			await applySorting();
		}
	}

	// ... (handleTreeFilter etc unchanged) ...

	// Since I cannot skip code chunks easily in replace_file_content when using large range,
	// I will just implement the unpacking for reloadWithBackendSort too in next block if needed.
	// But `reloadWithBackendSort` is further down.
	// I will include it if it falls in range.
	// Range 198 to 378 covers loadClientSide, loadLibraryData, loadRemainingLibraries.
	// reloadWithBackendSort is at 583.
	// I will check if I can use multi_replace.

	async function handleTreeFilter(event) {
		const { type, libraryId, folderId, folderName, comicId, libraryName } =
			event.detail;

		currentFilter = event.detail;
		// Persist filter to localStorage
		currentFilterStore.set(event.detail);

		// Update navigation context for continue reading filtering
		if (type === "all") {
			navigationContext.set({ type: "all", seriesNames: [] });
			// Show all series from all libraries
			displayedSeries = allSeries.slice(0, seriesPageSize);
			hasMoreSeries = allSeries.length > seriesPageSize;
		} else if (type === "library") {
			const librarySeries = allSeries.filter(
				(s) => s.libraryId === libraryId,
			);
			navigationContext.set({
				type: "library",
				libraryId,
				libraryName,
				seriesNames: librarySeries.map((s) => s.series_name),
			});
			// Filter to show only series from selected library with pagination
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;

			// If the library has no series loaded yet (or empty), load it immediately
			// This handles the race condition where user clicks a library before background loading completes
			if (librarySeries.length === 0) {
				await loadLibraryData(libraryId);
			}
		} else if (type === "folder") {
			// Navigate to series view page
			// The folder name corresponds to the series name
			window.location.href = `/series/${libraryId}/${encodeURIComponent(folderName)}`;
			return;
		} else if (type === "comic") {
			// Navigate to comic reader
			window.location.href = `/comic/${libraryId}/${comicId}/read`;
			return;
		}

		// Reload favorites if in favorites view
		if (currentView === "favorites") {
			await loadFavorites();
		}
	}

	async function handleViewChange(event) {
		const view = event.detail;
		currentView = view;

		if (view === "favorites") {
			await loadFavorites();
		}
	}

	async function loadFavorites() {
		isLoadingFavorites = true;
		try {
			if (currentFilter?.type === "library") {
				const favs = await getFavorites(currentFilter.libraryId);
				favorites = favs.map((f) => ({
					...f,
					libraryId: currentFilter.libraryId,
				}));
			} else {
				// Load from all libraries
				const favResults = await Promise.all(
					libraries.map((lib) =>
						getFavorites(lib.id)
							.then((comics) =>
								comics.map((c) => ({
									...c,
									libraryId: lib.id,
								})),
							)
							.catch(() => []),
					),
				);
				favorites = favResults.flat();
			}
			// Sort favorites by date added by default
			favorites.sort(
				(a, b) => (b.favoriteDate || 0) - (a.favoriteDate || 0),
			);
		} catch (err) {
			console.error("Failed to load favorites:", err);
		} finally {
			isLoadingFavorites = false;
		}
	}

	function resetFilter() {
		currentFilter = null;
		// Clear persisted filter
		currentFilterStore.set(null);
		navigationContext.set({ type: "all" });
		displayedSeries = allSeries.slice(0, seriesPageSize);
		hasMoreSeries = allSeries.length > seriesPageSize;
	}

	async function restoreFilter(filter) {
		if (!filter) return;

		currentFilter = filter;

		// Apply the filter based on its type
		if (filter.type === "all") {
			navigationContext.set({ type: "all", seriesNames: [] });
			displayedSeries = allSeries.slice(0, seriesPageSize);
			hasMoreSeries = allSeries.length > seriesPageSize;
		} else if (filter.type === "library") {
			const librarySeries = allSeries.filter(
				(s) => s.libraryId === filter.libraryId,
			);
			navigationContext.set({
				type: "library",
				libraryId: filter.libraryId,
				libraryName: filter.libraryName,
				seriesNames: librarySeries.map((s) => s.series_name),
			});
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;
		} else if (filter.type === "folder") {
			const librarySeries = allSeries.filter(
				(s) =>
					s.libraryId === filter.libraryId &&
					s.series_name === filter.folderName,
			);
			navigationContext.set({
				type: "folder",
				libraryId: filter.libraryId,
				folderName: filter.folderName,
				seriesNames: librarySeries.map((s) => s.series_name),
			});
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;
		}
	}

	async function applySorting() {
		if (!allSeries || allSeries.length === 0) {
			return;
		}

		let sortedSeries;

		switch (sortBy) {
			case "name":
			case "recent":
			case "updated":
			case "progress":
			case "recent-read":
				// Backend sorts - reload data with sort parameter

				await reloadWithBackendSort(sortBy);
				return;

			case "recent-read-client":
				// Client-side: Sort by most recent last_read_at (fallback, not normally used)
				sortedSeries = [...allSeries].sort((a, b) => {
					const aMaxTime = getMaxLastReadTime(a.volumes);
					const bMaxTime = getMaxLastReadTime(b.volumes);

					// Unread series go to end, sorted by first_comic_id
					if (aMaxTime === 0 && bMaxTime === 0) {
						return b.first_comic_id - a.first_comic_id;
					}
					if (aMaxTime === 0) return 1;
					if (bMaxTime === 0) return -1;

					return bMaxTime - aMaxTime; // Most recent first
				});
				break;

			case "shuffle":
				// Fisher-Yates shuffle
				sortedSeries = [...allSeries];
				for (let i = sortedSeries.length - 1; i > 0; i--) {
					const j = Math.floor(Math.random() * (i + 1));
					[sortedSeries[i], sortedSeries[j]] = [
						sortedSeries[j],
						sortedSeries[i],
					];
				}
				break;

			default:
				return;
		}

		allSeries = sortedSeries;
		updateDisplayedSeries();
	}

	function getMaxLastReadTime(volumes) {
		if (!volumes || volumes.length === 0) return 0;
		return Math.max(...volumes.map((v) => v.last_read_at || 0));
	}

	async function reloadWithBackendSort(sortType) {
		try {
			// IF viewing All Libraries (Unified Browse)
			if (!currentLibraryId) {
				const contentStats = await browseAllLibraries(
					sortType,
					0,
					seriesPageSize,
				);
				const items = (contentStats.items || []).map((i) => ({
					...i,
					libraryId: i.library_id,
				}));
				displayedSeries = items;
				// allSeries isn't really used for Unified Browse, but we set it for safety if anything relies on non-empty
				allSeries = items;
				hasMoreSeries = items.length < (contentStats.total || 0);
				return;
			}

			// If a library is selected, only fetch data for that library
			const librariesToFetch = libraries.filter(
				(lib) => lib.id === currentLibraryId,
			);

			const allSeriesResults = await Promise.all(
				librariesToFetch.map(async (lib) => {
					try {
						const seriesData = await getSeries(lib.id, sortType);
						const seriesItems = seriesData.items || [];
						return seriesItems.map((s) => ({
							...s,
							libraryId: lib.id,
						}));
					} catch (err) {
						console.error(
							`Failed to fetch series for library ${lib.id}:`,
							err,
						);
						return [];
					}
				}),
			);

			// Flatten results since we only fetched one library
			const flatSeries = allSeriesResults.flat();
			allSeries = flatSeries;

			updateDisplayedSeries();
		} catch (err) {
			console.error("[Home] Failed to reload with sort:", err);
		}
	}

	function updateDisplayedSeries() {
		if (currentFilter?.type === "library") {
			const librarySeries = allSeries.filter(
				(s) => s.libraryId === currentFilter.libraryId,
			);
			displayedSeries = librarySeries.slice(0, seriesPageSize);
			hasMoreSeries = librarySeries.length > seriesPageSize;
		} else {
			displayedSeries = allSeries.slice(0, seriesPageSize);
			hasMoreSeries = allSeries.length > seriesPageSize;
		}
	}

	async function loadMoreSeries() {
		if (isLoadingMore || !hasMoreSeries) {
			return;
		}

		isLoadingMore = true;

		// Use requestAnimationFrame to ensure smooth UI updates
		await new Promise((resolve) => requestAnimationFrame(resolve));

		// GLOBAL BROWSE PAGINATION
		if (!currentFilter || currentFilter.type === "all") {
			try {
				const offset = displayedSeries.length;
				const contentStats = await browseAllLibraries(
					sortBy,
					offset,
					seriesPageSize,
				);
				const newItems = (contentStats.items || []).map((i) => ({
					...i,
					libraryId: i.library_id,
				}));

				if (newItems.length > 0) {
					displayedSeries = [...displayedSeries, ...newItems];
					// Check if we have more based on total
					hasMoreSeries =
						displayedSeries.length < (contentStats.total || 0);
				} else {
					hasMoreSeries = false;
				}
			} catch (err) {
				console.error("Failed to load more items:", err);
			} finally {
				isLoadingMore = false;
			}
			return;
		}

		// OLD LOGIC (for specific libraries if they still load fully, or filtered views)
		// Note: Library view loads `loadLibraryData` which populates `allSeries` filtered?
		// Actually `loadLibraryData` loads ALL series for that library.
		// So for "Library" filter, we still have client-side pagination from `allSeries`.

		const currentLength = displayedSeries.length;
		// Determine the base source based on current filters
		let baseSource;
		if (searchQuery) {
			baseSource = searchResults;
		} else if (currentFilter?.type === "library") {
			baseSource = allSeries.filter(
				(s) => s.libraryId === currentFilter.libraryId,
			);
		} else {
			// Fallback
			baseSource = allSeries;
		}

		const nextBatch = baseSource.slice(
			currentLength,
			currentLength + seriesPageSize,
		);

		if (nextBatch.length > 0) {
			displayedSeries = [...displayedSeries, ...nextBatch];
			hasMoreSeries = displayedSeries.length < baseSource.length;
		} else {
			hasMoreSeries = false;
		}

		// Small delay to prevent rapid fire loading
		await new Promise((resolve) => setTimeout(resolve, 100));
		isLoadingMore = false;
	}

	async function handleSearch(query) {
		const trimmedQuery = query?.trim() || "";
		searchQuery = trimmedQuery;

		// Update URL without adding to history
		if (typeof window !== "undefined") {
			const url = new URL(window.location.href);
			if (trimmedQuery) {
				url.searchParams.set("q", trimmedQuery);
			} else {
				url.searchParams.delete("q");
			}
			window.history.replaceState({}, "", url);
		}

		// Clear search if query is empty (allow 1 character searches)
		if (!trimmedQuery) {
			// Clear search - show original filtered data
			displayedSeries =
				currentFilter?.type === "library"
					? allSeries
							.filter(
								(s) => s.libraryId === currentFilter.libraryId,
							)
							.slice(0, seriesPageSize)
					: allSeries.slice(0, seriesPageSize);
			hasMoreSeries =
				(currentFilter?.type === "library"
					? allSeries.filter(
							(s) => s.libraryId === currentFilter.libraryId,
						)
					: allSeries
				).length > seriesPageSize;
			searchResults = [];
			filteredSeriesTree = seriesTree; // Reset tree filter
			searchStore.update((s) => ({ ...s, isSearching: false }));
			filterContinueReadingBySeries();
			return;
		}

		searchStore.update((s) => ({ ...s, isSearching: true }));

		try {
			// Filter allSeries by series name instead of API search
			const lowerQuery = trimmedQuery.toLowerCase();

			searchResults = allSeries.filter(
				(series) =>
					series.series_name &&
					series.series_name.toLowerCase().includes(lowerQuery),
			);

			// Filter based on current library selection
			let filteredResults = searchResults;
			if (currentFilter?.type === "library") {
				filteredResults = searchResults.filter(
					(s) => s.libraryId === currentFilter.libraryId,
				);
			}

			displayedSeries = filteredResults.slice(0, seriesPageSize);
			hasMoreSeries = filteredResults.length > seriesPageSize;

			// Filter sidebar tree based on search results
			filterSidebarTree();

			// Filter continue reading to match search results
			filterContinueReadingBySeries();

			searchStore.update((s) => ({ ...s, isSearching: false }));
		} catch (err) {
			console.error("[Home] Search failed:", err);
			searchStore.update((s) => ({ ...s, isSearching: false }));
		}
	}

	// PERFORMANCE OPTIMIZATION: Debounced and cached tree filtering
	function filterSidebarTree() {
		// Debounce to avoid excessive filtering during rapid searches
		clearTimeout(filterDebounceTimer);
		filterDebounceTimer = setTimeout(() => {
			performTreeFiltering();
		}, 50);
	}

	function performTreeFiltering() {
		if (!searchQuery || !searchResults.length) {
			filteredSeriesTree = seriesTree;
			treeFilterCache.clear();
			return;
		}

		// Create cache key from search query and result count
		const cacheKey = `${searchQuery}_${searchResults.length}`;

		// Check cache first
		if (treeFilterCache.has(cacheKey)) {
			filteredSeriesTree = treeFilterCache.get(cacheKey);
			return;
		}

		// Use Set for O(1) lookups instead of array operations
		const matchingSeriesNames = new Set(
			searchResults.map((s) => s.series_name),
		);

		// Filter tree to only show libraries/folders that contain matching series
		const filtered = seriesTree
			.map((library) => {
				const filteredChildren = filterTreeNodesBySearch(
					library.children || [],
					matchingSeriesNames,
				);

				if (filteredChildren.length > 0) {
					return {
						...library,
						children: filteredChildren,
					};
				}
				return null;
			})
			.filter(Boolean);

		// Cache the result (limit cache size to prevent memory issues)
		if (treeFilterCache.size > 20) {
			// Remove oldest entry
			const firstKey = treeFilterCache.keys().next().value;
			treeFilterCache.delete(firstKey);
		}
		treeFilterCache.set(cacheKey, filtered);

		filteredSeriesTree = filtered;
	}

	function filterTreeNodesBySearch(nodes, matchingSeriesNames) {
		return nodes
			.map((node) => {
				// Check if this folder name matches any series name
				const nodeMatches = matchingSeriesNames.has(node.name);

				if (node.children && node.children.length > 0) {
					const filteredChildren = filterTreeNodesBySearch(
						node.children,
						matchingSeriesNames,
					);

					if (filteredChildren.length > 0 || nodeMatches) {
						return {
							...node,
							children: filteredChildren,
						};
					}
				} else if (nodeMatches) {
					return node;
				}

				return null;
			})
			.filter(Boolean);
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
			const searchSeriesNames = new Set(
				searchResults.map((s) => s.series_name).filter(Boolean),
			);
			filteredContinueReading = continueReading.filter((comic) =>
				Array.from(searchSeriesNames).some(
					(seriesName) =>
						comic.title &&
						seriesName &&
						comic.title
							.toLowerCase()
							.includes(seriesName.toLowerCase()),
				),
			);
			return;
		}

		// If no filter or "all" filter, show everything
		if (!currentFilter || currentFilter.type === "all") {
			filteredContinueReading = continueReading;
			return;
		}

		// If library filter, filter by library
		if (currentFilter.type === "library") {
			filteredContinueReading = continueReading.filter(
				(c) => c.libraryId === currentFilter.libraryId,
			);
			return;
		}

		// For folder/series filters, filter by displayed series names
		if (displayedSeries.length > 0) {
			const displayedSeriesNames = new Set(
				displayedSeries.map((s) => s.series_name),
			);

			filteredContinueReading = continueReading.filter((comic) => {
				// Check if comic title contains any of the displayed series names
				return Array.from(displayedSeriesNames).some(
					(seriesName) =>
						comic.title && comic.title.includes(seriesName),
				);
			});
		} else {
			// No displayed series, show nothing for folder filters
			filteredContinueReading = [];
		}
	}
</script>

<svelte:head>
	<title>Home - Kottlib</title>
</svelte:head>

<div class="flex flex-col h-screen overflow-hidden">
	<Navbar />

	<div class="flex flex-1 overflow-hidden">
		<!-- Left Sidebar -->
		<HomeSidebar
			{libraries}
			{seriesTree}
			{currentFilter}
			{currentView}
			on:filter={handleTreeFilter}
			on:viewChange={handleViewChange}
		/>

		<!-- Main Content -->
		<main class="flex-1 overflow-y-auto">
			<div class="container mx-auto px-4 py-8 max-w-content">
				{#if currentView === "favorites"}
					<div class="mb-8">
						<h2
							class="text-2xl font-bold mb-6 flex items-center gap-2"
						>
							<Heart class="w-6 h-6 text-accent-orange" />
							Favorites
						</h2>
						{#if isLoadingFavorites}
							<div class="flex justify-center py-12">
								<div
									class="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-orange"
								></div>
							</div>
						{:else if favorites.length > 0}
							<div
								class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6"
							>
								{#each favorites as comic}
									<ComicCard
										{comic}
										libraryId={comic.libraryId}
									/>
								{/each}
							</div>
						{:else}
							<div class="text-center py-12 text-gray-500">
								<Heart
									class="w-12 h-12 mx-auto mb-4 opacity-50"
								/>
								<p>No favorites found</p>
							</div>
						{/if}
					</div>
				{:else if currentView === "continue"}
					<div class="mb-8">
						<h2
							class="text-2xl font-bold mb-6 flex items-center gap-2"
						>
							<BookOpen class="w-6 h-6 text-accent-orange" />
							Continue Reading
						</h2>
						{#if filteredContinueReading.length > 0}
							<div
								class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6"
							>
								{#each filteredContinueReading as comic}
									<ComicCard
										{comic}
										libraryId={comic.libraryId}
									/>
								{/each}
							</div>
						{:else}
							<div class="text-center py-12 text-gray-500">
								<BookOpen
									class="w-12 h-12 mx-auto mb-4 opacity-50"
								/>
								<p>No continue reading items found</p>
							</div>
						{/if}
					</div>
				{:else}
					<!-- HOME VIEW -->
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
							<div
								class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6"
							>
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
											<ComicCard
												{comic}
												libraryId={comic.libraryId}
											/>
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
										{:else if currentFilter?.type === "all"}
											All Series
										{:else if currentFilter?.type === "library"}
											{currentFilter.libraryName}
										{:else if currentFilter?.type === "folder"}
											{currentFilter.folderName}
										{:else}
											All Series
										{/if}
									</h2>
									<div class="view-controls">
										<select
											bind:value={sortBy}
											on:change={async (e) => {
												const newSort = e.target.value;

												// Save library-specific preference if a library is selected
												preferencesStore.setSortBy(
													newSort,
													currentLibraryId,
												);
												// Explicitly apply the sort (don't rely solely on reactive statement)
												await applySorting();
											}}
											class="control-select"
										>
											<option value="name"
												>Alphabetical</option
											>
											<option value="updated"
												>Last Updated</option
											>
											<option value="recent"
												>Date Added</option
											>
											<option value="recent-read"
												>Recently Read</option
											>
											<option value="progress"
												>% Complete</option
											>
											<option value="shuffle"
												>Shuffle</option
											>
										</select>
										<button
											class="control-btn"
											class:active={showSizeSlider}
											on:click={() =>
												(showSizeSlider =
													!showSizeSlider)}
											title="Adjust cover size"
										>
											<SlidersHorizontal
												class="w-5 h-5"
											/>
										</button>
										<button
											class="control-btn"
											class:active={$preferencesStore.viewMode ===
												"grid"}
											on:click={() =>
												preferencesStore.setViewMode(
													"grid",
												)}
											title="Grid view"
										>
											<Grid class="w-5 h-5" />
										</button>
										<button
											class="control-btn"
											class:active={$preferencesStore.viewMode ===
												"list"}
											on:click={() =>
												preferencesStore.setViewMode(
													"list",
												)}
											title="List view"
										>
											<List class="w-5 h-5" />
										</button>
									</div>
								</div>
								{#if showSizeSlider}
									<div class="size-slider-container">
										<label
											for="cover-size-slider"
											class="slider-label"
										>
											<span>Cover Size</span>
											<span class="slider-value"
												>{Math.round(
													$preferencesStore.gridCoverSize *
														100,
												)}%</span
											>
										</label>
										<input
											id="cover-size-slider"
											type="range"
											min="0.5"
											max="2"
											step="0.1"
											value={$preferencesStore.gridCoverSize}
											on:input={(e) =>
												preferencesStore.setGridCoverSize(
													parseFloat(e.target.value),
												)}
											class="size-slider"
										/>
									</div>
								{/if}
								<InfiniteScroll
									hasMore={hasMoreSeries}
									isLoading={isLoadingMore}
									on:loadMore={loadMoreSeries}
								>
									<div
										class="comics-grid"
										class:list-view={$preferencesStore.viewMode ===
											"list"}
										style={browser
											? `--cover-size-multiplier: ${$preferencesStore.gridCoverSize};`
											: ""}
									>
										{#if currentFilter?.type === "folder"}
											<!-- Show individual comics when folder is selected -->
											{#each displayedSeries[0]?.volumes || [] as comic}
												<a
													href="/comic/{currentFilter.libraryId}/{comic.id}/read"
												>
													<ComicCard
														comic={{
															id: comic.id,
															title: comic.name,
															hash: comic.hash,
															currentPage:
																comic.currentPage,
															totalPages:
																comic.totalPages,
														}}
														libraryId={currentFilter.libraryId}
														showProgress={true}
														variant={$preferencesStore.viewMode}
													/>
												</a>
											{/each}
										{:else}
											<!-- Show series cards -->
											{#each displayedSeries as series (series.id)}
												{#if series.type === "collection" || series.type === "series"}
													<FolderCard
														item={series}
														libraryId={series.libraryId}
														on:click={() => {
															const path =
																encodeURIComponent(
																	series.name,
																);
															window.location.href = `/library/${series.libraryId}/browse/${path}`;
														}}
													/>
												{:else if series.type === "comic"}
													<ComicCard
														comic={{
															...series,
															id: series.id,
															// Ensure required props for ComicCard
															title:
																series.title ||
																series.name,
															hash: series.cover_hash,
															currentPage:
																series.current_page,
															totalPages:
																series.num_pages,
														}}
														libraryId={series.libraryId}
														showProgress={true}
														isFolder={false}
														isStandalone={true}
														variant={$preferencesStore.viewMode}
														href={`/comic/${series.libraryId}/${series.id}/read`}
													/>
												{:else}
													<ComicCard
														comic={{
															id: series.first_comic_id,
															name: series.name,
															series_name:
																series.series_name,
															title: series.title,
															hash: series.cover_hash,
															itemCount:
																series.total_issues,
															writer: series.writer,
															artist: series.artist,
															publisher:
																series.publisher,
															year: series.year,
															genre: series.genre,
															synopsis:
																series.synopsis,
														}}
														libraryId={series.libraryId}
														showProgress={false}
														isFolder={true}
														itemCount={series.total_issues}
														isStandalone={series.is_standalone}
														cardHref={series.is_standalone
															? `/comic/${series.libraryId}/${series.first_comic_id}`
															: `/library/${series.libraryId}/browse/${encodeURIComponent(series.series_name || series.name)}`}
														variant={$preferencesStore.viewMode}
													/>
												{/if}
											{/each}
										{/if}
									</div>
								</InfiniteScroll>
							</section>
						{/if}
					{/if}
				{/if}
				<!-- End of currentView check -->
			</div>
		</main>
	</div>
</div>

<style>
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

	.control-select {
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		background: var(--color-secondary-bg);
		border: 2px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		color: var(--color-text);
		cursor: pointer;
		transition: all 0.2s;
		min-width: 150px;
	}

	.control-select:hover {
		background: rgba(255, 255, 255, 0.05);
		border-color: rgba(255, 255, 255, 0.2);
	}

	.control-select:focus {
		outline: none;
		border-color: var(--color-accent);
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

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(
			auto-fill,
			minmax(calc(160px * var(--cover-size-multiplier, 1)), 1fr)
		);
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

	@media (max-width: 768px) {
		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
			gap: 0.75rem;
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

		/* Improve touch targets for mobile */
		.control-btn {
			min-height: 44px;
			min-width: 44px;
		}

		/* Better spacing on mobile */
		.section {
			margin-bottom: 2rem;
		}

		.section-header {
			margin-bottom: 1rem;
		}
	}

	@media (max-width: 480px) {
		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
			gap: 0.5rem;
		}
	}
</style>
