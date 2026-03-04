<script>
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { browser } from "$app/environment";
    import Navbar from "$lib/components/layout/Navbar.svelte";
    import HomeSidebar from "$lib/components/layout/HomeSidebar.svelte";
    import DetailHeader from "$lib/components/common/DetailHeader.svelte";
    import FolderCard from "$lib/components/library/FolderCard.svelte";
    import ComicCard from "$lib/components/comic/ComicCard.svelte";
    import MetadataDisplay from "$lib/components/comic/MetadataDisplay.svelte";
    import Breadcrumbs from "$lib/components/common/Breadcrumbs.svelte";
    import HorizontalCarousel from "$lib/components/common/HorizontalCarousel.svelte";
    import SeriesInfoPanel from "$lib/components/series/SeriesInfoPanel.svelte";
    import {
        FolderOpen,
        BookOpen,
        Layers,
        Grid,
        List,
        Loader2,
        SlidersHorizontal,
    } from "lucide-svelte";
    import { browseLibrary, browseAllLibraries, getContinueReading } from "$lib/api/libraries";
    import { preferencesStore } from "$lib/stores/preferences";
    import { scanSeries, applySeriesMetadata } from "$lib/api/scanners";

    import { X, ExternalLink, Check } from "lucide-svelte";

    export let data;

    // Determine if we're in "all libraries" mode
    $: isAllLibraries = data.libraryId === 'all';

    $: browseData = data.browseData;
    $: libraryId = data.libraryId;
    $: currentPath = data.currentPath;
    $: error = data.error;

    // Sidebar data
    $: libraries = data.libraries || [];
    $: seriesTree = data.seriesTree || [];

    // Continue reading (server-loaded for all-libraries, client-fetched for single library)
    $: serverContinueReading = data.continueReading || [];
    let clientContinueReading = [];
    let loadingContinueReading = false;
    $: continueReadingItems = isAllLibraries ? serverContinueReading : clientContinueReading;

    $: folder = browseData?.folder;
    $: comic = browseData?.comic;
    $: isComicView = !isAllLibraries && browseData?.is_comic_view;
    $: library = browseData?.library;
    $: breadcrumbs = browseData?.breadcrumbs || [];
    // Unified Items List (Pagination Support)
    $: initialItems = browseData?.items || [];
    $: totalItems = browseData?.total || 0;

    // Local state for items to support appending (infinite scroll)
    let items = [];
    let currentOffset = 0;
    let limit = 50;
    let loadingMore = false;
    let prefetching = false;
    let prefetchedPage = null;
    let prefetchedOffset = null;

    // Series scanner state
    let isScanningSeries = false;
    let seriesScanError = null;
    let scanCandidates = [];
    let showCandidateModal = false;
    let isApplyingCandidate = false;
    let selectedCandidateIndex = -1;

    // Per-volume metadata mode (for FILE-level scanners like nhentai)
    $: perVolumeMetadata = browseData?.per_volume_metadata || false;
    $: firstComicMetadata = browseData?.first_comic_metadata || null;

    // Selected comic for info panel in per-volume mode
    let selectedComic = null;
    let currentFolderPath = null; // Track current folder to reset selection on navigation

    // Initialize/reset selectedComic when browseData changes
    $: if (browseData) {
        const folderPath = currentPath || "";
        // Reset selection when navigating to a different folder
        if (folderPath !== currentFolderPath) {
            currentFolderPath = folderPath;
            selectedComic = null;
        }
        // Initialize to first comic if in per-volume mode and no selection yet
        if (perVolumeMetadata && firstComicMetadata && !selectedComic) {
            selectedComic = firstComicMetadata;
        }
        // Reset when not in per-volume mode
        if (!perVolumeMetadata) {
            selectedComic = null;
        }
    }

    async function handleScanSeries(overwrite = false) {
        if (!folder || !folder.name) return;

        try {
            isScanningSeries = true;
            seriesScanError = null;
            scanCandidates = [];

            const result = await scanSeries(libraryId, folder.name, overwrite);

            if (result.success) {
                // Reload the page to show updated metadata
                window.location.reload();
            } else if (result.candidates && result.candidates.length > 0) {
                // Show candidates for manual selection
                scanCandidates = result.candidates;
                showCandidateModal = true;
            } else {
                seriesScanError = result.error || "No matches found";
            }
        } catch (err) {
            seriesScanError = err.message;
        } finally {
            isScanningSeries = false;
        }
    }

    async function handleSelectCandidate(candidate, index) {
        if (!folder || !folder.name) return;

        try {
            isApplyingCandidate = true;
            selectedCandidateIndex = index;

            const result = await applySeriesMetadata(
                libraryId,
                folder.name,
                candidate,
                false,
            );

            if (result.success) {
                showCandidateModal = false;
                scanCandidates = [];
                window.location.reload();
            } else {
                seriesScanError = result.error || "Failed to apply metadata";
            }
        } catch (err) {
            seriesScanError = err.message;
        } finally {
            isApplyingCandidate = false;
            selectedCandidateIndex = -1;
        }
    }

    function closeCandidateModal() {
        showCandidateModal = false;
        scanCandidates = [];
    }

    // When browseData changes (navigation), reset items and fetch continue reading
    $: if (browseData) {
        items = initialItems;
        currentOffset = browseData.offset || 0;
        limit = browseData.limit || 50;
        prefetchedPage = null;
        prefetchedOffset = null;
        if (browser) {
            queueMicrotask(() => {
                prefetchNextPage();
            });
        }
        // Only fetch continue reading client-side for single-library mode
        if (browser && !isAllLibraries) {
            fetchContinueReading();
        }
    }

    async function fetchContinueReading() {
        // Only fetch reading list at root of library
        if (currentPath === "" && !isAllLibraries) {
            loadingContinueReading = true;
            try {
                clientContinueReading = await getContinueReading(libraryId);
            } catch (e) {
                console.error("Failed to fetch continue reading:", e);
            } finally {
                loadingContinueReading = false;
            }
        } else {
            clientContinueReading = [];
        }
    }

    $: hasMore = items.length < totalItems;
    $: hasContent = items.length > 0;

    // Construct currentFilter for sidebar highlighting
    $: currentFilter = isAllLibraries
        ? { type: "all" }
        : folder
        ? {
              type: "folder",
              libraryId,
              folderId: folder.id,
              folderName: folder.name,
          }
        : { type: "library", libraryId, libraryName: library?.name };

    // Initial setup for preferences
    // Derive sortBy from URL or fall back to store
    $: sortBy = isAllLibraries
        ? ($page.url.searchParams.get("sort") ||
           $preferencesStore.sortBy ||
           "name")
        : ($page.url.searchParams.get("sort") ||
           $preferencesStore.librarySortBy?.[libraryId] ||
           "name");

    let showSizeSlider = false;
    let showSortDropdown = false;
    // We don't need local randomSeed state if we use URL
    // But we might want to know if we just generated one?
    // Actually, we can just read seed from URL too
    $: randomSeed = $page.url.searchParams.get("seed");

    const sortOptions = [
        { value: "name", label: "Name" },
        { value: "created", label: "Date Added" },
        { value: "updated", label: "Last Updated" },
        { value: "progress", label: "Progress" },
        { value: "random", label: "Shuffle" },
    ];

    // Reactive: Check sort when libraryId changes (handles navigation between libraries)
    $: if (browser && libraryId) {
        const urlSort = $page.url.searchParams.get("sort");
        const storeSort = isAllLibraries
            ? $preferencesStore.sortBy
            : $preferencesStore.librarySortBy?.[libraryId];

        // Only apply if URL is missing sort but store has one
        if (!urlSort && storeSort && storeSort !== "name") {
            const url = new URL(window.location.href);
            url.searchParams.set("sort", storeSort);

            if (storeSort === "random") {
                url.searchParams.set("seed", String(Date.now()));
            }

            goto(url.toString(), { replaceState: true });
        }
    }

    // Function to apply sorting - now just updates URL
    async function applySorting(newSort) {
        // Save preference (global for all-libraries, per-library otherwise)
        if (newSort) {
            if (isAllLibraries) {
                preferencesStore.setSortBy(newSort);
            } else {
                preferencesStore.setSortBy(newSort, libraryId);
            }
        }

        const targetSort = newSort || sortBy;
        const url = new URL($page.url);
        url.searchParams.set("sort", targetSort);

        // Handle Random Seed
        if (targetSort === "random") {
            // Always generate new seed on explicit user action (applySorting)
            // If we just loaded the page with an existing seed, we don't call this function unless user clicks something
            url.searchParams.set("seed", String(Date.now()));
        } else {
            url.searchParams.delete("seed");
        }

        // Reset offset? SvelteKit load will reset data, but our client-side 'loadMore' logic needs reset
        // Actually, if we navigate, 'items' reactive statement will handle it.
        // We just navigate.
        goto(url.toString(), { noScroll: true });
        showSortDropdown = false;
    }

    // Watch for sort changes (only if triggered by user, not initial load which is handled by data)
    // Actually, simple way: Just call applySorting when sortBy changes via UI

    let viewMode = $preferencesStore.viewMode; // 'grid' | 'list'
    $: if (viewMode !== $preferencesStore.viewMode) {
        preferencesStore.setViewMode(viewMode);
    }
    // Sync back if store changes (e.g. from other tab or component)
    $: viewMode = $preferencesStore.viewMode;

    // Determine if we should show the two-column series layout (defined early for gridCoverSize default)
    $: isSeriesView = !isAllLibraries && !!folder && currentPath !== "" && !isComicView;

    // Reactive cover size that checks folder-specific preference first, then falls back to global
    $: gridCoverSize = (() => {
        if (isAllLibraries) {
            return $preferencesStore.gridCoverSize || 1.4;
        }
        const libId = data.libraryId;
        const path = data.currentPath || "";
        const key = `${libId}:${path}`;

        // Check if store has folder-specific value
        const storeSpecific = $preferencesStore.folderCoverSizes?.[key];
        if (storeSpecific !== undefined) return storeSpecific;

        // Fall back to global cover size from store
        const defaultSize = isSeriesView ? 2.0 : 1.0;
        return $preferencesStore.gridCoverSize || defaultSize;
    })();

    // Update the CSS variable on documentElement when cover size changes (for client-side navigation)
    $: if (browser && gridCoverSize) {
        document.documentElement.style.setProperty(
            "--cover-size-multiplier",
            String(gridCoverSize),
        );
    }

    // Compute breadcrumb items for the component
    $: breadcrumbItems = isAllLibraries
        ? [{ label: "All Libraries", href: "/library/all/browse" }]
        : [
            {
                label: library?.name || "Library",
                href: `/library/${libraryId}/browse`,
            },
            ...breadcrumbs.map((b, i) => {
                const currentSegments = (currentPath || "")
                    .split("/")
                    .filter(Boolean);
                const idPath = currentSegments.slice(0, i + 1).join("/");
                return {
                    label: b.name,
                    href: `/library/${libraryId}/browse/${idPath || encodePath(b.path)}`,
                };
            }),
        ];

    // Helper to encode path segments for URL (handles special chars like %, #, etc.)
    function encodePath(path) {
        if (!path) return "";
        return path
            .split("/")
            .map((s) => encodeURIComponent(s))
            .join("/");
    }

    function handleFolderClick(item) {
        if (isAllLibraries) {
            // In all-libraries mode, navigate to the specific library
            const itemLibraryId = item.library_id;
            if (item.type === "collection" || item.type === "series") {
                goto(`/library/${itemLibraryId}/browse/${item.id}`);
            }
        } else {
            // Navigate to subfolder within same library
            const rawPath = currentPath
                ? `${currentPath}/${item.id}`
                : `${item.id}`;
            goto(`/library/${libraryId}/browse/${rawPath}`);
        }
    }

    function handleComicSelect(item) {
        // In per-volume mode, clicking a comic updates the info panel
        // Build metadata object from the item - include ALL fields from the API
        selectedComic = {
            id: item.id,
            name: item.name || item.title,
            title: item.title || item.name,
            cover_hash: item.cover_hash,
            synopsis: item.synopsis || item.description,
            writer: item.writer,
            artist: item.artist || item.penciller,
            publisher: item.publisher,
            year: item.year,
            genre: item.genre,
            tags: item.tags,
            scanner_source: item.scanner_source,
            scanner_source_id: item.scanner_source_id,
            scanner_source_url: item.scanner_source_url,
            scan_confidence: item.scan_confidence,
            num_pages: item.num_pages,
            progress_percent: item.progress_percent,
            current_page: item.current_page,
        };
    }

    async function fetchBrowsePage(offset) {
        if (isAllLibraries) {
            return browseAllLibraries(sortBy, offset, limit, randomSeed);
        }
        const pathArg = currentPath || "";
        return browseLibrary(
            libraryId,
            pathArg,
            sortBy,
            offset,
            limit,
            randomSeed,
        );
    }

    async function prefetchNextPage() {
        if (prefetching || loadingMore || !hasMore) return;

        const nextOffset = items.length;
        if (prefetchedOffset === nextOffset) return;

        prefetching = true;
        try {
            const response = await fetchBrowsePage(nextOffset);
            if ((response.items || []).length > 0) {
                prefetchedPage = response;
                prefetchedOffset = nextOffset;
            }
        } catch (err) {
            console.error("Failed to prefetch next library page:", err);
        } finally {
            prefetching = false;
        }
    }

    async function loadMoreItems() {
        if (loadingMore || !hasMore) return;

        loadingMore = true;
        try {
            const nextOffset = items.length; // Use current length as new offset
            let response;

            if (prefetchedPage && prefetchedOffset === nextOffset) {
                response = prefetchedPage;
                prefetchedPage = null;
                prefetchedOffset = null;
            } else {
                response = await fetchBrowsePage(nextOffset);
            }

            const newItems = response.items || [];

            if (newItems.length > 0) {
                items = [...items, ...newItems];
                // Update total just in case
                if (response.total !== undefined) {
                    totalItems = response.total;
                }
            } else {
                // No more items?
                hasMore = false;
            }
        } catch (err) {
            console.error("Failed to load more items:", err);
        } finally {
            loadingMore = false;
            if (browser) {
                queueMicrotask(() => {
                    prefetchNextPage();
                });
            }
        }
    }

    function infiniteScroll(node) {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    loadMoreItems();
                }
            },
            {
                rootMargin: "1500px", // Load next page when within 1500px of bottom for smoother infinite scroll
            },
        );

        observer.observe(node);

        return {
            destroy() {
                observer.disconnect();
            },
        };
    }

    // Determine if we should show the detail header (only for comic view now)
    $: showDetailHeader = isComicView;
    $: headerItem = isComicView ? comic : null;

    $: seriesItem = folder
        ? {
              ...folder,
              cover_hash:
                  folder?.cover_hash ||
                  items?.[0]?.cover_hash ||
                  items?.[0]?.hash,
          }
        : null;

    // Get the first comic ID from items for favorites/lists
    $: firstComicId = items?.find(i => i.type === 'comic')?.id || null;

    // Initial setup for grid size
    $: if (isComicView) {
        // Comic view always grid, but maybe default to larger for single item?
        // Actually keep consistent size for now
    }
</script>

<div
    class="h-screen flex flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]"
>
    <!-- Navbar at Top -->
    <Navbar />

    <!-- Sidebar + Main Content Row -->
    <div class="flex-1 flex overflow-hidden">
        <!-- Sidebar -->
        <HomeSidebar
            {libraries}
            {seriesTree}
            {currentFilter}
        />

        <!-- Main Content -->
        <main
            class="flex-1 overflow-y-auto px-4 pb-8 scrollbar-thin scrollbar-thumb-[var(--color-border)] scrollbar-track-transparent"
        >
            <div class="w-full pt-4">
                {#if error}
                    <div
                        class="flex flex-col items-center justify-center py-20"
                    >
                        <p class="text-[var(--color-error)] text-lg mb-4">
                            {error}
                        </p>
                        <a
                            href={isAllLibraries ? "/library/all/browse" : `/library/${libraryId}/browse`}
                            class="px-4 py-2 bg-[var(--color-bg-secondary)] rounded hover:bg-[var(--color-bg-tertiary)] transition"
                            >{isAllLibraries ? "Reload" : "Return to Library Root"}</a
                        >
                    </div>
                {:else if browseData}
                    <!-- Breadcrumbs -->
                    <div class="py-4">
                        <Breadcrumbs items={breadcrumbItems} />
                    </div>

                    <!-- Continue Reading (at root for both modes) -->
                    {#if (isAllLibraries || currentPath === "") && continueReadingItems.length > 0}
                        <div class="mb-10">
                            <div class="flex items-center gap-2 mb-4 px-1">
                                <BookOpen
                                    class="w-5 h-5 text-[var(--color-accent)]"
                                />
                                <h2 class="text-xl font-bold text-dark-text">
                                    Continue Reading
                                </h2>
                            </div>

                            <HorizontalCarousel itemWidth={160} gap={16}>
                                {#each continueReadingItems as item (item.id)}
                                    <div class="w-[160px] flex-none">
                                        <ComicCard
                                            comic={item}
                                            libraryId={item.library_id || libraryId}
                                            variant="grid"
                                            href={`/comic/${item.library_id || libraryId}/${item.id}/read`}
                                        />
                                    </div>
                                {/each}
                            </HorizontalCarousel>
                        </div>
                    {/if}

                    <!-- TWO-COLUMN SERIES LAYOUT -->
                    {#if isSeriesView}
                        <div class="series-two-column">
                            <!-- Left Column: Series Info Panel -->
                            <aside class="series-info-sidebar">
                                <SeriesInfoPanel
                                    item={perVolumeMetadata && selectedComic
                                        ? selectedComic
                                        : seriesItem}
                                    {libraryId}
                                    onBack={() => history.back()}
                                    onScanSeries={(overwrite) =>
                                        handleScanSeries(overwrite)}
                                    isScanning={isScanningSeries}
                                    scanError={seriesScanError}
                                    {perVolumeMetadata}
                                    selectedComicId={selectedComic?.id}
                                    {firstComicId}
                                />
                            </aside>

                            <!-- Right Column: Issues Grid -->
                            <div class="series-content">
                                <!-- View Controls -->
                                {#if hasContent}
                                    <div
                                        class="flex items-center justify-between mb-4 p-3 bg-[var(--color-secondary-bg)] rounded-lg border border-[var(--color-border)]"
                                    >
                                        <div class="flex items-center gap-3">
                                            <span
                                                class="text-[var(--color-text-secondary)] text-sm font-medium"
                                            >
                                                {totalItems} Issues
                                            </span>
                                        </div>

                                        <div
                                            class="flex bg-[var(--color-bg-tertiary)] rounded-lg p-1 items-center gap-1"
                                        >
                                            <!-- Sort Dropdown -->
                                            <div class="relative">
                                                <button
                                                    type="button"
                                                    on:click={() =>
                                                        (showSortDropdown =
                                                            !showSortDropdown)}
                                                    class="flex items-center gap-1 text-sm text-[var(--color-text)] py-1 px-2 hover:text-[var(--color-text-secondary)] transition-colors"
                                                >
                                                    {sortOptions.find(
                                                        (o) =>
                                                            o.value === sortBy,
                                                    )?.label || "Name"}
                                                    <svg
                                                        class="w-4 h-4"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            stroke-linecap="round"
                                                            stroke-linejoin="round"
                                                            stroke-width="2"
                                                            d="M19 9l-7 7-7-7"
                                                        />
                                                    </svg>
                                                </button>
                                                {#if showSortDropdown}
                                                    <!-- svelte-ignore a11y-click-events-have-key-events -->
                                                    <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                    <div
                                                        class="fixed inset-0 z-40"
                                                        on:click={() =>
                                                            (showSortDropdown = false)}
                                                    ></div>
                                                    <div
                                                        class="absolute top-full left-0 mt-1 z-50 min-w-[140px] py-1 rounded-lg shadow-lg"
                                                        style="background-color: var(--color-secondary-bg); border: 1px solid var(--color-border);"
                                                    >
                                                        {#each sortOptions as option}
                                                            <button
                                                                type="button"
                                                                class="w-full text-left px-3 py-2 text-sm transition-colors {sortBy ===
                                                                option.value
                                                                    ? 'bg-[var(--color-accent)] text-white'
                                                                    : 'text-[var(--color-text)] hover:bg-[var(--color-bg-tertiary)]'}"
                                                                on:click={() =>
                                                                    applySorting(
                                                                        option.value,
                                                                    )}
                                                            >
                                                                {option.label}
                                                            </button>
                                                        {/each}
                                                    </div>
                                                {/if}
                                            </div>

                                            <div
                                                class="w-px h-5 bg-[var(--color-border)] mx-1"
                                            ></div>

                                            <button
                                                class="p-1.5 rounded transition-colors {showSizeSlider
                                                    ? 'bg-[var(--color-accent)] text-white'
                                                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
                                                on:click={() =>
                                                    (showSizeSlider =
                                                        !showSizeSlider)}
                                                title="Cover Size"
                                            >
                                                <SlidersHorizontal size={14} />
                                            </button>

                                            <div
                                                class="w-px h-5 bg-[var(--color-border)] mx-1"
                                            ></div>

                                            <button
                                                class="p-1.5 rounded transition-colors {viewMode ===
                                                'grid'
                                                    ? 'bg-[var(--color-accent)] text-white'
                                                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
                                                on:click={() =>
                                                    preferencesStore.setViewMode(
                                                        "grid",
                                                    )}
                                                title="Grid View"
                                            >
                                                <Grid size={14} />
                                            </button>
                                            <button
                                                class="p-1.5 rounded transition-colors {viewMode ===
                                                'list'
                                                    ? 'bg-[var(--color-accent)] text-white'
                                                    : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
                                                on:click={() =>
                                                    preferencesStore.setViewMode(
                                                        "list",
                                                    )}
                                                title="List View"
                                            >
                                                <List size={14} />
                                            </button>
                                        </div>
                                    </div>

                                    {#if showSizeSlider}
                                        <div
                                            class="mb-4 p-3 bg-[var(--color-secondary-bg)] rounded-lg border border-[var(--color-border)] flex items-center gap-4"
                                        >
                                            <span class="text-xs font-medium"
                                                >Size: {Math.round(
                                                    gridCoverSize * 100,
                                                )}%</span
                                            >
                                            <input
                                                type="range"
                                                min="0.5"
                                                max="2.0"
                                                step="0.1"
                                                value={gridCoverSize}
                                                on:input={(e) =>
                                                    preferencesStore.setFolderCoverSize(
                                                        parseFloat(
                                                            e.target.value,
                                                        ),
                                                        libraryId,
                                                        currentPath,
                                                    )}
                                                class="flex-1 accent-[var(--color-accent)] cursor-pointer"
                                            />
                                        </div>
                                    {/if}
                                {/if}

                                <!-- Issues Grid -->
                                {#if !hasContent}
                                    <div
                                        class="flex flex-col items-center justify-center py-16 text-[var(--color-text-muted)]"
                                    >
                                        <FolderOpen
                                            size={40}
                                            class="mb-3 opacity-20"
                                        />
                                        <p class="text-sm">No issues found</p>
                                    </div>
                                {:else}
                                    <div
                                        class="grid gap-4 {viewMode === 'grid'
                                            ? 'series-issues-grid'
                                            : 'grid-cols-1'}"
                                        style={browser
                                            ? `--cover-size-multiplier: ${gridCoverSize};`
                                            : ""}
                                    >
                                        {#each items as item (item.id + "_" + item.type)}
                                            {#if item.type === "collection" || item.type === "series"}
                                                <FolderCard
                                                    {item}
                                                    {libraryId}
                                                    on:click={() =>
                                                        handleFolderClick(item)}
                                                    {viewMode}
                                                />
                                            {:else if item.type === "comic"}
                                                <!-- svelte-ignore a11y-click-events-have-key-events -->
                                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                <div
                                                    class="comic-card-wrapper {perVolumeMetadata &&
                                                    selectedComic?.id ===
                                                        item.id
                                                        ? 'selected'
                                                        : ''}"
                                                    on:click={(e) => {
                                                        if (perVolumeMetadata) {
                                                            e.preventDefault();
                                                            e.stopPropagation();
                                                            handleComicSelect(item);
                                                        }
                                                    }}
                                                    on:dblclick={() =>
                                                        goto(
                                                            `/comic/${libraryId}/${item.id}/read`,
                                                        )}
                                                >
                                                    <ComicCard
                                                        comic={item}
                                                        {libraryId}
                                                        variant={viewMode}
                                                        href={perVolumeMetadata ? null : `/comic/${libraryId}/${item.id}/read`}
                                                        noLink={perVolumeMetadata}
                                                    />
                                                </div>
                                            {/if}
                                        {/each}
                                    </div>

                                    {#if hasMore}
                                        <div
                                            use:infiniteScroll
                                            class="flex justify-center mt-6 py-6"
                                        >
                                            <div
                                                class="flex items-center gap-2 text-[var(--color-text-secondary)]"
                                            >
                                                <Loader2
                                                    size={20}
                                                    class="animate-spin"
                                                />
                                                <span class="text-sm"
                                                    >Loading more...</span
                                                >
                                            </div>
                                        </div>
                                    {/if}
                                {/if}
                            </div>
                        </div>
                    {:else}
                        <!-- ORIGINAL LAYOUT (for library root, comic view, etc.) -->

                        <!-- Detail Header (Hero) - Only for Comic View -->
                        {#if showDetailHeader}
                            <DetailHeader
                                item={headerItem}
                                {libraryId}
                                {firstComicId}
                                onBack={() => history.back()}
                                showBack={true}
                                onStartReading={isComicView
                                    ? () => {
                                          const page =
                                              comic.current_page > 0
                                                  ? `?page=${comic.current_page}`
                                                  : "";
                                          window.location.href = `/comic/${libraryId}/${comic.id}/read${page}`;
                                      }
                                    : undefined}
                            />
                        {/if}

                        <!-- View Controls & Stats (for library root) -->
                        {#if hasContent && !showDetailHeader}
                            <div
                                class="flex items-center justify-between mb-6 p-4 bg-[var(--color-secondary-bg)] rounded-xl border border-[var(--color-border)]"
                            >
                                <div class="flex flex-wrap gap-4">
                                    <span
                                        class="text-[var(--color-text-secondary)] text-sm"
                                    >
                                        {totalItems} Items
                                    </span>
                                </div>

                                <div
                                    class="flex bg-[var(--color-bg-tertiary)] rounded-lg p-1 items-center gap-1"
                                >
                                    <!-- Custom Sort Dropdown -->
                                    <div class="relative">
                                        <button
                                            type="button"
                                            on:click={() =>
                                                (showSortDropdown =
                                                    !showSortDropdown)}
                                            class="flex items-center gap-1 text-sm text-[var(--color-text)] py-1 px-2 hover:text-[var(--color-text-secondary)] transition-colors"
                                        >
                                            {sortOptions.find(
                                                (o) => o.value === sortBy,
                                            )?.label || "Name"}
                                            <svg
                                                class="w-4 h-4"
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    stroke-width="2"
                                                    d="M19 9l-7 7-7-7"
                                                />
                                            </svg>
                                        </button>
                                        {#if showSortDropdown}
                                            <!-- svelte-ignore a11y-click-events-have-key-events -->
                                            <!-- svelte-ignore a11y-no-static-element-interactions -->
                                            <div
                                                class="fixed inset-0 z-40"
                                                on:click={() =>
                                                    (showSortDropdown = false)}
                                            ></div>
                                            <div
                                                class="absolute top-full left-0 mt-1 z-50 min-w-[140px] py-1 rounded-lg shadow-lg"
                                                style="background-color: var(--color-secondary-bg); border: 1px solid var(--color-border);"
                                            >
                                                {#each sortOptions as option}
                                                    <button
                                                        type="button"
                                                        class="w-full text-left px-3 py-2 text-sm transition-colors {sortBy ===
                                                        option.value
                                                            ? 'bg-[var(--color-accent)] text-white'
                                                            : 'text-[var(--color-text)] hover:bg-[var(--color-bg-tertiary)]'}"
                                                        on:click={() => {
                                                            applySorting(
                                                                option.value,
                                                            );
                                                        }}
                                                    >
                                                        {option.label}
                                                    </button>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>

                                    <div
                                        class="w-px h-6 bg-[var(--color-border)] mx-1"
                                    ></div>

                                    <button
                                        class="p-2 rounded transition-colors {showSizeSlider
                                            ? 'bg-[var(--color-accent)] text-white'
                                            : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
                                        on:click={() =>
                                            (showSizeSlider = !showSizeSlider)}
                                        title="Cover Size"
                                    >
                                        <SlidersHorizontal size={16} />
                                    </button>

                                    <div
                                        class="w-px h-6 bg-[var(--color-border)] mx-1"
                                    ></div>

                                    <button
                                        class="p-2 rounded transition-colors {viewMode ===
                                        'grid'
                                            ? 'bg-[var(--color-accent)] text-white'
                                            : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
                                        on:click={() =>
                                            preferencesStore.setViewMode(
                                                "grid",
                                            )}
                                        title="Grid View"
                                    >
                                        <Grid size={16} />
                                    </button>
                                    <button
                                        class="p-2 rounded transition-colors {viewMode ===
                                        'list'
                                            ? 'bg-[var(--color-accent)] text-white'
                                            : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}"
                                        on:click={() =>
                                            preferencesStore.setViewMode(
                                                "list",
                                            )}
                                        title="List View"
                                    >
                                        <List size={16} />
                                    </button>
                                </div>
                            </div>

                            {#if showSizeSlider}
                                <div
                                    class="mb-6 p-4 bg-[var(--color-secondary-bg)] rounded-xl border border-[var(--color-border)] flex items-center gap-4"
                                >
                                    <span class="text-sm font-medium"
                                        >Cover Size: {Math.round(
                                            gridCoverSize * 100,
                                        )}%</span
                                    >
                                    <input
                                        type="range"
                                        min="0.5"
                                        max="2.0"
                                        step="0.1"
                                        value={gridCoverSize}
                                        on:input={(e) => {
                                            if (isAllLibraries) {
                                                preferencesStore.setGridCoverSize(parseFloat(e.target.value));
                                            } else {
                                                preferencesStore.setFolderCoverSize(
                                                    parseFloat(e.target.value),
                                                    libraryId,
                                                    currentPath,
                                                );
                                            }
                                        }}
                                        class="flex-1 accent-[var(--color-accent)] cursor-pointer"
                                    />
                                </div>
                            {/if}
                        {/if}

                        <!-- Metadata Display for Comic View -->
                        {#if isComicView && comic}
                            <div class="mb-8">
                                <MetadataDisplay
                                    {comic}
                                    showScannerActions={true}
                                />
                            </div>
                        {/if}

                        <!-- Section Title for Comic View -->
                        {#if isComicView && hasContent}
                            <div class="flex items-center gap-2 mb-4 px-1">
                                <BookOpen
                                    class="w-5 h-5 text-[var(--color-accent)]"
                                />
                                <h2 class="text-xl font-bold text-dark-text">
                                    Volumes
                                </h2>
                            </div>
                        {/if}

                        <!-- Content Grid -->
                        {#if !hasContent}
                            <div
                                class="flex flex-col items-center justify-center py-20 text-[var(--color-text-muted)]"
                            >
                                <FolderOpen size={48} class="mb-4 opacity-20" />
                                <p>{isAllLibraries ? "No content available" : "This folder is empty"}</p>
                            </div>
                        {:else}
                            <div
                                class="grid gap-6 {viewMode === 'grid'
                                    ? 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6'
                                    : 'grid-cols-1 max-w-3xl mx-auto'}"
                                style="{browser
                                    ? `--cover-size-multiplier: ${gridCoverSize};`
                                    : ''} grid-template-columns: {viewMode ===
                                'grid'
                                    ? 'repeat(auto-fill, minmax(calc(160px * var(--cover-size-multiplier, 1)), 1fr))'
                                    : ''};"
                            >
                                {#each items as item (item.id + "_" + item.type)}
                                    {#if item.type === "collection" || item.type === "series"}
                                        <FolderCard
                                            {item}
                                            libraryId={isAllLibraries ? item.library_id : libraryId}
                                            on:click={() =>
                                                handleFolderClick(item)}
                                            {viewMode}
                                        />
                                    {:else if item.type === "comic"}
                                        <ComicCard
                                            comic={item}
                                            libraryId={isAllLibraries ? item.library_id : libraryId}
                                            variant={viewMode}
                                            href={isAllLibraries
                                                ? `/comic/${item.library_id}/${item.id}/read`
                                                : currentPath === ""
                                                    ? `/library/${libraryId}/browse/${item.id}`
                                                    : `/comic/${libraryId}/${item.id}/read`}
                                        />
                                    {/if}
                                {/each}
                            </div>

                            <!-- Infinite Scroll Sentinel -->
                            {#if hasMore}
                                <div
                                    use:infiniteScroll
                                    class="flex justify-center mt-8 py-8"
                                >
                                    <div
                                        class="flex items-center gap-2 text-[var(--color-text-secondary)]"
                                    >
                                        <Loader2
                                            size={24}
                                            class="animate-spin"
                                        />
                                        <span>Loading more...</span>
                                    </div>
                                </div>
                            {/if}
                        {/if}
                    {/if}
                {:else}
                    <!-- Loading State -->
                    <div
                        class="flex flex-col items-center justify-center py-20"
                    >
                        <div
                            class="w-10 h-10 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin"
                        ></div>
                        <p class="mt-4 text-[var(--color-text-muted)]">
                            Loading library contents...
                        </p>
                    </div>
                {/if}
            </div>
        </main>
    </div>
</div>

<!-- Candidate Selection Modal -->
{#if showCandidateModal && scanCandidates.length > 0}
    <div
        class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        on:click|self={closeCandidateModal}
        on:keydown={(e) => e.key === "Escape" && closeCandidateModal()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-modal-title"
        tabindex="-1"
    >
        <div
            class="bg-dark-bg-secondary rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden border"
            style="border-color: var(--color-border);"
        >
            <!-- Modal Header -->
            <div
                class="flex items-center justify-between p-5 border-b bg-gradient-to-r from-accent-orange/10 to-accent-orange/5"
                style="border-color: var(--color-border);"
            >
                <div>
                    <h2
                        id="candidate-modal-title"
                        class="text-xl font-bold text-dark-text"
                    >
                        Select Match
                    </h2>
                    <p class="text-sm text-accent-orange/80 mt-1">
                        No automatic match found. Choose from {scanCandidates.length}
                        candidate{scanCandidates.length > 1 ? "s" : ""} below:
                    </p>
                </div>
                <button
                    on:click={closeCandidateModal}
                    class="p-2 hover:bg-dark-bg-tertiary rounded-lg transition-colors text-dark-text-secondary hover:text-dark-text"
                    aria-label="Close modal"
                >
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Candidates List -->
            <div class="overflow-y-auto max-h-[calc(85vh-120px)] p-4 space-y-3">
                {#each scanCandidates as candidate, index}
                    <button
                        on:click={() => handleSelectCandidate(candidate, index)}
                        disabled={isApplyingCandidate}
                        class="w-full text-left p-4 rounded-xl border transition-all duration-200
                               {selectedCandidateIndex === index
                            ? 'border-status-success bg-status-success/20'
                            : 'bg-dark-bg-tertiary hover:border-accent-orange/50 hover:bg-accent-orange/10'}
                               disabled:opacity-50 disabled:cursor-not-allowed"
                        style="border-color: {selectedCandidateIndex === index
                            ? ''
                            : 'var(--color-border)'}"
                    >
                        <div class="flex items-start gap-4">
                            <!-- Confidence Badge -->
                            <div class="flex-shrink-0">
                                <div
                                    class="w-14 h-14 rounded-xl flex flex-col items-center justify-center
                                           {candidate.confidence >= 0.7
                                        ? 'bg-status-success/20 text-status-success'
                                        : candidate.confidence >= 0.5
                                          ? 'bg-status-warning/20 text-status-warning'
                                          : 'bg-status-error/20 text-status-error'}"
                                >
                                    <span class="text-lg font-bold"
                                        >{Math.round(
                                            candidate.confidence * 100,
                                        )}</span
                                    >
                                    <span class="text-xs opacity-70">%</span>
                                </div>
                            </div>

                            <!-- Candidate Info -->
                            <div class="flex-1 min-w-0">
                                <h3
                                    class="text-dark-text font-semibold text-lg truncate"
                                >
                                    {candidate.title ||
                                        candidate.metadata?.title ||
                                        "Unknown Title"}
                                </h3>

                                {#if candidate.metadata}
                                    <div
                                        class="mt-2 flex flex-wrap gap-2 text-sm"
                                    >
                                        {#if candidate.metadata.year}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                {candidate.metadata.year}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.status}
                                            <span
                                                class="px-2 py-0.5 rounded
                                                   {candidate.metadata
                                                    .status === 'FINISHED'
                                                    ? 'bg-status-success/20 text-status-success'
                                                    : candidate.metadata
                                                            .status ===
                                                        'RELEASING'
                                                      ? 'bg-accent-blue/20 text-accent-blue'
                                                      : 'bg-dark-bg text-dark-text-muted'}"
                                            >
                                                {candidate.metadata.status}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.format}
                                            <span
                                                class="px-2 py-0.5 rounded bg-accent-blue/20 text-accent-blue"
                                            >
                                                {candidate.metadata.format}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.count}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                {candidate.metadata.count} chapters
                                            </span>
                                        {/if}
                                    </div>

                                    {#if candidate.metadata.writer || candidate.metadata.artist}
                                        <p
                                            class="mt-2 text-sm text-dark-text-secondary truncate"
                                        >
                                            {#if candidate.metadata.writer}
                                                <span
                                                    >By {candidate.metadata
                                                        .writer}</span
                                                >
                                            {/if}
                                            {#if candidate.metadata.writer && candidate.metadata.artist && candidate.metadata.writer !== candidate.metadata.artist}
                                                <span>
                                                    • Art by {candidate.metadata
                                                        .artist}</span
                                                >
                                            {:else if candidate.metadata.artist && !candidate.metadata.writer}
                                                <span
                                                    >Art by {candidate.metadata
                                                        .artist}</span
                                                >
                                            {/if}
                                        </p>
                                    {/if}

                                    {#if candidate.metadata.description}
                                        <p
                                            class="mt-2 text-sm text-dark-text-muted line-clamp-2"
                                        >
                                            {candidate.metadata.description
                                                .replace(/<[^>]*>/g, "")
                                                .substring(0, 150)}...
                                        </p>
                                    {/if}
                                {/if}
                            </div>

                            <!-- Action -->
                            <div class="flex-shrink-0 flex items-center">
                                {#if selectedCandidateIndex === index && isApplyingCandidate}
                                    <Loader2
                                        class="w-5 h-5 animate-spin text-status-success"
                                    />
                                {:else}
                                    <div
                                        class="p-2 rounded-lg bg-dark-bg group-hover:bg-accent-orange/20 transition-colors"
                                    >
                                        <Check
                                            class="w-5 h-5 text-dark-text-muted"
                                        />
                                    </div>
                                {/if}
                            </div>
                        </div>

                        <!-- Source Link -->
                        {#if candidate.source_url}
                            <a
                                href={candidate.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                on:click|stopPropagation
                                class="mt-3 inline-flex items-center gap-1 text-xs text-accent-blue hover:text-accent-orange-hover transition-colors"
                            >
                                <ExternalLink class="w-3 h-3" />
                                View on AniList
                            </a>
                        {/if}
                    </button>
                {/each}
            </div>

            <!-- Modal Footer -->
            <div
                class="p-4 border-t bg-dark-bg-tertiary"
                style="border-color: var(--color-border);"
            >
                <div class="flex justify-between items-center">
                    <p class="text-xs text-dark-text-muted">
                        Click on a result to apply its metadata
                    </p>
                    <button
                        on:click={closeCandidateModal}
                        class="px-4 py-2 rounded-lg bg-dark-bg text-dark-text-secondary hover:bg-dark-bg-secondary transition-colors text-sm font-medium"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Two-column series layout */
    .series-two-column {
        display: flex;
        gap: 1.5rem;
        min-height: calc(100vh - 200px);
    }

    .series-info-sidebar {
        flex-shrink: 0;
        width: 320px;
        position: sticky;
        top: 0;
        max-height: calc(100vh - 140px);
        overflow-y: auto;
        border-radius: 0.75rem;
        border: 1px solid var(--color-border);
    }

    .series-content {
        flex: 1;
        min-width: 0;
    }

    .series-issues-grid {
        display: grid;
        grid-template-columns: repeat(
            auto-fill,
            minmax(calc(140px * var(--cover-size-multiplier, 1)), 1fr)
        );
        gap: 1rem;
    }

    /* Comic card wrapper for per-volume selection */
    .comic-card-wrapper {
        cursor: pointer;
        border-radius: 0.5rem;
        transition:
            transform 0.15s ease,
            box-shadow 0.15s ease;
    }

    .comic-card-wrapper:hover {
        transform: translateY(-2px);
    }

    .comic-card-wrapper.selected {
        outline: 2px solid var(--color-accent);
        outline-offset: 2px;
        transform: scale(1.02);
    }

    /* Responsive: stack on smaller screens */
    @media (max-width: 1024px) {
        .series-two-column {
            flex-direction: column;
        }

        .series-info-sidebar {
            width: 100%;
            position: relative;
            max-height: none;
            overflow-y: visible;
        }

        .series-issues-grid {
            grid-template-columns: repeat(
                auto-fill,
                minmax(calc(120px * var(--cover-size-multiplier, 1)), 1fr)
            );
        }
    }

    @media (max-width: 640px) {
        .series-issues-grid {
            grid-template-columns: repeat(
                auto-fill,
                minmax(calc(100px * var(--cover-size-multiplier, 1)), 1fr)
            );
            gap: 0.75rem;
        }
    }
</style>
