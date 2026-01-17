<script>
	/**
	 * MetadataDisplay - Unified metadata display component
	 *
	 * Renders comic metadata consistently based on available data and scanner capabilities.
	 * Combines functionality from DetailHeader and ScannerMetadata.
	 *
	 * Features:
	 * - Displays standard comic fields (title, series, writer, artist, etc.)
	 * - Shows scanner-specific metadata (tags, parodies, characters)
	 * - Adapts display based on scanner capabilities
	 * - Provides scan/rescan actions
	 */
	import {
		User,
		Pen,
		Calendar,
		BookOpen,
		Layers,
		ExternalLink,
		Globe,
		Tag,
		RefreshCw,
		Trash2,
		Scan,
	} from "lucide-svelte";
	import { scanComic, clearMetadata } from "$lib/api/scanners";

	export let comic;
	export let showScannerActions = true;
	export let compact = false;

	let isScanning = false;
	let isClearing = false;
	let error = null;

	// Parse tags into categorized structure
	function parseTags(tagsString) {
		if (!tagsString) return {};
		return tagsString
			.split("\n")
			.filter((t) => t.trim())
			.reduce((acc, tagString) => {
				const [tagType, tagName] = tagString.includes(":")
					? tagString.split(":", 2)
					: ["tag", tagString];
				if (!acc[tagType]) acc[tagType] = [];
				acc[tagType].push(tagName);
				return acc;
			}, {});
	}

	// Parse comma-separated strings
	function parseList(value) {
		if (!value) return [];
		if (Array.isArray(value)) return value;
		return value
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
	}

	$: tagsByType = parseTags(comic?.tags);
	$: genres = parseList(comic?.genre);
	$: characters = parseList(comic?.characters);
	$: teams = parseList(comic?.teams);
	$: locations = parseList(comic?.locations);

	// Standard metadata fields
	$: hasCreators = comic?.writer || comic?.artist;
	$: hasExtendedCreators =
		comic?.penciller ||
		comic?.inker ||
		comic?.colorist ||
		comic?.letterer ||
		comic?.cover_artist ||
		comic?.editor;
	$: hasScannerData = comic?.scanner_source;

	async function handleScan(overwrite = false) {
		try {
			isScanning = true;
			error = null;
			const result = await scanComic(comic.id, overwrite);
			if (result.success) {
				window.location.reload();
			} else {
				error = result.error || "Scan failed";
			}
		} catch (err) {
			error = err.message;
		} finally {
			isScanning = false;
		}
	}

	async function handleClear() {
		if (!confirm("Clear scanner metadata for this comic?")) return;
		try {
			isClearing = true;
			error = null;
			await clearMetadata({
				comicIds: [comic.id],
				clearScannerInfo: true,
				clearTags: true,
				clearMetadata: false,
			});
			window.location.reload();
		} catch (err) {
			error = err.message;
		} finally {
			isClearing = false;
		}
	}
</script>

<div class="metadata-display" class:compact>
	<!-- Core Metadata -->
	<section class="metadata-section">
		<h3 class="section-title">Details</h3>

		<div class="metadata-grid">
			{#if comic?.series}
				<div class="metadata-item">
					<span class="label">Series</span>
					<span class="value">{comic.series}</span>
				</div>
			{/if}

			{#if comic?.volume}
				<div class="metadata-item">
					<span class="label">Volume</span>
					<span class="value">{comic.volume}</span>
				</div>
			{/if}

			{#if comic?.issue_number}
				<div class="metadata-item">
					<span class="label">Issue</span>
					<span class="value">#{comic.issue_number}</span>
				</div>
			{/if}

			{#if comic?.year}
				<div class="metadata-item">
					<span class="label">Year</span>
					<span class="value">{comic.year}</span>
				</div>
			{/if}

			{#if comic?.publisher}
				<div class="metadata-item">
					<span class="label">Publisher</span>
					<span class="value">{comic.publisher}</span>
				</div>
			{/if}

			{#if comic?.num_pages}
				<div class="metadata-item">
					<span class="label">Pages</span>
					<span class="value">{comic.num_pages}</span>
				</div>
			{/if}

			{#if comic?.language_iso}
				<div class="metadata-item">
					<span class="label">Language</span>
					<span class="value">{comic.language_iso.toUpperCase()}</span>
				</div>
			{/if}

			{#if comic?.age_rating}
				<div class="metadata-item">
					<span class="label">Rating</span>
					<span class="value">{comic.age_rating}</span>
				</div>
			{/if}
		</div>
	</section>

	<!-- Creators -->
	{#if hasCreators || hasExtendedCreators}
		<section class="metadata-section">
			<h3 class="section-title">Creators</h3>

			<div class="creators-list">
				{#if comic?.writer}
					<div class="creator-item">
						<User class="icon" />
						<span class="role">Writer</span>
						<span class="name">{comic.writer}</span>
					</div>
				{/if}

				{#if comic?.artist && comic.artist !== comic.writer}
					<div class="creator-item">
						<Pen class="icon" />
						<span class="role">Artist</span>
						<span class="name">{comic.artist}</span>
					</div>
				{/if}

				{#if comic?.penciller}
					<div class="creator-item">
						<span class="role">Penciller</span>
						<span class="name">{comic.penciller}</span>
					</div>
				{/if}

				{#if comic?.inker}
					<div class="creator-item">
						<span class="role">Inker</span>
						<span class="name">{comic.inker}</span>
					</div>
				{/if}

				{#if comic?.colorist}
					<div class="creator-item">
						<span class="role">Colorist</span>
						<span class="name">{comic.colorist}</span>
					</div>
				{/if}

				{#if comic?.letterer}
					<div class="creator-item">
						<span class="role">Letterer</span>
						<span class="name">{comic.letterer}</span>
					</div>
				{/if}

				{#if comic?.cover_artist}
					<div class="creator-item">
						<span class="role">Cover Artist</span>
						<span class="name">{comic.cover_artist}</span>
					</div>
				{/if}

				{#if comic?.editor}
					<div class="creator-item">
						<span class="role">Editor</span>
						<span class="name">{comic.editor}</span>
					</div>
				{/if}
			</div>
		</section>
	{/if}

	<!-- Description -->
	{#if comic?.description}
		<section class="metadata-section">
			<h3 class="section-title">Synopsis</h3>
			<p class="description">{comic.description}</p>
		</section>
	{/if}

	<!-- Genres -->
	{#if genres.length > 0}
		<section class="metadata-section">
			<h3 class="section-title">Genres</h3>
			<div class="tags-list">
				{#each genres as genre}
					<span class="tag-badge tag-genre">{genre}</span>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Scanner-specific Tags -->
	{#if Object.keys(tagsByType).length > 0}
		<section class="metadata-section">
			<h3 class="section-title">Tags</h3>

			{#if tagsByType.parody?.length > 0}
				<div class="tag-category">
					<span class="category-label">Parodies</span>
					<div class="tags-list">
						{#each tagsByType.parody as tag}
							<span class="tag-badge tag-parody">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if tagsByType.character?.length > 0}
				<div class="tag-category">
					<span class="category-label">Characters</span>
					<div class="tags-list">
						{#each tagsByType.character as tag}
							<span class="tag-badge tag-character">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if tagsByType.artist?.length > 0}
				<div class="tag-category">
					<span class="category-label">Artists</span>
					<div class="tags-list">
						{#each tagsByType.artist as tag}
							<span class="tag-badge tag-artist">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if tagsByType.group?.length > 0}
				<div class="tag-category">
					<span class="category-label">Groups</span>
					<div class="tags-list">
						{#each tagsByType.group as tag}
							<span class="tag-badge tag-group">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if tagsByType.language?.length > 0}
				<div class="tag-category">
					<span class="category-label">Languages</span>
					<div class="tags-list">
						{#each tagsByType.language as tag}
							<span class="tag-badge tag-language">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if tagsByType.category?.length > 0}
				<div class="tag-category">
					<span class="category-label">Categories</span>
					<div class="tags-list">
						{#each tagsByType.category as tag}
							<span class="tag-badge tag-category">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if tagsByType.tag?.length > 0}
				<div class="tag-category">
					<span class="category-label">Content Tags</span>
					<div class="tags-list">
						{#each tagsByType.tag as tag}
							<span class="tag-badge tag-tag">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}
		</section>
	{/if}

	<!-- Characters (from standard field) -->
	{#if characters.length > 0 && !tagsByType.character?.length}
		<section class="metadata-section">
			<h3 class="section-title">Characters</h3>
			<div class="tags-list">
				{#each characters as character}
					<span class="tag-badge tag-character">{character}</span>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Teams -->
	{#if teams.length > 0}
		<section class="metadata-section">
			<h3 class="section-title">Teams</h3>
			<div class="tags-list">
				{#each teams as team}
					<span class="tag-badge tag-team">{team}</span>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Locations -->
	{#if locations.length > 0}
		<section class="metadata-section">
			<h3 class="section-title">Locations</h3>
			<div class="tags-list">
				{#each locations as location}
					<span class="tag-badge tag-location">{location}</span>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Story Arc -->
	{#if comic?.story_arc}
		<section class="metadata-section">
			<h3 class="section-title">Story Arc</h3>
			<div class="story-arc">
				<span class="arc-name">{comic.story_arc}</span>
				{#if comic.arc_number}
					<span class="arc-position">Part {comic.arc_number}</span>
				{/if}
				{#if comic.arc_count}
					<span class="arc-total">of {comic.arc_count}</span>
				{/if}
			</div>
		</section>
	{/if}

	<!-- Scanner Source Info -->
	{#if hasScannerData}
		<section class="metadata-section scanner-info">
			<h3 class="section-title">Source</h3>

			<div class="source-details">
				<div class="source-row">
					<span class="label">Provider</span>
					<span class="value">{comic.scanner_source}</span>
				</div>

				{#if comic.scanner_source_id}
					<div class="source-row">
						<span class="label">ID</span>
						<span class="value">{comic.scanner_source_id}</span>
					</div>
				{/if}

				{#if comic.scan_confidence !== null && comic.scan_confidence !== undefined}
					<div class="source-row">
						<span class="label">Confidence</span>
						<span
							class="value confidence"
							class:high={comic.scan_confidence >= 0.7}
						>
							{Math.round(comic.scan_confidence * 100)}%
						</span>
					</div>
				{/if}

				{#if comic.scanner_source_url}
					<div class="source-row">
						<a
							href={comic.scanner_source_url}
							target="_blank"
							rel="noopener noreferrer"
							class="source-link"
						>
							<Globe class="w-4 h-4" />
							View on {comic.scanner_source}
							<ExternalLink class="w-3 h-3" />
						</a>
					</div>
				{/if}
			</div>
		</section>
	{/if}

	<!-- Web Link -->
	{#if comic?.web && !comic?.scanner_source_url}
		<section class="metadata-section">
			<h3 class="section-title">External Link</h3>
			<a
				href={comic.web}
				target="_blank"
				rel="noopener noreferrer"
				class="external-link"
			>
				<Globe class="w-4 h-4" />
				View Source
				<ExternalLink class="w-3 h-3" />
			</a>
		</section>
	{/if}

	<!-- Scanner Actions -->
	{#if showScannerActions}
		<section class="metadata-section actions-section">
			{#if hasScannerData}
				<div class="action-buttons">
					<button
						on:click={() => handleScan(true)}
						disabled={isScanning}
						class="btn-action btn-rescan"
					>
						<RefreshCw class="w-4 h-4" />
						{isScanning ? "Rescanning..." : "Rescan"}
					</button>
					<button
						on:click={handleClear}
						disabled={isClearing}
						class="btn-action btn-clear"
					>
						<Trash2 class="w-4 h-4" />
						{isClearing ? "Clearing..." : "Clear"}
					</button>
				</div>
			{:else}
				<button
					on:click={() => handleScan(false)}
					disabled={isScanning}
					class="btn-action btn-scan"
				>
					<Scan class="w-4 h-4" />
					{isScanning ? "Scanning..." : "Scan for Metadata"}
				</button>
			{/if}
		</section>
	{/if}

	<!-- Error Message -->
	{#if error}
		<div class="error-message">{error}</div>
	{/if}
</div>

<style>
	.metadata-display {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.metadata-display.compact {
		gap: 1rem;
	}

	.metadata-section {
		background: rgba(255, 255, 255, 0.03);
		border-radius: 12px;
		padding: 1rem;
	}

	.section-title {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-text-secondary, #9ca3af);
		margin: 0 0 0.75rem 0;
	}

	.metadata-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
	}

	.metadata-item {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.metadata-item .label {
		font-size: 0.75rem;
		color: var(--color-text-secondary, #9ca3af);
	}

	.metadata-item .value {
		font-size: 0.875rem;
		color: var(--color-text, #e5e7eb);
	}

	.creators-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.creator-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.creator-item :global(.icon) {
		width: 1rem;
		height: 1rem;
		color: var(--color-text-secondary, #9ca3af);
	}

	.creator-item .role {
		color: var(--color-text-secondary, #9ca3af);
		min-width: 80px;
	}

	.creator-item .name {
		color: var(--color-text, #e5e7eb);
	}

	.description {
		font-size: 0.875rem;
		line-height: 1.6;
		color: var(--color-text, #d4d4d8);
		margin: 0;
	}

	.tag-category {
		margin-bottom: 0.75rem;
	}

	.tag-category:last-child {
		margin-bottom: 0;
	}

	.category-label {
		display: block;
		font-size: 0.75rem;
		color: var(--color-text-secondary, #9ca3af);
		margin-bottom: 0.5rem;
	}

	.tags-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.tag-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
		transition: all 0.2s;
	}

	.tag-badge:hover {
		transform: translateY(-1px);
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	.tag-badge.tag-genre {
		background: rgba(139, 92, 246, 0.2);
		color: #a78bfa;
	}

	.tag-badge.tag-artist {
		background: rgba(236, 72, 153, 0.2);
		color: #ec4899;
	}

	.tag-badge.tag-character {
		background: rgba(168, 85, 247, 0.2);
		color: #a855f7;
	}

	.tag-badge.tag-parody {
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
	}

	.tag-badge.tag-group {
		background: rgba(249, 115, 22, 0.2);
		color: #f97316;
	}

	.tag-badge.tag-language {
		background: rgba(59, 130, 246, 0.2);
		color: #3b82f6;
	}

	.tag-badge.tag-category,
	.tag-badge.tag-team {
		background: rgba(234, 179, 8, 0.2);
		color: #eab308;
	}

	.tag-badge.tag-location {
		background: rgba(20, 184, 166, 0.2);
		color: #14b8a6;
	}

	.tag-badge.tag-tag {
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
	}

	.story-arc {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.arc-name {
		color: var(--color-text, #e5e7eb);
		font-weight: 500;
	}

	.arc-position,
	.arc-total {
		color: var(--color-text-secondary, #9ca3af);
	}

	.scanner-info {
		background: rgba(96, 165, 250, 0.05);
		border: 1px solid rgba(96, 165, 250, 0.1);
	}

	.source-details {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.source-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.875rem;
	}

	.source-row .label {
		color: var(--color-text-secondary, #9ca3af);
		min-width: 80px;
	}

	.source-row .value {
		color: var(--color-text, #e5e7eb);
	}

	.source-row .value.confidence {
		color: #fbbf24;
	}

	.source-row .value.confidence.high {
		color: #34d399;
	}

	.source-link,
	.external-link {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		color: #60a5fa;
		text-decoration: none;
		font-size: 0.875rem;
		transition: color 0.2s;
	}

	.source-link:hover,
	.external-link:hover {
		color: #93c5fd;
	}

	.actions-section {
		background: transparent;
		padding: 0;
	}

	.action-buttons {
		display: flex;
		gap: 0.5rem;
	}

	.btn-action {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		font-weight: 500;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-rescan {
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
	}

	.btn-rescan:hover:not(:disabled) {
		background: rgba(96, 165, 250, 0.3);
	}

	.btn-clear {
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
	}

	.btn-clear:hover:not(:disabled) {
		background: rgba(239, 68, 68, 0.3);
	}

	.btn-scan {
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
	}

	.btn-scan:hover:not(:disabled) {
		background: rgba(34, 197, 94, 0.3);
	}

	.btn-action:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.error-message {
		padding: 0.75rem;
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
		border-radius: 6px;
		font-size: 0.875rem;
	}
</style>
