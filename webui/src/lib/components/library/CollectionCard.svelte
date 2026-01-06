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
        background: rgba(24, 24, 27, 0.9);
        border-radius: 0.75rem;
        overflow: hidden;
        border: 1px solid rgba(63, 63, 70, 0.8);
        cursor: pointer;
        text-decoration: none;
        text-align: left;
        transition: all 0.2s ease;
        width: 100%;
    }

    .collection-card:hover {
        border-color: rgba(249, 115, 22, 0.5);
        transform: scale(1.02);
        box-shadow: 0 20px 40px -15px rgba(249, 115, 22, 0.1);
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
        background: rgba(63, 63, 70, 0.8);
        border: 1px solid rgba(82, 82, 91, 0.7);
        border-bottom: none;
    }

    .layer-2 {
        top: -0.125rem;
        left: 0.375rem;
        right: 0.375rem;
        background: rgba(52, 52, 56, 0.9);
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
        background: rgba(24, 24, 27, 0.9);
        color: #fb923c;
        border: 1px solid rgba(249, 115, 22, 0.3);
    }

    .progress-badge {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        padding: 0.125rem 0.5rem;
        background: rgba(24, 24, 27, 0.9);
        backdrop-filter: blur(4px);
        border-radius: 0.25rem;
        font-size: 0.625rem;
        font-weight: 500;
        color: #d4d4d8;
    }

    .progress-bar {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 0.25rem;
        background: rgba(0, 0, 0, 0.4);
    }

    .progress-fill {
        height: 100%;
        background: #f97316;
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
        color: white;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        transition: color 0.2s;
    }

    .collection-card:hover .card-title {
        color: #fb923c;
    }

    .genre-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }

    .genre-pill {
        padding: 0.125rem 0.375rem;
        background: rgba(63, 63, 70, 0.8);
        color: #a1a1aa;
        border-radius: 0.25rem;
        font-size: 0.625rem;
    }

    .card-stats {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        color: #71717a;
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
        color: #eab308;
    }
</style>
