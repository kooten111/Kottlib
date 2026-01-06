<script>
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { browser } from "$app/environment";
    import Navbar from "$lib/components/layout/Navbar.svelte";
    import HomeSidebar from "$lib/components/layout/HomeSidebar.svelte";
    import DetailHeader from "$lib/components/common/DetailHeader.svelte";
    import FolderCard from "$lib/components/library/FolderCard.svelte";
    import ComicCard from "$lib/components/comic/ComicCard.svelte";
    import ScannerMetadata from "$lib/components/comic/ScannerMetadata.svelte";
    import Breadcrumbs from "$lib/components/common/Breadcrumbs.svelte";
    import HorizontalCarousel from "$lib/components/common/HorizontalCarousel.svelte";
    import {
        FolderOpen,
        BookOpen,
        Layers,
        Grid,
        List,
        Loader2,
        SlidersHorizontal,
    } from "lucide-svelte";
    import { browseLibrary, getContinueReading } from "$lib/api/libraries";
    import { preferencesStore } from "$lib/stores/preferences";

    export let data;

    $: browseData = data.browseData;
    $: libraryId = data.libraryId;
    $: currentPath = data.currentPath;
    $: error = data.error;

    // Sidebar data
    $: libraries = data.libraries || [];
    $: seriesTree = data.seriesTree || [];

    $: folder = browseData?.folder;
    $: comic = browseData?.comic;
    $: isComicView = browseData?.is_comic_view;
    $: library = browseData?.library;
    $: breadcrumbs = browseData?.breadcrumbs || [];
    // Unified Items List (Pagination Support)
    $: initialItems = browseData?.items || [];
    $: totalItems = browseData?.total || 0;

    // Continue Reading Data
    let continueReadingItems = [];
    let loadingContinueReading = false;

    // Local state for items to support appending (infinite scroll)
    let items = [];
    let currentOffset = 0;
    let limit = 50;
    let loadingMore = false;

    // When browseData changes (navigation), reset items and fetch continue reading
    $: if (browseData) {
        items = initialItems;
        currentOffset = browseData.offset || 0;
        limit = browseData.limit || 50;
        fetchContinueReading();
    }

    async function fetchContinueReading() {
        // Only fetch reading list at root of library
        if (currentPath === "") {
            loadingContinueReading = true;
            try {
                continueReadingItems = await getContinueReading(libraryId);
            } catch (e) {
                console.error("Failed to fetch continue reading:", e);
            } finally {
                loadingContinueReading = false;
            }
        } else {
            continueReadingItems = [];
        }
    }

    $: hasMore = items.length < totalItems;
    $: hasContent = items.length > 0;

    // Construct currentFilter for sidebar highlighting
    $: currentFilter = folder
        ? {
              type: "folder",
              libraryId,
              folderId: folder.id,
              folderName: folder.name,
          }
        : { type: "library", libraryId, libraryName: library?.name };

    // Initial setup for preferences
    // Initial setup for preferences
    // Derive sortBy from URL or fall back to store (but ideally URL drives everything)
    // We use a reactive statement to keep it in sync with URL
    $: sortBy =
        $page.url.searchParams.get("sort") ||
        $preferencesStore.librarySortBy?.[libraryId] ||
        "name";

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
        const storeSort = $preferencesStore.librarySortBy?.[libraryId];

        // Only apply if URL is missing sort but store has one
        // And ensure we are at the root of the library (optional, depending on requirements, but safe)
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
        // Save preference
        if (newSort) {
            preferencesStore.setSortBy(newSort, libraryId);
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

    // Reactive cover size that checks folder-specific preference first, then falls back to global
    // Uses data prop directly to ensure we always have the latest values
    $: gridCoverSize = (() => {
        const libId = data.libraryId;
        const path = data.currentPath || "";
        const key = `${libId}:${path}`;

        // Check if store has folder-specific value (this updates when user changes slider)
        const storeSpecific = $preferencesStore.folderCoverSizes?.[key];
        if (storeSpecific !== undefined) return storeSpecific;

        // Fall back to global cover size from store
        return $preferencesStore.gridCoverSize || 1.0;
    })();

    // Update the CSS variable on documentElement when cover size changes (for client-side navigation)
    $: if (browser && gridCoverSize) {
        document.documentElement.style.setProperty(
            "--cover-size-multiplier",
            String(gridCoverSize),
        );
    }

    // Compute breadcrumb items for the component
    $: breadcrumbItems = [
        {
            label: library?.name || "Library",
            href: `/library/${libraryId}/browse`,
        },
        ...breadcrumbs.map((b, i) => ({
            label: b.name,
            href: `/library/${libraryId}/browse/${b.path}`,
        })),
    ];

    function handleFolderClick(item) {
        // Navigate to subfolder
        const rawPath =
            item.path ||
            (currentPath ? `${currentPath}/${item.name}` : item.name);

        // Encode each segment of the path to ensure valid URI
        const encodedPath = rawPath
            .split("/")
            .map((segment) => encodeURIComponent(segment))
            .join("/");

        goto(`/library/${libraryId}/browse/${encodedPath}`);
    }

    async function loadMoreItems() {
        if (loadingMore || !hasMore) return;

        loadingMore = true;
        try {
            const nextOffset = items.length; // Use current length as new offset
            // Determine path from URL or params
            // If at root, path is empty string/undefined
            // browseLibrary handles it.
            const pathArg = currentPath || "";

            const response = await browseLibrary(
                libraryId,
                pathArg,
                sortBy,
                nextOffset,
                limit,
                randomSeed,
            );
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
                rootMargin: "400px", // Load next page when within 400px of bottom
            },
        );

        observer.observe(node);

        return {
            destroy() {
                observer.disconnect();
            },
        };
    }

    // Determine if we should show the detail header
    $: showDetailHeader = (!!folder && currentPath !== "") || isComicView;
    $: headerItem = isComicView
        ? comic
        : folder
          ? {
                ...folder,
                cover_hash:
                    folder?.cover_hash ||
                    items?.[0]?.cover_hash ||
                    items?.[0]?.hash,
            }
          : null;

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
            currentView="home"
        />

        <!-- Main Content -->
        <main
            class="flex-1 overflow-y-auto px-4 pb-8 scrollbar-thin scrollbar-thumb-[var(--color-border)] scrollbar-track-transparent"
        >
            <div class="max-w-7xl mx-auto w-full pt-4">
                {#if error}
                    <div
                        class="flex flex-col items-center justify-center py-20"
                    >
                        <p class="text-[var(--color-error)] text-lg mb-4">
                            {error}
                        </p>
                        <a
                            href="/library/{libraryId}/browse"
                            class="px-4 py-2 bg-[var(--color-bg-secondary)] rounded hover:bg-[var(--color-bg-tertiary)] transition"
                            >Return to Library Root</a
                        >
                    </div>
                {:else if browseData}
                    <!-- Breadcrumbs -->
                    <div class="py-4">
                        <Breadcrumbs items={breadcrumbItems} />
                    </div>

                    <!-- Continue Reading (Only at root) -->
                    {#if currentPath === "" && continueReadingItems.length > 0}
                        <div class="mb-10">
                            <div class="flex items-center gap-2 mb-4 px-1">
                                <BookOpen
                                    class="w-5 h-5 text-[var(--color-accent)]"
                                />
                                <h2 class="text-xl font-bold text-white">
                                    Continue Reading
                                </h2>
                            </div>

                            <HorizontalCarousel itemWidth={160} gap={16}>
                                {#each continueReadingItems as item (item.id)}
                                    <div class="w-[160px] flex-none">
                                        <ComicCard
                                            comic={item}
                                            {libraryId}
                                            variant="grid"
                                            href={`/comic/${libraryId}/${item.id}/read`}
                                        />
                                    </div>
                                {/each}
                            </HorizontalCarousel>
                        </div>
                    {/if}

                    <!-- Detail Header (Hero) -->
                    {#if showDetailHeader}
                        <DetailHeader
                            item={headerItem}
                            {libraryId}
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

                    <!-- View Controls & Stats -->
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
                                        preferencesStore.setViewMode("grid")}
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
                                        preferencesStore.setViewMode("list")}
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
                                    on:input={(e) =>
                                        preferencesStore.setFolderCoverSize(
                                            parseFloat(e.target.value),
                                            libraryId,
                                            currentPath,
                                        )}
                                    class="flex-1 accent-[var(--color-accent)] cursor-pointer"
                                />
                            </div>
                        {/if}
                    {/if}

                    <!-- Section Title for Comic View -->
                    {#if isComicView && hasContent}
                        <div class="flex items-center gap-2 mb-4 px-1">
                            <BookOpen
                                class="w-5 h-5 text-[var(--color-accent)]"
                            />
                            <h2 class="text-xl font-bold text-white">
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
                            <p>This folder is empty</p>
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
                                        {libraryId}
                                        on:click={() => handleFolderClick(item)}
                                        {viewMode}
                                    />
                                {:else if item.type === "comic"}
                                    <ComicCard
                                        comic={item}
                                        {libraryId}
                                        variant={viewMode}
                                        href={!currentPath
                                            ? `/library/${libraryId}/browse/_comic/${item.id}`
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
                                    <Loader2 size={24} class="animate-spin" />
                                    <span>Loading more...</span>
                                </div>
                            </div>
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
