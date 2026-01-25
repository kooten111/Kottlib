<script>
    import { goto, afterNavigate } from "$app/navigation";
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    import { browser } from "$app/environment";
    import Navbar from "$lib/components/layout/Navbar.svelte";
    import HomeSidebar from "$lib/components/layout/HomeSidebar.svelte";
    import FolderCard from "$lib/components/library/FolderCard.svelte";
    import ComicCard from "$lib/components/comic/ComicCard.svelte";
    import Breadcrumbs from "$lib/components/common/Breadcrumbs.svelte";
    import HorizontalCarousel from "$lib/components/common/HorizontalCarousel.svelte";
    import {
        FolderOpen,
        BookOpen,
        Grid,
        List,
        Loader2,
        SlidersHorizontal,
    } from "lucide-svelte";
    import { browseAllLibraries } from "$lib/api/libraries";
    import { preferencesStore } from "$lib/stores/preferences";

    export let data;

    $: browseData = data.browseData;
    $: error = data.error;
    $: libraries = data.libraries || [];
    $: seriesTree = data.seriesTree || [];
    $: continueReadingItems = data.continueReading || [];

    // Unified Items List (Pagination Support)
    $: initialItems = browseData?.items || [];
    $: totalItems = browseData?.total || 0;

    // Local state for items to support appending (infinite scroll)
    let items = [];
    let currentOffset = 0;
    let limit = 50;
    let loadingMore = false;

    // When browseData changes (navigation), reset items
    $: if (browseData) {
        items = initialItems;
        currentOffset = browseData.offset || 0;
        limit = browseData.limit || 50;
    }

    $: hasMore = items.length < totalItems;
    $: hasContent = items.length > 0;

    // Construct currentFilter for sidebar highlighting - showing "All Libraries"
    $: currentFilter = { type: "all" };

    // Derive sortBy from URL or fall back to store
    $: sortBy =
        $page.url.searchParams.get("sort") ||
        $preferencesStore.sortBy ||
        "name";

    let showSizeSlider = false;
    let showSortDropdown = false;
    $: randomSeed = $page.url.searchParams.get("seed");

    const sortOptions = [
        { value: "name", label: "Name" },
        { value: "created", label: "Date Added" },
        { value: "updated", label: "Last Updated" },
        { value: "progress", label: "Progress" },
        { value: "random", label: "Shuffle" },
    ];

    // Unified sort check using afterNavigate
    afterNavigate(() => {
        const urlSort = $page.url.searchParams.get("sort");
        const storeSort = $preferencesStore.sortBy;

        if (!urlSort && storeSort && storeSort !== "name") {
            const newUrl = new URL($page.url);
            newUrl.searchParams.set("sort", storeSort);
            if (storeSort === "random")
                newUrl.searchParams.set("seed", String(Date.now()));
            goto(newUrl.toString(), {
                replaceState: true,
                invalidateAll: true,
            });
        }
    });

    // onMount handles the "refresh on random" case
    onMount(() => {
        const urlSort = new URL(window.location.href).searchParams.get("sort");

        if (urlSort === "random") {
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set("seed", String(Date.now()));
            goto(newUrl.toString(), {
                replaceState: true,
                invalidateAll: true,
            });
        }
    });

    // Function to apply sorting - updates URL
    async function applySorting(newSort) {
        // Save preference
        if (newSort) {
            preferencesStore.setSortBy(newSort);
        }

        const targetSort = newSort || sortBy;
        const url = new URL($page.url);
        url.searchParams.set("sort", targetSort);

        // Handle Random Seed
        if (targetSort === "random") {
            const seed = String(Date.now());
            url.searchParams.set("seed", seed);
        } else {
            url.searchParams.delete("seed");
        }

        goto(url.toString(), { noScroll: true, invalidateAll: true });
        showSortDropdown = false;
    }

    let viewMode = $preferencesStore.viewMode; // 'grid' | 'list'
    $: if (viewMode !== $preferencesStore.viewMode) {
        preferencesStore.setViewMode(viewMode);
    }
    // Sync back if store changes
    $: viewMode = $preferencesStore.viewMode;

    // Use global cover size for "All Libraries" browse
    $: gridCoverSize = $preferencesStore.gridCoverSize || 1.4;

    // Update the CSS variable when cover size changes
    $: if (browser && gridCoverSize) {
        document.documentElement.style.setProperty(
            "--cover-size-multiplier",
            String(gridCoverSize),
        );
    }

    // Compute breadcrumb items - just "All Libraries" at root
    $: breadcrumbItems = [
        {
            label: "All Libraries",
            href: "/browse",
        },
    ];

    function handleFolderClick(item) {
        // Navigate to the library browse for this folder/series
        const libraryId = item.library_id;
        if (item.type === "collection" || item.type === "series") {
            // Navigate to library browse with path
            const path = item.path || item.name;
            const encodedPath = path
                .split("/")
                .map((segment) => encodeURIComponent(segment))
                .join("/");
            goto(`/library/${libraryId}/browse/${encodedPath}`);
        }
    }

    function handleComicClick(item) {
        const libraryId = item.library_id;
        goto(`/comic/${libraryId}/${item.id}/read`);
    }

    async function loadMoreItems() {
        if (loadingMore || !hasMore) return;

        loadingMore = true;
        try {
            const nextOffset = items.length;
            const response = await browseAllLibraries(
                sortBy,
                nextOffset,
                limit,
                randomSeed,
            );
            const newItems = response.items || [];

            if (newItems.length > 0) {
                items = [...items, ...newItems];
                if (response.total !== undefined) {
                    totalItems = response.total;
                }
            }

            // Check if we've reached the end based on total count
            if (items.length >= totalItems) {
                hasMore = false;
            }
        } catch (err) {
            console.error("Failed to load more items:", err);
            // Don't set hasMore to false on error - allow retry
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
                            href="/browse"
                            class="px-4 py-2 bg-[var(--color-bg-secondary)] rounded hover:bg-[var(--color-bg-tertiary)] transition"
                            >Reload</a
                        >
                    </div>
                {:else if browseData}
                    <!-- Breadcrumbs -->
                    <div class="py-4">
                        <Breadcrumbs items={breadcrumbItems} />
                    </div>

                    <!-- Continue Reading -->
                    {#if continueReadingItems.length > 0}
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
                                            libraryId={item.library_id}
                                            variant="grid"
                                            href={`/comic/${item.library_id}/${item.id}/read`}
                                        />
                                    </div>
                                {/each}
                            </HorizontalCarousel>
                        </div>
                    {/if}

                    <!-- View Controls & Stats -->
                    {#if hasContent}
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
                                        preferencesStore.setGridCoverSize(
                                            parseFloat(e.target.value),
                                        )}
                                    class="flex-1 accent-[var(--color-accent)] cursor-pointer"
                                />
                            </div>
                        {/if}
                    {/if}

                    <!-- Content Grid -->
                    {#if !hasContent}
                        <div
                            class="flex flex-col items-center justify-center py-20 text-[var(--color-text-muted)]"
                        >
                            <FolderOpen size={48} class="mb-4 opacity-20" />
                            <p>No content available</p>
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
                                        libraryId={item.library_id}
                                        on:click={() => handleFolderClick(item)}
                                        {viewMode}
                                    />
                                {:else if item.type === "comic"}
                                    <ComicCard
                                        comic={item}
                                        libraryId={item.library_id}
                                        variant={viewMode}
                                        href={`/comic/${item.library_id}/${item.id}/read`}
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
                            Loading content...
                        </p>
                    </div>
                {/if}
            </div>
        </main>
    </div>
</div>
