<script>
    import { createEventDispatcher } from "svelte";
    import {
        FolderOpen,
        BookOpen,
        Star,
        Clock,
        Play,
        Library,
    } from "lucide-svelte";
    import { getCoverUrl } from "$lib/api/comics";
    import { getGradientColors } from "$lib/utils/colors";
    import GenreTag from "$lib/components/common/GenreTag.svelte";

    export let item; // The folder/series object
    export let libraryId;
    export let onClick = null;

    const dispatch = createEventDispatcher();

    // Determine type and styling
    $: isCollection = item.type === "collection";
    $: isLibrary = item.type === "library";
    $: typeLabel = isLibrary
        ? "LIBRARY"
        : isCollection
          ? "COLLECTION"
          : "SERIES";
        $: badgeClass = isLibrary
                ? "type-badge-library"
                : isCollection
                    ? "type-badge-collection"
                    : "type-badge-series";

    $: metadata = item.metadata || item || {};
    $: coverHash = item.cover_hash || item.coverHash;
    $: coverUrl = coverHash ? getCoverUrl(libraryId, coverHash) : null;

    // Stats
    $: subCollections = item.sub_collections || 0; // count of sub-folders
    $: totalIssues = item.total_issues || 0; // total comics
    $: rating = metadata.rating || 0;

    // Progress (mock for now if not provided, or calculated from item)
    $: progress = item.progress || {
        percentage: 0,
        read: 0,
        total: totalIssues,
    };

    $: displayName = item.name || item.title;

    function handleClick() {
        if (onClick) {
            onClick(item);
        } else {
            dispatch("click", item);
        }
    }

    $: gradientColors = getGradientColors(coverHash, displayName);
</script>

<button
    class="folder-card group relative rounded-xl overflow-hidden text-left w-full flex flex-col h-full"
    on:click={handleClick}
>
    <!-- Collection Stack Effect -->
    {#if isCollection}
        <div
            class="absolute -top-1.5 left-3 right-3 h-3 rounded-t-xl border-t border-x stack-layer-1"
        ></div>
        <div
            class="absolute -top-0.5 left-1.5 right-1.5 h-2 rounded-t-lg stack-layer-2"
        ></div>
    {/if}

    <!-- Cover Image Area -->
    <div class="relative aspect-[1/1.414] overflow-hidden w-full cover-area-bg">
        {#if coverUrl}
            <img
                src={coverUrl}
                alt={displayName}
                class="w-full h-full object-cover rounded-none transition-transform duration-500 group-hover:scale-105"
                loading="lazy"
                decoding="async"
            />
        {:else}
            <div
                class="w-full h-full flex items-center justify-center p-4 bg-gradient-to-br"
                style="background-image: linear-gradient(135deg, {gradientColors[0]}, {gradientColors[1]})"
            >
                <div class="placeholder-icon">
                    {#if isLibrary}
                        <Library size={48} />
                    {:else if isCollection}
                        <FolderOpen size={48} />
                    {:else}
                        <BookOpen size={48} />
                    {/if}
                </div>
                <div
                    class="absolute bottom-0 left-0 right-0 p-2 placeholder-label-wrap"
                >
                    <span
                        class="text-xs font-medium line-clamp-2 text-center placeholder-label"
                        >{displayName}</span
                    >
                </div>
            </div>
        {/if}

        <!-- Type Badge -->
        <div
            class="absolute top-2 left-2 px-2 py-0.5 backdrop-blur rounded text-[10px] font-bold border type-badge {badgeClass}"
        >
            {typeLabel}
        </div>

        <!-- Progress Badge (if started) -->
        {#if progress.percentage > 0}
            <div
                class="absolute top-2 right-2 px-2 py-0.5 backdrop-blur rounded text-[10px] font-medium progress-badge"
            >
                {progress.read}/{progress.total}
            </div>
        {/if}

        <!-- Hover Overlay -->
        <div
            class="absolute inset-0 hover-overlay opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3"
        >
            {#if metadata.description || metadata.synopsis}
                <p
                    class="text-xs font-medium leading-relaxed line-clamp-3 mb-2 overlay-description"
                >
                    {metadata.description || metadata.synopsis}
                </p>
            {/if}
            <div class="flex items-center gap-2">
                <Play class="w-4 h-4 overlay-action-icon" />
                <span class="text-xs font-medium overlay-action-text"
                    >Browse {isCollection ? "Collection" : "Series"}</span
                >
            </div>
        </div>

        <!-- Progress Bar (Bottom Line) -->
        {#if progress.percentage > 0}
            <div class="absolute bottom-0 left-0 right-0 h-1 progress-track">
                <div
                    class="h-full progress-fill"
                    style="width: {progress.percentage}%"
                ></div>
            </div>
        {/if}
    </div>

    <!-- Info Area -->
    <div class="p-3 space-y-2 flex-1 flex flex-col w-full card-info-bg">
        <h3
            class="font-semibold text-sm line-clamp-2 card-title transition-colors"
            title={displayName}
        >
            {displayName}
        </h3>

        {#if !isCollection && metadata.writer}
            <p class="text-xs truncate card-writer">{metadata.writer}</p>
        {/if}

        {#if isCollection && metadata.genres}
            <div class="flex flex-wrap gap-1">
                {#each Array.isArray(metadata.genres) ? metadata.genres : metadata.genres.split(",") as genre}
                    <span
                        class="text-[10px] px-1.5 py-0.5 rounded border genre-pill"
                        >{genre.trim()}</span
                    >
                {/each}
            </div>
        {/if}

        <div class="mt-auto flex items-center gap-3 text-xs pt-1 card-stats">
            {#if isCollection || isLibrary}
                {#if subCollections > 0}
                    <span class="flex items-center gap-1"
                        ><FolderOpen class="w-3 h-3" />{subCollections}</span
                    >
                {/if}
                <span class="flex items-center gap-1"
                    ><BookOpen class="w-3 h-3" />{totalIssues}</span
                >
            {:else}
                <span class="flex items-center gap-1"
                    ><BookOpen class="w-3 h-3" />{totalIssues} issues</span
                >
            {/if}

            {#if rating > 0}
                <span class="flex items-center gap-1 ml-auto">
                    <Star
                        class="w-3 h-3 text-yellow-500 fill-yellow-500"
                    />{rating}
                </span>
            {/if}
        </div>
    </div>
</button>

<style>
    .folder-card {
        background: var(--color-secondary-bg);
        border: 1px solid var(--color-border);
        transition: all 0.2s ease;
    }

    .folder-card:hover {
        border-color: var(--color-accent);
        transform: scale(1.02);
        box-shadow: 0 14px 28px -12px color-mix(in srgb, var(--color-accent) 22%, transparent);
    }

    .stack-layer-1 {
        background: var(--color-tertiary-bg);
        border-color: var(--color-border-strong);
    }

    .stack-layer-2 {
        background: color-mix(in srgb, var(--color-tertiary-bg) 88%, black 12%);
    }

    .cover-area-bg {
        background: var(--color-tertiary-bg);
    }

    .placeholder-icon {
        color: color-mix(in srgb, var(--color-text) 55%, transparent);
    }

    .placeholder-label-wrap {
        background: var(--color-overlay-light);
        backdrop-filter: blur(4px);
    }

    .placeholder-label {
        color: var(--color-text);
    }

    .type-badge,
    .progress-badge {
        background: var(--color-overlay);
    }

    .type-badge-library {
        color: var(--color-success);
        border-color: color-mix(in srgb, var(--color-success) 40%, transparent);
    }

    .type-badge-collection {
        color: var(--color-accent);
        border-color: color-mix(in srgb, var(--color-accent) 40%, transparent);
    }

    .type-badge-series {
        color: var(--color-accent-blue);
        border-color: color-mix(in srgb, var(--color-accent-blue) 40%, transparent);
    }

    .progress-badge {
        color: var(--color-text-secondary);
    }

    .hover-overlay {
        background: linear-gradient(
            to top,
            color-mix(in srgb, var(--color-bg) 96%, black 4%),
            color-mix(in srgb, var(--color-bg) 76%, transparent),
            transparent
        );
    }

    .overlay-description {
        color: var(--color-text);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95), 0 0 10px rgba(0, 0, 0, 0.6);
    }

    .overlay-action-icon,
    .overlay-action-text {
        color: var(--color-accent);
    }

    .progress-track {
        background: color-mix(in srgb, var(--color-bg) 40%, transparent);
    }

    .progress-fill {
        background: var(--color-accent);
    }

    .card-info-bg {
        background: var(--color-secondary-bg);
    }

    .card-title {
        color: var(--color-text);
    }

    .group:hover .card-title {
        color: var(--color-accent);
    }

    .card-writer,
    .card-stats {
        color: var(--color-text-muted);
    }

    .genre-pill {
        background: var(--color-tertiary-bg);
        color: var(--color-text-secondary);
        border-color: var(--color-border);
    }
</style>
