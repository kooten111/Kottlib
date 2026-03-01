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
    import { addFavorite, removeFavorite, isFavorite } from "$lib/api/favorites";
    import AddToListModal from "$lib/components/common/AddToListModal.svelte";
    import GenreTag from "$lib/components/common/GenreTag.svelte";
    import { scanComic, applyComicMetadata } from "$lib/api/scanners";
    import { goto } from "$app/navigation";
    import { onMount } from "svelte";
    import { X, ExternalLink, Check, Loader2 } from "lucide-svelte";

    export let item; // Series/folder data
    export let libraryId;
    export let onBack = () => history.back();
    export let onScanSeries = null;
    export let isScanning = false;
    export let scanError = null;

    // Per-volume metadata mode props
    export let perVolumeMetadata = false;
    export let selectedComicId = null;
    export let firstComicId = null; // First comic ID for favorites (passed from parent)

    // Comic scanning state (for per-volume mode)
    let isScanningComic = false;
    let comicScanError = null;
    let comicScanCandidates = [];
    let showComicCandidateModal = false;
    let isApplyingComicCandidate = false;
    let selectedComicCandidateIndex = -1;

    // Track if a specific comic is selected (used for per-volume mode)
    $: hasSelectedComic = selectedComicId !== null;

    // Favorites state
    let isFav = false;
    let favLoading = false;
    let showListModal = false;

    // Get the comic ID for favorite operations
    // For per-volume mode: use selectedComicId (a real comic ID)
    // For series mode: use firstComicId prop (a real comic ID from items)
    $: favoriteComicId = perVolumeMetadata && selectedComicId
        ? selectedComicId
        : firstComicId || null;

    // Check favorite status when comic changes
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

    let synopsisExpanded = false;

    // Computed values
    $: coverHash = item?.cover_hash || item?.coverHash;
    $: displayName =
        item?.display_name || item?.series_name || item?.name || "Unknown";
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
        return value
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
    }

    // Parse tags into categorized structure (handles nhentai format: "tag:elf\nlanguage:translated")
    function parseTags(tagsValue) {
        if (!tagsValue) return {};
        const tagsString = typeof tagsValue === 'string' ? tagsValue : String(tagsValue);
        
        // Handle both newline-separated (nhentai format) and comma-separated
        const tagLines = tagsString.includes('\n') 
            ? tagsString.split('\n')
            : tagsString.split(',');
        
        return tagLines
            .filter((t) => t.trim())
            .reduce((acc, tagString) => {
                const trimmed = tagString.trim();
                if (trimmed.includes(':')) {
                    // Format: "tag:elf" or "language:translated"
                    const [tagType, tagName] = trimmed.split(':', 2);
                    const type = tagType.trim().toLowerCase();
                    const name = tagName.trim();
                    if (name) {
                        if (!acc[type]) acc[type] = [];
                        acc[type].push(name);
                    }
                } else {
                    // Plain tag without category
                    if (!acc.tag) acc.tag = [];
                    acc.tag.push(trimmed);
                }
                return acc;
            }, {});
    }

    $: genres = parseList(item?.genre);
    $: tags = parseList(item?.tags);
    $: tagsByType = perVolumeMetadata ? parseTags(item?.tags) : {};

    // Handle comic scanning in per-volume mode
    async function handleScanComic(overwrite = false) {
        if (!selectedComicId || !perVolumeMetadata) return;

        try {
            isScanningComic = true;
            comicScanError = null;
            comicScanCandidates = [];

            const result = await scanComic(selectedComicId, overwrite);

            if (result.success) {
                // Reload the page to show updated metadata
                // This ensures all metadata is fresh from the server
                window.location.reload();
            } else if (result.candidates && result.candidates.length > 0) {
                // Show candidates for manual selection
                comicScanCandidates = result.candidates;
                showComicCandidateModal = true;
            } else {
                comicScanError = result.error || "No matches found";
            }
        } catch (err) {
            comicScanError = err.message;
        } finally {
            isScanningComic = false;
        }
    }

    async function handleSelectComicCandidate(candidate, index) {
        if (!selectedComicId || !perVolumeMetadata) return;

        try {
            isApplyingComicCandidate = true;
            selectedComicCandidateIndex = index;

            const result = await applyComicMetadata(
                selectedComicId,
                candidate,
                false
            );

            if (result.success) {
                showComicCandidateModal = false;
                comicScanCandidates = [];
                window.location.reload();
            } else {
                comicScanError = result.error || "Failed to apply metadata";
            }
        } catch (err) {
            comicScanError = err.message;
        } finally {
            isApplyingComicCandidate = false;
            selectedComicCandidateIndex = -1;
        }
    }

    function closeComicCandidateModal() {
        showComicCandidateModal = false;
        comicScanCandidates = [];
    }

    // Handle reading the selected comic
    function handleReadComic() {
        if (!selectedComicId || !perVolumeMetadata) return;
        goto(`/comic/${libraryId}/${selectedComicId}/read`);
    }
</script>

<div class="series-info-panel">
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
                    <div class="cover-placeholder">
                        <Book class="placeholder-icon" />
                    </div>
                {/if}
            </div>
        </div>

        <!-- Title and badges -->
        <div class="title-section">
            <div class="badge-row">
                <GenreTag variant="default"
                    >{perVolumeMetadata ? "comic" : "series"}</GenreTag
                >
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
            {#if perVolumeMetadata && item?.num_pages}
                <div class="meta-item">
                    <Book class="icon" />
                    <span>{item.num_pages} pages</span>
                </div>
            {:else if totalCount > 0}
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
                    <span class="progress-value"
                        >{completedCount}/{totalCount}</span
                    >
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress}%"></div>
                </div>
            </div>
        {/if}

        <!-- Action buttons -->
        <div class="action-buttons">
            {#if perVolumeMetadata && selectedComicId}
                <!-- Read button for per-volume mode -->
                <button class="btn-read" on:click={handleReadComic}>
                    <BookOpen class="icon" />
                    <span>Read</span>
                </button>
            {/if}
            <button class="btn-action" class:is-favorite={isFav} on:click={toggleFavorite} disabled={favLoading || !favoriteComicId}>
                <Heart class="icon" fill={isFav ? "currentColor" : "none"} />
                <span>{isFav ? 'Favorited' : 'Favorite'}</span>
            </button>
            <button class="btn-action" on:click={() => showListModal = true} disabled={!favoriteComicId}>
                <Bookmark class="icon" />
                <span>Add to List</span>
            </button>
        </div>

        <!-- Synopsis -->
        {#if hasSynopsis}
            <div class="synopsis-section">
                <h3 class="section-label">Synopsis</h3>
                <p
                    class="synopsis-text"
                    class:collapsed={!synopsisExpanded && synopsisNeedsExpand}
                >
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

        <!-- Tags - Categorized display for per-volume metadata -->
        {#if perVolumeMetadata && Object.keys(tagsByType).length > 0}
            <div class="tags-section categorized-tags">
                <h3 class="section-label">Tags</h3>
                
                {#if tagsByType.parody?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Parodies</span>
                        <div class="tags-row">
                            {#each tagsByType.parody as tag}
                                <GenreTag variant="tag" class="tag-parody">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}

                {#if tagsByType.character?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Characters</span>
                        <div class="tags-row">
                            {#each tagsByType.character as tag}
                                <GenreTag variant="tag" class="tag-character">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}

                {#if tagsByType.artist?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Artists</span>
                        <div class="tags-row">
                            {#each tagsByType.artist as tag}
                                <GenreTag variant="tag" class="tag-artist">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}

                {#if tagsByType.group?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Groups</span>
                        <div class="tags-row">
                            {#each tagsByType.group as tag}
                                <GenreTag variant="tag" class="tag-group">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}

                {#if tagsByType.language?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Languages</span>
                        <div class="tags-row">
                            {#each tagsByType.language as tag}
                                <GenreTag variant="tag" class="tag-language">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}

                {#if tagsByType.category?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Categories</span>
                        <div class="tags-row">
                            {#each tagsByType.category as tag}
                                <GenreTag variant="tag" class="tag-category">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}

                {#if tagsByType.tag?.length > 0}
                    <div class="tag-category">
                        <span class="category-label">Content Tags</span>
                        <div class="tags-row">
                            {#each tagsByType.tag as tag}
                                <GenreTag variant="tag">{tag}</GenreTag>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        {:else if tags.length > 0}
            <!-- Fallback: Simple tag display for series-level metadata -->
            <div class="tags-section">
                <h3 class="section-label">Tags</h3>
                <div class="tags-row">
                    {#each tags as tag}
                        <GenreTag variant="tag">{tag}</GenreTag>
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Scanner status -->
        {#if perVolumeMetadata && selectedComicId}
            <!-- Per-volume mode: scan individual comic -->
            <div class="scanner-section">
                <div class="scanner-status">
                    {#if item?.scanner_source}
                        <span class="scanner-label">
                            Scanned via <strong>{item.scanner_source}</strong>
                        </span>
                        {#if item?.scan_confidence !== null && item?.scan_confidence !== undefined}
                            <span
                                class="confidence-badge"
                                class:high={item.scan_confidence >= 0.7}
                            >
                                {Math.round(item.scan_confidence * 100)}%
                            </span>
                        {/if}
                        {#if item?.scanner_source_url}
                            <a
                                href={item.scanner_source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="source-link"
                                title="View on {item.scanner_source}"
                            >
                                <ExternalLink size={12} />
                                View on {item.scanner_source}
                            </a>
                        {/if}
                    {:else}
                        <span class="scanner-label muted"
                            >No metadata scanned</span
                        >
                    {/if}
                </div>
                <button
                    class="btn-scan"
                    on:click={() => handleScanComic(!!item?.scanner_source)}
                    disabled={isScanningComic}
                >
                    {#if item?.scanner_source}
                        <RefreshCw
                            class="icon {isScanningComic ? 'spinning' : ''}"
                        />
                        {isScanningComic ? "Rescanning..." : "Rescan"}
                    {:else}
                        <Scan class="icon" />
                        {isScanningComic ? "Scanning..." : "Scan"}
                    {/if}
                </button>
                {#if comicScanError}
                    <div class="scan-error">{comicScanError}</div>
                {/if}
            </div>
        {:else if onScanSeries}
            <!-- Series mode: scan series/folder -->
            <div class="scanner-section">
                <div class="scanner-status">
                    {#if item?.scanner_source}
                        <span class="scanner-label">
                            Scanned via <strong>{item.scanner_source}</strong>
                        </span>
                        {#if item?.scan_confidence !== null && item?.scan_confidence !== undefined}
                            <span
                                class="confidence-badge"
                                class:high={item.scan_confidence >= 0.7}
                            >
                                {Math.round(item.scan_confidence * 100)}%
                            </span>
                        {/if}
                        {#if item?.scanner_source_url}
                            <a
                                href={item.scanner_source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="source-link"
                                title="View on {item.scanner_source}"
                            >
                                <ExternalLink size={12} />
                                View on {item.scanner_source}
                            </a>
                        {/if}
                    {:else}
                        <span class="scanner-label muted"
                            >No metadata scanned</span
                        >
                    {/if}
                </div>
                <button
                    class="btn-scan"
                    on:click={() => onScanSeries(!!item?.scanner_source)}
                    disabled={isScanning}
                >
                    {#if item?.scanner_source}
                        <RefreshCw
                            class="icon {isScanning ? 'spinning' : ''}"
                        />
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

<!-- Comic Candidate Selection Modal -->
{#if showComicCandidateModal && comicScanCandidates.length > 0}
    <div
        class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        on:click|self={closeComicCandidateModal}
        on:keydown={(e) => e.key === "Escape" && closeComicCandidateModal()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="comic-candidate-modal-title"
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
                        id="comic-candidate-modal-title"
                        class="text-xl font-bold text-dark-text"
                    >
                        Select Match
                    </h2>
                    <p class="text-sm text-accent-orange/80 mt-1">
                        No automatic match found. Choose from {comicScanCandidates.length}
                        candidate{comicScanCandidates.length > 1 ? "s" : ""} below:
                    </p>
                </div>
                <button
                    on:click={closeComicCandidateModal}
                    class="p-2 hover:bg-dark-bg-tertiary rounded-lg transition-colors text-dark-text-secondary hover:text-dark-text"
                    aria-label="Close modal"
                >
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Candidates List -->
            <div class="overflow-y-auto max-h-[calc(85vh-120px)] p-4 space-y-3">
                {#each comicScanCandidates as candidate, index}
                    <button
                        on:click={() => handleSelectComicCandidate(candidate, index)}
                        disabled={isApplyingComicCandidate}
                        class="w-full text-left p-4 rounded-xl border transition-all duration-200
                               {selectedComicCandidateIndex === index
                            ? 'border-status-success bg-status-success/20'
                            : 'bg-dark-bg-tertiary hover:border-accent-orange/50 hover:bg-accent-orange/10'}
                               disabled:opacity-50 disabled:cursor-not-allowed"
                        style="border-color: {selectedComicCandidateIndex === index
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
                                        {#if candidate.metadata.artists && candidate.metadata.artists.length > 0}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                Artist: {candidate.metadata.artists.join(', ')}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.groups && candidate.metadata.groups.length > 0}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                Group: {candidate.metadata.groups.join(', ')}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.writer}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                Writer: {candidate.metadata.writer}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.publisher}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                Publisher: {candidate.metadata.publisher}
                                            </span>
                                        {/if}
                                        {#if candidate.metadata.tags && candidate.metadata.tags.length > 0}
                                            <span
                                                class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary"
                                            >
                                                Tags: {candidate.metadata.tags.slice(0, 3).join(', ')}{candidate.metadata.tags.length > 3 ? '...' : ''}
                                            </span>
                                        {/if}
                                    </div>

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
                                {#if selectedComicCandidateIndex === index && isApplyingComicCandidate}
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
                                View Source
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
                        on:click={closeComicCandidateModal}
                        class="px-4 py-2 rounded-lg bg-dark-bg text-dark-text-secondary hover:bg-dark-bg-secondary transition-colors text-sm font-medium"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<AddToListModal
    {libraryId}
    comicId={favoriteComicId}
    bind:show={showListModal}
/>

<style>
    .series-info-panel {
        position: relative;
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: var(--color-border) transparent;
        background: var(--color-secondary-bg);
    }

    .panel-content {
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .back-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--color-text-secondary);
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.25rem 0;
        font-size: 0.875rem;
        transition: color 0.2s;
        width: fit-content;
    }

    .back-button:hover {
        color: var(--color-text);
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
        background: var(--color-tertiary-bg);
    }

    .cover-placeholder :global(.placeholder-icon) {
        width: 48px;
        height: 48px;
        color: var(--color-text-muted);
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
        color: var(--color-text);
        line-height: 1.3;
        margin: 0;
    }

    .metadata-section {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
        padding: 0.75rem;
        background: var(--color-tertiary-bg);
        border-radius: 0.5rem;
    }

    .meta-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8125rem;
        color: var(--color-text-secondary);
    }

    .meta-item :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
        flex-shrink: 0;
    }

    .progress-section {
        padding: 0.75rem;
        background: var(--color-tertiary-bg);
        border-radius: 0.5rem;
    }

    .progress-header {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-bottom: 0.375rem;
    }

    .progress-label {
        color: var(--color-text-secondary);
    }

    .progress-value {
        color: var(--color-accent);
        font-weight: 500;
    }

    .progress-bar {
        height: 4px;
        background: var(--color-border);
        border-radius: 2px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: var(--color-accent);
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
        background: var(--color-tertiary-bg);
        border: 1px solid var(--color-border);
        border-radius: 0.5rem;
        color: var(--color-text-secondary);
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-action:hover {
        background: var(--color-border);
        color: var(--color-text);
    }

    .btn-action :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
    }

    .btn-action.is-favorite {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.4);
        color: #ef4444;
    }

    .btn-action.is-favorite:hover {
        background: rgba(239, 68, 68, 0.25);
    }

    .btn-action:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-read {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        padding: 0.75rem;
        background: var(--color-accent);
        border: none;
        border-radius: 0.5rem;
        color: white;
        font-size: 0.875rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }

    .btn-read:hover {
        background: var(--color-accent-hover);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    .btn-read :global(.icon) {
        width: 1rem;
        height: 1rem;
    }

    .synopsis-section {
        padding: 0.75rem;
        background: var(--color-tertiary-bg);
        border-radius: 0.5rem;
    }

    .section-label {
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-text-secondary);
        margin: 0 0 0.5rem 0;
    }

    .synopsis-text {
        font-size: 0.8125rem;
        line-height: 1.5;
        color: var(--color-text);
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
        color: var(--color-accent);
        background: none;
        border: none;
        cursor: pointer;
        font-size: 0.75rem;
        padding: 0;
        margin-top: 0.5rem;
    }

    .expand-button:hover {
        color: var(--color-accent-hover);
    }

    .expand-button :global(.icon) {
        width: 0.875rem;
        height: 0.875rem;
    }

    .tags-section {
        margin-top: 1.5rem;
    }

    .tags-section .section-label {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--color-text-secondary);
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .tag-category {
        margin-bottom: 1rem;
    }

    .tag-category:last-child {
        margin-bottom: 0;
    }

    .category-label {
        display: block;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--color-text-secondary);
        margin-bottom: 0.5rem;
        opacity: 0.8;
    }

    .tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.375rem;
    }

    /* Tag type styling for categorized tags */
    :global(.tag-parody) {
        background: rgba(147, 51, 234, 0.15) !important;
        color: rgb(168, 85, 247) !important;
    }

    :global(.tag-character) {
        background: rgba(59, 130, 246, 0.15) !important;
        color: rgb(96, 165, 250) !important;
    }

    :global(.tag-artist) {
        background: rgba(34, 197, 94, 0.15) !important;
        color: rgb(74, 222, 128) !important;
    }

    :global(.tag-group) {
        background: rgba(249, 115, 22, 0.15) !important;
        color: rgb(251, 146, 60) !important;
    }

    :global(.tag-language) {
        background: rgba(234, 179, 8, 0.15) !important;
        color: rgb(250, 204, 21) !important;
    }

    :global(.tag-category) {
        background: rgba(236, 72, 153, 0.15) !important;
        color: rgb(244, 114, 182) !important;
    }

    .scanner-section {
        padding: 0.75rem;
        background: var(--color-tertiary-bg);
        border: 1px solid var(--color-border);
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
        color: var(--color-text-secondary);
    }

    .scanner-label.muted {
        color: var(--color-text-muted);
    }

    .scanner-label strong {
        color: var(--color-text);
    }

    .confidence-badge {
        padding: 0.125rem 0.375rem;
        font-size: 0.6875rem;
        font-weight: 500;
        border-radius: 0.25rem;
        background: color-mix(in srgb, var(--color-warning) 20%, transparent);
        color: var(--color-warning);
    }

    .confidence-badge.high {
        background: color-mix(in srgb, var(--color-success) 20%, transparent);
        color: var(--color-success);
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
        background: color-mix(
            in srgb,
            var(--color-accent-blue) 20%,
            transparent
        );
        color: var(--color-accent-blue);
    }

    .btn-scan:hover:not(:disabled) {
        background: color-mix(
            in srgb,
            var(--color-accent-blue) 30%,
            transparent
        );
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
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }

    .scan-error {
        padding: 0.5rem;
        background: color-mix(in srgb, var(--color-error) 20%, transparent);
        color: var(--color-error);
        border-radius: 0.375rem;
        font-size: 0.75rem;
    }

    .source-link {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.125rem 0.5rem;
        font-size: 0.6875rem;
        font-weight: 500;
        color: var(--color-accent-blue);
        background: color-mix(
            in srgb,
            var(--color-accent-blue) 12%,
            transparent
        );
        border-radius: 1rem;
        text-decoration: none;
        transition: all 0.2s;
        white-space: nowrap;
    }

    .source-link:hover {
        background: color-mix(
            in srgb,
            var(--color-accent-blue) 25%,
            transparent
        );
        text-decoration: none;
    }
</style>
