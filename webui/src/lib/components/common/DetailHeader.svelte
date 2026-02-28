<script>
    /**
     * DetailHeader - Hero header component for series/collection detail pages
     *
     * Features:
     * - Blurred background gradient from cover colors
     * - Large cover with shine effect on hover
     * - Type/status badges
     * - Metadata display (writer, artist, publisher, year, issue count)
     * - Action buttons (Start/Continue Reading, Favorite, Add to List)
     * - Progress bar with completion stats
     * - Expandable synopsis
     * - Genre and tag pills
     */
    import {
        ArrowLeft,
        Play,
        Heart,
        Bookmark,
        User,
        Calendar,
        BookOpen,
        Layers,
        ChevronDown,
        ChevronUp,
        FileText,
        Book,
    } from "lucide-svelte";
    import { getCoverUrl } from "$lib/api/comics";
    import { addFavorite, removeFavorite, isFavorite } from "$lib/api/favorites";
    import AddToListModal from "./AddToListModal.svelte";
    import GenreTag from "./GenreTag.svelte";
    import StarRating from "./StarRating.svelte";
    import ProgressBar from "./ProgressBar.svelte";
    import { onMount } from "svelte";

    export let item; // Series/collection/comic data
    export let libraryId;
    export let onBack = () => history.back();
    export let onStartReading = null;
    export let firstComicId = null; // Comic ID for favorites (passed from parent)

    let expanded = false;
    let isFav = false;
    let favLoading = false;
    let showListModal = false;

    // Get the comic ID for favorites
    // For comic view: use item.id directly
    // For series view: use the firstComicId prop passed from parent
    $: favoriteComicId = (item?.type === 'comic')
        ? item?.id
        : firstComicId || null;

    // Check favorite status on mount and when item changes
    onMount(async () => {
        if (favoriteComicId) {
            isFav = await isFavorite(favoriteComicId);
        }
    });

    $: if (favoriteComicId) {
        checkFavoriteStatus(favoriteComicId);
    }

    async function checkFavoriteStatus(comicId) {
        if (!comicId) return;
        isFav = await isFavorite(comicId);
    }

    async function toggleFavorite() {
        if (!favoriteComicId || favLoading) return;
        try {
            favLoading = true;
            if (isFav) {
                await removeFavorite(favoriteComicId);
                isFav = false;
            } else {
                await addFavorite(favoriteComicId);
                isFav = true;
            }
        } catch (err) {
            console.error('Failed to toggle favorite:', err);
        } finally {
            favLoading = false;
        }
    }

    // Computed values
    $: metadata = item?.metadata || item || {};
    $: isComic = item?.type === "comic";
    $: coverHash = item?.cover_hash || item?.coverHash;
    $: displayName =
        item?.display_name || item?.series_name || item?.name || "Unknown";

    // Progress calculation
    $: progress = isComic
        ? item?.num_pages && item?.current_page
            ? Math.round((item.current_page / item.num_pages) * 100)
            : 0
        : item?.overall_progress || 0;

    $: completedCount = item?.completed_volumes || 0;
    $: totalCount = item?.total_issues || item?.volumes?.length || 0;

    // Determine button text
    $: buttonText =
        progress > 0 && progress < 100 ? "Continue Reading" : "Start Reading";

    // Generate gradient colors from hash (simple hash-based color)
    function getGradientColors(hash) {
        const colorPairs = [
            ["#f97316", "#dc2626"],
            ["#3b82f6", "#8b5cf6"],
            ["#22c55e", "#14b8a6"],
            ["#ec4899", "#f43f5e"],
            ["#eab308", "#f97316"],
            ["#6366f1", "#3b82f6"],
            ["#06b6d4", "#0ea5e9"],
            ["#a855f7", "#ec4899"],
        ];
        let sum = 0;
        for (let i = 0; i < (hash || "").length; i++) sum += hash.charCodeAt(i);
        return colorPairs[sum % colorPairs.length] || colorPairs[0];
    }

    $: gradientColors = getGradientColors(coverHash);

    // Parse genres and tags (may come as comma-separated string or array)
    function parseList(value) {
        if (!value) return [];
        if (Array.isArray(value)) return value;
        return value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
    }

    $: genres = parseList(metadata.genres || metadata.genre || item?.genre);
    $: tags = parseList(metadata.tags || item?.tags);
    $: contentWarnings = parseList(metadata.contentWarning);
</script>

<div class="detail-header">
    <!-- Background gradient/blur effect -->
    <div class="header-background">
        <div
            class="gradient-blur"
            style="background: linear-gradient(135deg, {gradientColors[0]}40, {gradientColors[1]}20);"
        ></div>
        <div class="gradient-overlay"></div>
    </div>

    <div class="header-content">
        <!-- Back button -->
        <button class="back-button" on:click={onBack}>
            <ArrowLeft class="icon" />
            <span>Back</span>
        </button>

        <div class="header-main">
            <!-- Cover -->
            <div class="cover-wrapper">
                <div class="cover-container">
                    {#if coverHash}
                        <img
                            src={getCoverUrl(libraryId, coverHash)}
                            alt={displayName}
                            class="cover-image"
                        />
                    {:else}
                        <div
                            class="cover-placeholder"
                            style="background: linear-gradient(135deg, {gradientColors[0]}, {gradientColors[1]});"
                        >
                            <Book class="placeholder-icon" />
                            <span class="placeholder-text">{displayName}</span>
                        </div>
                    {/if}
                    <div class="cover-shine"></div>
                </div>
            </div>

            <!-- Info -->
            <div class="info-section">
                <!-- Type badges -->
                <div class="badge-row">
                    <GenreTag
                        variant={item?.type === "collection"
                            ? "genre"
                            : "default"}
                    >
                        {item?.type || "series"}
                    </GenreTag>
                    {#if metadata.status || item?.status}
                        <GenreTag variant="status"
                            >{metadata.status || item?.status}</GenreTag
                        >
                    {/if}
                </div>

                <!-- Title -->
                <h1 class="title">{displayName}</h1>

                <!-- Creator info -->
                {#if metadata.writer || item?.writer || metadata.artist || item?.artist}
                    <div class="creators">
                        {#if metadata.writer || item?.writer}
                            <span class="creator-item">
                                <User class="icon" />
                                {metadata.writer || item?.writer}
                            </span>
                        {/if}
                        {#if (metadata.artist || item?.artist) && (metadata.artist || item?.artist) !== (metadata.writer || item?.writer)}
                            <span class="creator-item">
                                <FileText class="icon" />
                                {metadata.artist || item?.artist}
                            </span>
                        {/if}
                    </div>
                {/if}

                <!-- Stats row -->
                <div class="stats-row">
                    {#if metadata.rating || item?.rating}
                        <StarRating
                            rating={metadata.rating || item?.rating || 0}
                        />
                    {/if}
                    {#if metadata.publisher || item?.publisher}
                        <span class="stat-item">
                            <Layers class="icon" />
                            {metadata.publisher || item?.publisher}
                        </span>
                    {/if}
                    {#if metadata.year || item?.year}
                        <span class="stat-item">
                            <Calendar class="icon" />
                            {metadata.year || item?.year}
                        </span>
                    {/if}
                    {#if !isComic && totalCount > 0}
                        <span class="stat-item">
                            <BookOpen class="icon" />
                            {totalCount} issues
                        </span>
                    {/if}
                    {#if isComic && item?.num_pages}
                        <span class="stat-item">
                            <FileText class="icon" />
                            {item.num_pages} pages
                        </span>
                    {/if}
                </div>

                <!-- Action buttons -->
                <div class="action-buttons">
                    {#if onStartReading}
                        <button class="btn-primary" on:click={onStartReading}>
                            <Play class="icon" />
                            {buttonText}
                        </button>
                    {:else if item?.nextVolumeToRead || (item?.volumes && item.volumes.length > 0)}
                        <a
                            href="/comic/{libraryId}/{item?.nextVolumeToRead
                                ?.id || item?.volumes?.[0]?.id}/read"
                            class="btn-primary"
                        >
                            <Play class="icon" />
                            {buttonText}
                        </a>
                    {/if}
                    <button class="btn-secondary" class:is-favorite={isFav} on:click={toggleFavorite} disabled={favLoading || !favoriteComicId}>
                        <Heart class="icon" fill={isFav ? "currentColor" : "none"} />
                        {isFav ? 'Favorited' : 'Favorite'}
                    </button>
                    <button class="btn-secondary" on:click={() => showListModal = true} disabled={!favoriteComicId}>
                        <Bookmark class="icon" />
                        Add to List
                    </button>
                </div>

                <!-- Progress bar -->
                {#if progress > 0}
                    <div class="progress-section">
                        <div class="progress-header">
                            <span class="progress-label">Reading Progress</span>
                            <span class="progress-value">
                                {#if isComic}
                                    Page {item.current_page}/{item.num_pages}
                                {:else}
                                    {completedCount}/{totalCount} completed
                                {/if}
                            </span>
                        </div>
                        <div class="progress-bar-container">
                            <div
                                class="progress-bar-fill"
                                style="width: {progress}%"
                            ></div>
                        </div>
                    </div>
                {/if}

                <!-- Genres -->
                {#if genres.length > 0}
                    <div class="tags-row">
                        {#each genres as genre}
                            <GenreTag variant="genre">{genre}</GenreTag>
                        {/each}
                    </div>
                {/if}

                <!-- Tags -->
                {#if tags.length > 0}
                    <div class="tags-row">
                        {#each tags as tag}
                            <GenreTag variant="tag">{tag}</GenreTag>
                        {/each}
                    </div>
                {/if}

                <!-- Content warnings -->
                {#if contentWarnings.length > 0}
                    <div class="tags-row">
                        {#each contentWarnings as warning}
                            <GenreTag variant="warning">{warning}</GenreTag>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>

        <!-- Description/Synopsis -->
        {#if metadata.description || item?.synopsis}
            <div class="synopsis-section">
                <h3 class="synopsis-label">Synopsis</h3>
                <p class="synopsis-text" class:collapsed={!expanded}>
                    {metadata.description || item?.synopsis}
                </p>
                {#if (metadata.description || item?.synopsis || "").length > 200}
                    <button
                        class="expand-button"
                        on:click={() => (expanded = !expanded)}
                    >
                        {#if expanded}
                            <ChevronUp class="icon" />
                            Show less
                        {:else}
                            <ChevronDown class="icon" />
                            Show more
                        {/if}
                    </button>
                {/if}
            </div>
        {/if}
    </div>
</div>

<AddToListModal
    {libraryId}
    comicId={favoriteComicId}
    bind:show={showListModal}
/>

<style>
    .detail-header {
        position: relative;
        margin-bottom: 2rem;
    }

    .header-background {
        position: absolute;
        inset: 0;
        z-index: -1;
        overflow: hidden;
    }

    .gradient-blur {
        position: absolute;
        inset: 0;
        opacity: 0.3;
        filter: blur(60px);
    }

    .gradient-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            to bottom,
            rgba(9, 9, 11, 0.5),
            rgba(9, 9, 11, 0.8) 50%,
            rgba(9, 9, 11, 1)
        );
    }

    .header-content {
        padding: 1.5rem 1rem 2rem;
    }

    .back-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #a1a1aa;
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.5rem 0;
        margin-bottom: 1.5rem;
        font-size: 0.875rem;
        transition: color 0.2s;
    }

    .back-button:hover {
        color: white;
    }

    .back-button :global(.icon) {
        width: 1rem;
        height: 1rem;
        transition: transform 0.2s;
    }

    .back-button:hover :global(.icon) {
        transform: translateX(-4px);
    }

    .header-main {
        display: flex;
        gap: 1.5rem;
        flex-direction: column;
    }

    @media (min-width: 768px) {
        .header-main {
            flex-direction: row;
            gap: 2rem;
        }

        .header-content {
            padding: 1.5rem 2rem 2rem;
        }
    }

    .cover-wrapper {
        flex-shrink: 0;
        align-self: center;
    }

    @media (min-width: 768px) {
        .cover-wrapper {
            align-self: flex-start;
        }
    }

    .cover-container {
        position: relative;
        width: 14rem;
        height: 20rem;
        border-radius: 0.75rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
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
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 1rem;
    }

    .cover-placeholder :global(.placeholder-icon) {
        width: 33%;
        height: 33%;
        color: rgba(255, 255, 255, 0.6);
    }

    .placeholder-text {
        color: white;
        font-size: 0.875rem;
        font-weight: 500;
        text-align: center;
        line-clamp: 2;
        -webkit-line-clamp: 2;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .cover-shine {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            135deg,
            transparent 0%,
            rgba(255, 255, 255, 0.1) 50%,
            transparent 100%
        );
        opacity: 1;
        transition: opacity 0.5s;
    }

    .cover-container:hover .cover-shine {
        opacity: 1;
    }

    .info-section {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .badge-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .title {
        font-size: 1.75rem;
        font-weight: 700;
        color: white;
        line-height: 1.2;
        margin: 0;
    }

    @media (min-width: 768px) {
        .title {
            font-size: 2.25rem;
        }
    }

    .creators {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1rem;
        font-size: 0.875rem;
        color: #a1a1aa;
    }

    .creator-item {
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }

    .creator-item :global(.icon) {
        width: 1rem;
        height: 1rem;
    }

    .stats-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1rem;
        font-size: 0.875rem;
    }

    .stat-item {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        color: #a1a1aa;
    }

    .stat-item :global(.icon) {
        width: 1rem;
        height: 1rem;
    }

    .action-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        padding-top: 0.5rem;
    }

    .btn-primary {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1.25rem;
        background: #f97316;
        color: white;
        font-weight: 600;
        border-radius: 0.5rem;
        border: none;
        cursor: pointer;
        text-decoration: none;
        transition: background-color 0.2s;
    }

    .btn-primary:hover {
        background: #fb923c;
    }

    .btn-primary :global(.icon) {
        width: 1rem;
        height: 1rem;
    }

    .btn-secondary {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1rem;
        background: rgba(63, 63, 70, 0.8);
        color: white;
        border-radius: 0.5rem;
        border: 1px solid rgba(82, 82, 91, 0.7);
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .btn-secondary:hover {
        background: rgba(82, 82, 91, 0.8);
    }

    .btn-secondary :global(.icon) {
        width: 1rem;
        height: 1rem;
    }

    .btn-secondary.is-favorite {
        background: rgba(239, 68, 68, 0.2);
        border-color: rgba(239, 68, 68, 0.5);
        color: #ef4444;
    }

    .btn-secondary.is-favorite:hover {
        background: rgba(239, 68, 68, 0.3);
    }

    .btn-secondary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .progress-section {
        padding-top: 0.5rem;
    }

    .progress-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.25rem;
        font-size: 0.875rem;
    }

    .progress-label {
        color: #a1a1aa;
    }

    .progress-value {
        color: #fb923c;
        font-weight: 500;
    }

    .progress-bar-container {
        width: 100%;
        height: 0.375rem;
        background: rgba(63, 63, 70, 0.8);
        border-radius: 9999px;
        overflow: hidden;
    }

    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(to right, #f97316, #fb923c);
        transition: width 0.3s ease;
    }

    .tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .synopsis-section {
        margin-top: 1.5rem;
        max-width: 56rem;
    }

    .synopsis-label {
        font-size: 0.875rem;
        font-weight: 600;
        color: #a1a1aa;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0 0 0.5rem 0;
    }

    .synopsis-text {
        color: #d4d4d8;
        line-height: 1.6;
        margin: 0;
    }

    .synopsis-text.collapsed {
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .expand-button {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        color: #fb923c;
        background: none;
        border: none;
        cursor: pointer;
        font-size: 0.875rem;
        padding: 0;
        margin-top: 0.5rem;
        transition: color 0.2s;
    }

    .expand-button:hover {
        color: #fdba74;
    }

    .expand-button :global(.icon) {
        width: 1rem;
        height: 1rem;
    }
</style>
