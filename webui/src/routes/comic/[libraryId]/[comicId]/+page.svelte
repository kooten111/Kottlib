<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import Button from '$lib/components/common/Button.svelte';
	import ScannerMetadata from '$lib/components/comic/ScannerMetadata.svelte';
	import { getComicInfo } from '$lib/api/comics';
	import { addFavorite, removeFavorite } from '$lib/api/favorites';
	import { Heart, Book, Play, ArrowLeft, ArrowRight, Library } from 'lucide-svelte';

	$: libraryId = parseInt($page.params.libraryId);
	$: comicId = parseInt($page.params.comicId);

	let comic = null;
	let relatedComics = [];
	let isLoading = true;
	let error = null;
	let isFavorite = false;
	let favoriteLoading = false;

	onMount(async () => {
		await loadComicData();
	});

	function handleBack() {
		// Check if there's a history to go back to
		if (window.history.length > 1) {
			window.history.back();
		} else {
			// Fallback to home page if no history
			goto('/');
		}
	}

	async function loadComicData() {
		try {
			isLoading = true;
			error = null;

			// Load comic info
			const comicData = await getComicInfo(libraryId, comicId);
			comic = comicData;
			isFavorite = comic.favorite || false;

			// TODO: Load related comics (same series)
			// For now, we'll leave this empty
			relatedComics = [];

			isLoading = false;
		} catch (err) {
			console.error('Failed to load comic:', err);
			error = err.message;
			isLoading = false;
		}
	}

	async function handleFavoriteToggle() {
		try {
			favoriteLoading = true;

			if (isFavorite) {
				await removeFavorite(libraryId, comicId);
				isFavorite = false;
			} else {
				await addFavorite(libraryId, comicId);
				isFavorite = true;
			}

			favoriteLoading = false;
		} catch (err) {
			console.error('Failed to toggle favorite:', err);
			favoriteLoading = false;
		}
	}

	function handleRead() {
		window.location.href = `/comic/${libraryId}/${comicId}/read`;
	}

	function handleContinue() {
		window.location.href = `/comic/${libraryId}/${comicId}/read?page=${comic.current_page || comic.currentPage || 1}`;
	}

	$: readProgress = comic ? ((comic.current_page || comic.currentPage || 0) / (comic.num_pages || comic.numPages || 1)) * 100 : 0;
	$: hasStarted = comic && (comic.current_page || comic.currentPage || 0) > 0;

	// Determine series name for navigation - use series metadata or fallback to path-based series
	$: seriesName = comic?.series || getSeriesFromPath(comic?.path || comic?.file_name);

	function getSeriesFromPath(path) {
		if (!path) return null;
		// Extract series from path like "/Series Name/Volume 1/chapter.cbz"
		const parts = path.split('/').filter(p => p);
		// Return the first folder (typically the series name)
		return parts.length > 1 ? parts[0] : null;
	}

	function handleViewSeries() {
		if (seriesName) {
			goto(`/series/${libraryId}/${encodeURIComponent(seriesName)}`);
		}
	}
</script>

<svelte:head>
	<title>{comic ? comic.title || comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '') : 'Loading...'} - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		{#if isLoading}
			<div class="loading-container">
				<div class="spinner"></div>
				<p class="text-gray-400 mt-4">Loading comic...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="text-red-400">Failed to load comic: {error}</p>
				<a href="/" class="btn-primary mt-4">Back to Home</a>
			</div>
		{:else if comic}
			<!-- Navigation Buttons -->
			<div class="nav-buttons">
				<button on:click={handleBack} class="nav-button">
					<ArrowLeft class="w-4 h-4" />
					<span>Back</span>
				</button>
				{#if seriesName}
					<button on:click={handleViewSeries} class="nav-button">
						<Library class="w-4 h-4" />
						<span>View Series</span>
					</button>
				{/if}
			</div>

			<!-- Comic Detail Section -->
			<div class="comic-detail">
				<!-- Cover Image -->
				<div class="cover-section">
					<div class="cover-container">
						<img
							src="/v2/library/{libraryId}/cover/{comic.hash}.jpg"
							alt={comic.title || comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '')}
							class="cover-image"
						/>
					</div>
					{#if readProgress > 0}
						<div class="small-progress-bar">
							<div class="small-progress-fill" style="width: {readProgress}%"></div>
						</div>
					{/if}
				</div>

				<!-- Comic Info -->
				<div class="info-container">
					<h1 class="comic-title">{comic.title || comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '')}</h1>

					<!-- Metadata -->
					<div class="metadata">
						{#if comic.series}
							<div class="metadata-item">
								<span class="metadata-label">Series:</span>
								<a href="/series/{libraryId}/{encodeURIComponent(comic.series)}" class="metadata-value series-link">
									{comic.series}
								</a>
							</div>
						{/if}
						{#if comic.volume}
							<div class="metadata-item">
								<span class="metadata-label">Volume:</span>
								<span class="metadata-value">{comic.volume}</span>
							</div>
						{/if}
						{#if comic.number}
							<div class="metadata-item">
								<span class="metadata-label">Issue:</span>
								<span class="metadata-value">#{comic.number}</span>
							</div>
						{/if}
						{#if comic.publisher}
							<div class="metadata-item">
								<span class="metadata-label">Publisher:</span>
								<span class="metadata-value">{comic.publisher}</span>
							</div>
						{/if}
						{#if comic.year}
							<div class="metadata-item">
								<span class="metadata-label">Year:</span>
								<span class="metadata-value">{comic.year}</span>
							</div>
						{/if}
						{#if comic.writer}
							<div class="metadata-item">
								<span class="metadata-label">Writer:</span>
								<span class="metadata-value">{comic.writer}</span>
							</div>
						{/if}
						{#if comic.penciller}
							<div class="metadata-item">
								<span class="metadata-label">Artist:</span>
								<span class="metadata-value">{comic.penciller}</span>
							</div>
						{/if}
						<div class="metadata-item">
							<span class="metadata-label">Pages:</span>
							<span class="metadata-value">{comic.num_pages || comic.numPages}</span>
						</div>
					</div>

					<!-- Action Buttons -->
					<div class="actions">
						{#if hasStarted}
							<Button variant="primary" on:click={handleContinue}>
								<Play class="w-5 h-5 mr-2" />
								Continue Reading (Page {comic.current_page || comic.currentPage})
							</Button>
							<Button variant="secondary" on:click={handleRead}>
								<Book class="w-5 h-5 mr-2" />
								Start Over
							</Button>
						{:else}
							<Button variant="primary" on:click={handleRead}>
								<Book class="w-5 h-5 mr-2" />
								Start Reading
							</Button>
						{/if}

						<button
							class="favorite-button"
							class:active={isFavorite}
							on:click={handleFavoriteToggle}
							disabled={favoriteLoading}
							aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
						>
							<Heart class="w-5 h-5" fill={isFavorite ? 'currentColor' : 'none'} />
						</button>
					</div>

					<!-- Description -->
					{#if comic.synopsis}
						<div class="description">
							<h2 class="description-title">Description</h2>
							<p class="description-text">{comic.synopsis}</p>
						</div>
					{/if}

					<!-- Scanner Metadata -->
					<ScannerMetadata {libraryId} {comicId} comic={comic} on:updated={loadComicData} />
				</div>
			</div>

			<!-- Related Comics Section -->
			{#if relatedComics.length > 0}
				<section class="related-section">
					<h2 class="section-title">More from this Series</h2>
					<div class="comics-grid">
						{#each relatedComics as relatedComic}
							<ComicCard comic={relatedComic} {libraryId} />
						{/each}
					</div>
				</section>
			{/if}
		{/if}
	</main>
</div>

<style>
	.loading-container,
	.error-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
	}

	.spinner {
		width: 64px;
		height: 64px;
		border: 4px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.nav-buttons {
		display: flex;
		gap: 1rem;
		margin-bottom: 2rem;
		flex-wrap: wrap;
	}

	.nav-button {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		transition: color 0.2s;
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;
		font-family: inherit;
	}

	.nav-button:hover {
		color: var(--color-text);
	}

	.comic-detail {
		display: grid;
		grid-template-columns: 300px 1fr;
		gap: 3rem;
		margin-bottom: 3rem;
	}

	.cover-section {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.cover-container {
		position: relative;
	}

	.cover-image {
		width: 100%;
		height: auto;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	.small-progress-bar {
		height: 6px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 3px;
		overflow: hidden;
	}

	.small-progress-fill {
		height: 100%;
		background: var(--color-accent);
		transition: width 0.3s ease;
	}

	.info-container {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.comic-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.metadata {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 0.75rem;
	}

	.metadata-item {
		display: flex;
		gap: 0.5rem;
	}

	.metadata-label {
		font-weight: 600;
		color: var(--color-text-secondary);
		min-width: 80px;
	}

	.metadata-value {
		color: var(--color-text);
	}

	.series-link {
		color: var(--color-accent);
		text-decoration: none;
		transition: opacity 0.2s;
	}

	.series-link:hover {
		opacity: 0.8;
		text-decoration: underline;
	}

	.actions {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.favorite-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		border-radius: 4px;
		background: var(--color-secondary-bg);
		border: 1px solid transparent;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.favorite-button:hover {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	.favorite-button.active {
		color: #ff6740;
	}

	.favorite-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.description {
		padding: 1.5rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
	}

	.description-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 1rem 0;
	}

	.description-text {
		font-size: 1rem;
		line-height: 1.6;
		color: var(--color-text-secondary);
		margin: 0;
	}

	.related-section {
		margin-top: 3rem;
	}

	.section-title {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 1.5rem;
	}

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
	}

	@media (max-width: 768px) {
		.comic-detail {
			grid-template-columns: 1fr;
			gap: 2rem;
		}

		.cover-container {
			max-width: 300px;
			margin: 0 auto;
		}

		.comic-title {
			font-size: 1.5rem;
		}

		.metadata {
			grid-template-columns: 1fr;
		}

		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}
	}
</style>
