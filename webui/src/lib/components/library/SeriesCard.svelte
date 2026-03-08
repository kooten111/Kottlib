<script>
    /**
     * SeriesCard - Card for displaying series (folders with comics)
     *
     * Features:
     * - "SERIES" type badge
     * - Hover overlay with description preview
     * - Writer info
     * - Issue count and in-progress count
     * - Rating stars
     */
    import { BookOpen, Clock, Star, Play } from "lucide-svelte";
    import { getCoverUrl } from "$lib/api/comics";
    import { getGradientColors } from "$lib/utils/colors";

    export let item;
    export let libraryId;
    export let onClick = null;
    export let href = null;

    // Computed values
    $: metadata = item?.metadata || {};
    $: coverHash = item?.cover_hash || item?.coverHash;
    $: name = item?.name || item?.title || "Unknown";
    $: issueCount =
        item?.total_issues ||
        item?.volumes?.length ||
        item?.comics?.length ||
        0;
    $: writer = metadata.writer || item?.writer;
    $: description = metadata.description || item?.synopsis;

    // Progress
    $: progressPercent = item?.overall_progress || 0;
    $: completedCount = item?.completed_volumes || 0;
    $: inProgressCount =
        item?.volumes?.filter((v) => v.current_page > 0 && !v.is_completed)
            .length || 0;

    $: gradientColors = getGradientColors(coverHash, name);
</script>

{#if href}
    <a {href} class="series-card">
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

            <div class="badge series-badge">SERIES</div>

            {#if progressPercent > 0}
                <div class="progress-badge">{completedCount}/{issueCount}</div>
            {/if}

            <!-- Hover overlay -->
            <div class="hover-overlay">
                {#if description}
                    <p class="overlay-description">{description}</p>
                {/if}
                <div class="overlay-action">
                    <Play class="play-icon" />
                    <span>View Series</span>
                </div>
            </div>

            <div class="progress-bar">
                <div
                    class="progress-fill"
                    style="width: {progressPercent}%"
                ></div>
            </div>
        </div>

        <div class="card-info">
            <h3 class="card-title">{name}</h3>

            {#if writer}
                <p class="card-writer">{writer}</p>
            {/if}

            <div class="card-stats">
                <span class="stat">
                    <BookOpen class="stat-icon" />
                    {issueCount} issues
                </span>
                {#if inProgressCount > 0}
                    <span class="stat in-progress">
                        <Clock class="stat-icon" />
                        {inProgressCount}
                    </span>
                {/if}
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
    <button class="series-card" on:click={onClick}>
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

            <div class="badge series-badge">SERIES</div>

            {#if progressPercent > 0}
                <div class="progress-badge">{completedCount}/{issueCount}</div>
            {/if}

            <!-- Hover overlay -->
            <div class="hover-overlay">
                {#if description}
                    <p class="overlay-description">{description}</p>
                {/if}
                <div class="overlay-action">
                    <Play class="play-icon" />
                    <span>View Series</span>
                </div>
            </div>

            <div class="progress-bar">
                <div
                    class="progress-fill"
                    style="width: {progressPercent}%"
                ></div>
            </div>
        </div>

        <div class="card-info">
            <h3 class="card-title">{name}</h3>

            {#if writer}
                <p class="card-writer">{writer}</p>
            {/if}

            <div class="card-stats">
                <span class="stat">
                    <BookOpen class="stat-icon" />
                    {issueCount} issues
                </span>
                {#if inProgressCount > 0}
                    <span class="stat in-progress">
                        <Clock class="stat-icon" />
                        {inProgressCount}
                    </span>
                {/if}
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
    .series-card {
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

    .series-card:hover {
        border-color: var(--color-accent);
        transform: scale(1.02);
        box-shadow: 0 20px 40px -15px color-mix(in srgb, var(--color-accent) 20%, transparent);
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

    .series-badge {
        left: 0.5rem;
        background: var(--color-overlay);
        color: var(--color-accent-blue);
        border: 1px solid color-mix(in srgb, var(--color-accent-blue) 40%, transparent);
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

    .hover-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            to top,
            color-mix(in srgb, var(--color-bg) 96%, black 4%),
            color-mix(in srgb, var(--color-bg) 70%, transparent) 50%,
            transparent
        );
        opacity: 0;
        transition: opacity 0.2s;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        padding: 0.75rem;
        gap: 0.5rem;
    }

    .series-card:hover .hover-overlay {
        opacity: 1;
    }

    .overlay-description {
        font-size: 0.75rem;
        color: var(--color-text-secondary);
        margin: 0;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .overlay-action {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    :global(.play-icon) {
        width: 1rem;
        height: 1rem;
        color: var(--color-accent);
    }

    .overlay-action span {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--color-accent);
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

    .series-card:hover .card-title {
        color: var(--color-accent);
    }

    .card-writer {
        font-size: 0.75rem;
        color: var(--color-text-muted);
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
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

    .stat.in-progress :global(.stat-icon) {
        color: var(--color-accent);
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
