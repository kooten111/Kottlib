<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import Button from '$lib/components/common/Button.svelte';
	import { getComicInfo } from '$lib/api/comics';
	import { addFavorite, removeFavorite } from '$lib/api/favorites';
	import { Heart, Book, Play, ArrowLeft, ArrowRight } from 'lucide-svelte';

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
</script>

<svelte:head>
	<title>{comic ? comic.title || comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '') : 'Loading...'} - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		{#if isLoading}
			<div class="loading-container">
				<div class="spinner" />
				<p class="text-gray-400 mt-4">Loading comic...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="text-red-400">Failed to load comic: {error}</p>
				<a href="/browse" class="btn-primary mt-4">Back to Browse</a>
			</div>
		{:else if comic}
			<!-- Back Button -->
			<a href="/browse/{libraryId}" class="back-link">
				<ArrowLeft class="w-4 h-4" />
				<span>Back to Library</span>
			</a>

			<!-- Comic Detail Section -->
			<div class="comic-detail">
				<!-- Cover Image -->
				<div class="cover-container">
					<img
						src="/v2/library/{libraryId}/cover/{comic.hash}.jpg"
						alt={comic.title || comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '')}
						class="cover-image"
					/>
					{#if readProgress > 0}
						<div class="progress-overlay">
							<div class="progress-bar" style="width: {readProgress}%" />
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
								<span class="metadata-value">{comic.series}</span>
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

					<!-- Reading Progress -->
					{#if hasStarted}
						<div class="reading-progress">
							<div class="progress-info">
								<span class="progress-text">Reading Progress</span>
								<span class="progress-percentage">{Math.round(readProgress)}%</span>
							</div>
							<div class="progress-bar-container">
								<div class="progress-bar-fill" style="width: {readProgress}%" />
							</div>
						</div>
					{/if}

					<!-- Description -->
					{#if comic.synopsis}
						<div class="description">
							<h2 class="description-title">Description</h2>
							<p class="description-text">{comic.synopsis}</p>
						</div>
					{/if}

					<!-- Tags -->
					{#if comic.tags && comic.tags.length > 0}
						<div class="tags-section">
							<h3 class="tags-title">Tags</h3>
							<div class="tags">
								{#each comic.tags as tag}
									<span class="tag">{tag}</span>
								{/each}
							</div>
						</div>
					{/if}
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

	.back-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		margin-bottom: 2rem;
		transition: color 0.2s;
	}

	.back-link:hover {
		color: var(--color-text);
	}

	.comic-detail {
		display: grid;
		grid-template-columns: 300px 1fr;
		gap: 3rem;
		margin-bottom: 3rem;
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

	.progress-overlay {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 4px;
		background: rgba(0, 0, 0, 0.5);
		border-radius: 0 0 8px 8px;
		overflow: hidden;
	}

	.progress-bar {
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

	.reading-progress {
		padding: 1rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
	}

	.progress-info {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.progress-text {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
	}

	.progress-percentage {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-accent);
	}

	.progress-bar-container {
		height: 8px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-bar-fill {
		height: 100%;
		background: var(--color-accent);
		border-radius: 4px;
		transition: width 0.3s ease;
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

	.tags-section {
		margin-top: 1rem;
	}

	.tags-title {
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 0.75rem;
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.tag {
		padding: 0.375rem 0.75rem;
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-accent);
		border-radius: 9999px;
		font-size: 0.875rem;
		color: var(--color-text);
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
