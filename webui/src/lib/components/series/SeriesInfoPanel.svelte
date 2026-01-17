<script>
    /**
     * SeriesInfoPanel - Compact sidebar component for series detail pages
     * 
     * Features:
     * - Cover image with gradient background
     * - Title and status badges
     * - Compact metadata (creators, year, issue count)
     * - Collapsible synopsis
     * - Genre and tag pills
     * - Action buttons (Favorite, Add to List)
     * - Scanner status and actions
     */
    import {
        ArrowLeft,
        Heart,
        Bookmark,
        User,
        Calendar,
        BookOpen,
        Layers,
        ChevronDown,
        ChevronUp,
        Book,
        Pen,
        RefreshCw,
        Scan,
    } from "lucide-svelte";
    import { getCoverUrl } from "$lib/api/comics";
    import GenreTag from "$lib/components/common/GenreTag.svelte";

    export let item; // Series/folder data
    export let libraryId;
    export let onBack = () => history.back();
    export let onScanSeries = null;
    export let isScanning = false;
    export let scanError = null;

    let synopsisExpanded = false;

    // Computed values
    $: coverHash = item?.cover_hash || item?.coverHash;
    $: displayName = item?.display_name || item?.series_name || item?.name || "Unknown";
    $: synopsis = item?.synopsis || item?.description || "";
    $: hasSynopsis = synopsis && synopsis.length > 0;
    $: synopsisNeedsExpand = synopsis.length > 200;

    // Progress calculation
    $: progress = item?.overall_progress || 0;
    $: completedCount = item?.completed_volumes || 0;
    $: totalCount = item?.total_issues || 0;

    // Parse genres and tags
    function parseList(value) {
        if (!value) return [];
        if (Array.isArray(value)) return value;
        return value.split(",").map((s) => s.trim()).filter(Boolean);
    }

    $: genres = parseList(item?.genre);
    $: tags = parseList(item?.tags);

    // Generate gradient colors from hash
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
</script>

<div class="series-info-panel">
    <!-- Background gradient effect -->
    <div class="panel-background">
        <div
            class="gradient-blur"
            style="background: linear-gradient(180deg, {gradientColors[0]}30, {gradientColors[1]}10);"
        ></div>
    </div>

    <div class="panel-content">
        <!-- Back button -->
        <button class="back-button" on:click={onBack}>
            <ArrowLeft class="icon" />
            <span>Back</span>
        </button>

        <!-- Cover -->
        <div class="cover-section">
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
                    </div>
                {/if}
            </div>
        </div>

        <!-- Title and badges -->
        <div class="title-section">
            <div class="badge-row">
                <GenreTag variant="default">series</GenreTag>
                {#if item?.status}
                    <GenreTag variant="status">{item.status}</GenreTag>
                {/if}
            </div>
            <h1 class="title">{displayName}</h1>
        </div>

        <!-- Metadata -->
        <div class="metadata-section">
            {#if item?.writer}
                <div class="meta-item">
                    <User class="icon" />
                    <span>{item.writer}</span>
                </div>
            {/if}
            {#if item?.artist && item.artist !== item.writer}
                <div class="meta-item">
                    <Pen class="icon" />
                    <span>{item.artist}</span>
                </div>
            {/if}
            {#if item?.publisher}
                <div class="meta-item">
                    <Layers class="icon" />
                    <span>{item.publisher}</span>
                </div>
            {/if}
            {#if item?.year}
                <div class="meta-item">
                    <Calendar class="icon" />
                    <span>{item.year}</span>
                </div>
            {/if}
            {#if totalCount > 0}
                <div class="meta-item">
                    <BookOpen class="icon" />
                    <span>{totalCount} issues</span>
                </div>
            {/if}
        </div>

        <!-- Progress bar -->
        {#if progress > 0}
            <div class="progress-section">
                <div class="progress-header">
                    <span class="progress-label">Progress</span>
                    <span class="progress-value">{completedCount}/{totalCount}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
            </div>
        {/if}

        <!-- Action buttons -->
        <div class="action-buttons">
            <button class="btn-action">
                <Heart class="icon" />
                <span>Favorite</span>
            </button>
            <button class="btn-action">
                <Bookmark class="icon" />
                <span>Add to List</span>
            </button>
        </div>

        <!-- Synopsis -->
        {#if hasSynopsis}
            <div class="synopsis-section">
                <h3 class="section-label">Synopsis</h3>
                <p class="synopsis-text" class:collapsed={!synopsisExpanded && synopsisNeedsExpand}>
                    {synopsis}
                </p>
                {#if synopsisNeedsExpand}
                    <button
                        class="expand-button"
                        on:click={() => (synopsisExpanded = !synopsisExpanded)}
                    >
                        {#if synopsisExpanded}
                            <ChevronUp class="icon" />
                            Less
                        {:else}
                            <ChevronDown class="icon" />
                            More
                        {/if}
                    </button>
                {/if}
            </div>
        {/if}

        <!-- Genres -->
        {#if genres.length > 0}
            <div class="tags-section">
                <div class="tags-row">
                    {#each genres as genre}
                        <GenreTag variant="genre">{genre}</GenreTag>
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Tags -->
        {#if tags.length > 0}
            <div class="tags-section">
                <div class="tags-row">
                    {#each tags.slice(0, 8) as tag}
                        <GenreTag variant="tag">{tag}</GenreTag>
                    {/each}
                    {#if tags.length > 8}
                        <span class="more-tags">+{tags.length - 8}</span>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- Scanner status -->
        {#if onScanSeries}
            <div class="scanner-section">
                <div class="scanner-status">
                    {#if item?.scanner_source}
                        <span class="scanner-label">
                            Scanned via <strong>{item.scanner_source}</strong>
                        </span>
                        {#if item?.scan_confidence !== null && item?.scan_confidence !== undefined}
                            <span class="confidence-badge" class:high={item.scan_confidence >= 0.7}>
                                {Math.round(item.scan_confidence * 100)}%
                            </span>
                        {/if}
                    {:else}
                        <span class="scanner-label muted">No metadata scanned</span>
                    {/if}
                </div>
                <button
                    class="btn-scan"
                    on:click={() => onScanSeries(!!item?.scanner_source)}
                    disabled={isScanning}
                >
                    {#if item?.scanner_source}
                        <RefreshCw class="icon {isScanning ? 'spinning' : ''}" />
                        {isScanning ? "Rescanning..." : "Rescan"}
                    {:else}
                        <Scan class="icon" />
                        {isScanning ? "Scanning..." : "Scan"}
                    {/if}
                </button>
                {#if scanError}
                    <div class="scan-error">{scanError}</div>
                {/if}
            </div>
        {/if}
    </div>
</div>

<style>
    .series-info-panel {
        position: relative;
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: var(--color-border) transparent;
    }

    .panel-background {
        position: absolute;
        inset: 0;
        z-index: 0;
        pointer-events: none;
    }

    .gradient-blur {
        position: absolute;
        inset: 0;
        opacity: 0.5;
    }

    .panel-content {
        position: relative;
        z-index: 1;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .back-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--color-text-secondary, #a1a1aa);
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.25rem 0;
        font-size: 0.875rem;
        transition: color 0.2s;
        width: fit-content;
    }

    .back-button:hover {
        color: white;
    }

    .back-button :global(.icon) {
        width: 1rem;
        height: 1rem;
    }

    .cover-section {
        display: flex;
        justify-content: center;
    }

    .cover-container {
        width: 180px;
        height: 260px;
        border-radius: 0.5rem;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
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
        align-items: center;
        justify-content: center;
    }

    .cover-placeholder :global(.placeholder-icon) {
        width: 48px;
        height: 48px;
        color: rgba(255, 255, 255, 0.5);
    }

    .title-section {
        text-align: center;
    }

    .badge-row {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
        flex-wrap: wrap;
    }

    .title {
        font-size: 1.25rem;
        font-weight: 700;
        color: white;
        line-height: 1.3;
        margin: 0;
    }

    .metadata-section {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
        padding: 0.75rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 0.5rem;
    }

    .meta-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8125rem;
        color: var(--color-text-secondary, #a1a1aa);
    }

    .meta-item :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
        flex-shrink: 0;
    }

    .progress-section {
        padding: 0.75rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 0.5rem;
    }

    .progress-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-bottom: 0.375rem;
    }

    .progress-label {
        color: var(--color-text-secondary, #a1a1aa);
    }

    .progress-value {
        color: var(--color-accent, #f97316);
        font-weight: 500;
    }

    .progress-bar {
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(to right, #f97316, #fb923c);
        transition: width 0.3s ease;
    }

    .action-buttons {
        display: flex;
        gap: 0.5rem;
    }

    .btn-action {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        padding: 0.5rem;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 0.5rem;
        color: var(--color-text-secondary, #a1a1aa);
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-action:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
    }

    .btn-action :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
    }

    .synopsis-section {
        padding: 0.75rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 0.5rem;
    }

    .section-label {
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-text-secondary, #a1a1aa);
        margin: 0 0 0.5rem 0;
    }

    .synopsis-text {
        font-size: 0.8125rem;
        line-height: 1.5;
        color: var(--color-text, #d4d4d8);
        margin: 0;
    }

    .synopsis-text.collapsed {
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .expand-button {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        color: var(--color-accent, #fb923c);
        background: none;
        border: none;
        cursor: pointer;
        font-size: 0.75rem;
        padding: 0;
        margin-top: 0.5rem;
    }

    .expand-button:hover {
        color: #fdba74;
    }

    .expand-button :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
    }

    .tags-section {
        /* No extra padding, just spacing */
    }

    .tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.375rem;
    }

    .more-tags {
        display: inline-flex;
        align-items: center;
        padding: 0.125rem 0.375rem;
        font-size: 0.6875rem;
        color: var(--color-text-secondary, #a1a1aa);
        background: rgba(255, 255, 255, 0.05);
        border-radius: 0.25rem;
    }

    .scanner-section {
        padding: 0.75rem;
        background: rgba(96, 165, 250, 0.05);
        border: 1px solid rgba(96, 165, 250, 0.1);
        border-radius: 0.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .scanner-status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .scanner-label {
        font-size: 0.75rem;
        color: var(--color-text-secondary, #9ca3af);
    }

    .scanner-label.muted {
        color: var(--color-text-muted, #6b7280);
    }

    .scanner-label strong {
        color: var(--color-text, #e5e7eb);
    }

    .confidence-badge {
        padding: 0.125rem 0.375rem;
        font-size: 0.6875rem;
        font-weight: 500;
        border-radius: 0.25rem;
        background: rgba(234, 179, 8, 0.2);
        color: #eab308;
    }

    .confidence-badge.high {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }

    .btn-scan {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        padding: 0.5rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 500;
        border: none;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: all 0.2s;
        background: rgba(96, 165, 250, 0.2);
        color: #60a5fa;
    }

    .btn-scan:hover:not(:disabled) {
        background: rgba(96, 165, 250, 0.3);
    }

    .btn-scan:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-scan :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
    }

    .btn-scan :global(.icon.spinning) {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .scan-error {
        padding: 0.5rem;
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border-radius: 0.375rem;
        font-size: 0.75rem;
    }
</style>
