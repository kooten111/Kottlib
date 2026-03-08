<script>
    /**
     * CollectionCard - Card for displaying collections (folders with sub-folders)
     *
     * Features:
     * - Stacked card visual effect
     * - "COLLECTION" type badge
     * - Sub-collection and comic counts
     * - Progress indicator
     * - Genre pills preview
     */
    import { FolderOpen, BookOpen, Star } from "lucide-svelte";
    import { getCoverUrl } from "$lib/api/comics";

    export let item;
    export let libraryId;
    export let onClick = null;
    export let href = null;

    // Computed values
    $: metadata = item?.metadata || {};
    $: coverHash = item?.cover_hash || item?.coverHash;
    $: name = item?.name || item?.title || "Unknown";
    $: subCollections =
        item?.children?.filter(
            (c) => c.type === "collection" || c.type === "series",
        ).length || 0;
    $: totalComics = item?.total_issues || item?.comic_count || 0;

    // Progress
    $: progressPercent = item?.overall_progress || 0;
    $: completedCount = item?.completed_volumes || 0;

    // Generate gradient colors from hash
    function getGradientColors(hash) {
        const colorPairs = [
            ["#f97316", "#dc2626"],
            ["#3b82f6", "#8b5cf6"],
            ["#22c55e", "#14b8a6"],
            ["#ec4899", "#f43f5e"],
            ["#eab308", "#f97316"],
            ["#6366f1", "#3b82f6"],
        ];
        let sum = 0;
        for (let i = 0; i < (hash || name || "").length; i++)
            sum += (hash || name).charCodeAt(i);
        return colorPairs[sum % colorPairs.length] || colorPairs[0];
    }

    $: gradientColors = getGradientColors(coverHash);
</script>

{#if href}
    <a {href} class="collection-card">
        <div class="card-stack">
            <div class="stack-layer layer-1"></div>
            <div class="stack-layer layer-2"></div>
            <div class="cover-container">
                {#if coverHash}
                    <img
                        src={getCoverUrl(libraryId, coverHash)}
                        alt={name}
                        class="cover-image"
                        loading="lazy"
                        decoding="async"
                    />
                {:else}
                    <div
                        class="cover-placeholder"
                        style="background: linear-gradient(135deg, {gradientColors[0]}, {gradientColors[1]});"
                    ></div>
                {/if}

                <div class="badge collection-badge">COLLECTION</div>

                {#if progressPercent > 0}
                    <div class="progress-badge">
                        {completedCount}/{totalComics}
                    </div>
                {/if}

                <div class="progress-bar">
                    <div
                        class="progress-fill"
                        style="width: {progressPercent}%"
                    ></div>
                </div>
            </div>
        </div>

        <div class="card-info">
            <h3 class="card-title">{name}</h3>

            {#if metadata.genres && metadata.genres.length > 0}
                <div class="genre-pills">
                    {#each (Array.isArray(metadata.genres) ? metadata.genres : [metadata.genres]).slice(0, 2) as genre}
                        <span class="genre-pill">{genre}</span>
                    {/each}
                </div>
            {/if}

            <div class="card-stats">
                <span class="stat">
                    <FolderOpen class="stat-icon" />
                    {subCollections}
                </span>
                <span class="stat">
                    <BookOpen class="stat-icon" />
                    {totalComics}
                </span>
                {#if metadata.rating}
                    <span class="stat rating">
                        <Star class="stat-icon star" />
                        {metadata.rating}
                    </span>
                {/if}
            </div>
        </div>
    </a>
{:else}
    <button class="collection-card" on:click={onClick}>
        <div class="card-stack">
            <div class="stack-layer layer-1"></div>
            <div class="stack-layer layer-2"></div>
            <div class="cover-container">
                {#if coverHash}
                    <img
                        src={getCoverUrl(libraryId, coverHash)}
                        alt={name}
                        class="cover-image"
                        loading="lazy"
                        decoding="async"
                    />
                {:else}
                    <div
                        class="cover-placeholder"
                        style="background: linear-gradient(135deg, {gradientColors[0]}, {gradientColors[1]});"
                    ></div>
                {/if}

                <div class="badge collection-badge">COLLECTION</div>

                {#if progressPercent > 0}
                    <div class="progress-badge">
                        {completedCount}/{totalComics}
                    </div>
                {/if}

                <div class="progress-bar">
                    <div
                        class="progress-fill"
                        style="width: {progressPercent}%"
                    ></div>
                </div>
            </div>
        </div>

        <div class="card-info">
            <h3 class="card-title">{name}</h3>

            {#if metadata.genres && metadata.genres.length > 0}
                <div class="genre-pills">
                    {#each (Array.isArray(metadata.genres) ? metadata.genres : [metadata.genres]).slice(0, 2) as genre}
                        <span class="genre-pill">{genre}</span>
                    {/each}
                </div>
            {/if}

            <div class="card-stats">
                <span class="stat">
                    <FolderOpen class="stat-icon" />
                    {subCollections}
                </span>
                <span class="stat">
                    <BookOpen class="stat-icon" />
                    {totalComics}
                </span>
                {#if metadata.rating}
                    <span class="stat rating">
                        <Star class="stat-icon star" />
                        {metadata.rating}
                    </span>
                {/if}
            </div>
        </div>
    </button>
{/if}

<style>
    .collection-card {
        position: relative;
        display: flex;
        flex-direction: column;
        background: var(--color-secondary-bg);
        border-radius: 0.75rem;
        overflow: hidden;
        border: 1px solid var(--color-border);
        cursor: pointer;
        text-decoration: none;
        text-align: left;
        transition: all 0.2s ease;
        width: 100%;
    }

    .collection-card:hover {
        border-color: var(--color-accent);
        transform: scale(1.02);
        box-shadow: 0 20px 40px -15px color-mix(in srgb, var(--color-accent) 20%, transparent);
    }

    .card-stack {
        position: relative;
    }

    .stack-layer {
        position: absolute;
        left: 0.75rem;
        right: 0.75rem;
        height: 0.75rem;
        border-radius: 0.5rem 0.5rem 0 0;
    }

    .layer-1 {
        top: -0.375rem;
        background: var(--color-tertiary-bg);
        border: 1px solid var(--color-border-strong);
        border-bottom: none;
    }

    .layer-2 {
        top: -0.125rem;
        left: 0.375rem;
        right: 0.375rem;
        background: color-mix(in srgb, var(--color-tertiary-bg) 88%, black 12%);
    }

    .cover-container {
        position: relative;
        aspect-ratio: 2/3;
        overflow: hidden;
    }

    .cover-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .cover-placeholder {
        width: 100%;
        height: 100%;
    }

    .badge {
        position: absolute;
        top: 0.5rem;
        padding: 0.125rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.625rem;
        font-weight: 700;
        backdrop-filter: blur(4px);
    }

    .collection-badge {
        left: 0.5rem;
        background: var(--color-overlay);
        color: var(--color-accent);
        border: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent);
    }

    .progress-badge {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        padding: 0.125rem 0.5rem;
        background: var(--color-overlay);
        backdrop-filter: blur(4px);
        border-radius: 0.25rem;
        font-size: 0.625rem;
        font-weight: 500;
        color: var(--color-text-secondary);
    }

    .progress-bar {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 0.25rem;
        background: color-mix(in srgb, var(--color-bg) 40%, transparent);
    }

    .progress-fill {
        height: 100%;
        background: var(--color-accent);
    }

    .card-info {
        padding: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .card-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-text);
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        transition: color 0.2s;
    }

    .collection-card:hover .card-title {
        color: var(--color-accent);
    }

    .genre-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }

    .genre-pill {
        padding: 0.125rem 0.375rem;
        background: var(--color-tertiary-bg);
        color: var(--color-text-secondary);
        border-radius: 0.25rem;
        font-size: 0.625rem;
    }

    .card-stats {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        color: var(--color-text-muted);
    }

    .stat {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .stat.rating {
        margin-left: auto;
    }

    :global(.stat-icon) {
        width: 0.75rem;
        height: 0.75rem;
    }

    :global(.stat-icon.star) {
        color: var(--color-warning);
    }
</style>
