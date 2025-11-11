<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import BackButton from '$lib/components/common/BackButton.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getSeriesDetail, getLibrary } from '$lib/api/libraries';
	import { getCoverUrl } from '$lib/api/comics';
	import { BookOpen, Calendar, User, Tag } from 'lucide-svelte';
	import { navigationContext } from '$lib/stores/library';

	$: libraryId = parseInt($page.params.libraryId);
	$: seriesName = decodeURIComponent($page.params.seriesName);

	let series = null;
	let library = null;
	let isLoading = true;
	let error = null;
	let sortedVolumes = [];
	let nextVolumeToRead = null;
	let hasStartedReading = false;

	onMount(async () => {
		await loadSeriesData();
	});

	$: if (libraryId || seriesName) {
		loadSeriesData();
	}

	async function loadSeriesData() {
		try {
			isLoading = true;
			error = null;

			// Load library info
			library = await getLibrary(libraryId);

			// Load series detail
			series = await getSeriesDetail(libraryId, seriesName);

			// Sort volumes by title naturally (v01, v02, v03, etc.)
			if (series && series.volumes) {
				sortedVolumes = [...series.volumes].sort((a, b) => {
					return a.title.localeCompare(b.title, undefined, {
						numeric: true,
						sensitivity: 'base'
					});
				});

				// Determine which volume to read next
				// Priority:
				// 1. First volume with progress but not completed (continue reading)
				// 2. First uncompleted volume (start reading next)
				// 3. First volume (start from beginning)
				const volumeWithProgress = sortedVolumes.find(v => v.current_page > 0 && !v.is_completed);
				const firstUnread = sortedVolumes.find(v => !v.is_completed);
				nextVolumeToRead = volumeWithProgress || firstUnread || sortedVolumes[0];

				// Check if user has started reading any volume
				hasStartedReading = sortedVolumes.some(v => v.current_page > 0);
			}

			// Update navigation context for continue reading filtering
			navigationContext.set({
				type: 'series',
				libraryId: libraryId,
				seriesName: seriesName,
				seriesNames: [seriesName]
			});

			isLoading = false;
		} catch (err) {
			console.error('Failed to load series:', err);
			error = err.message;
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>{series ? series.series_name : 'Loading...'} - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 overflow-y-auto">
		<div class="container mx-auto px-4 py-8 max-w-content">
			{#if isLoading}
				<div class="loading-container">
					<div class="spinner" />
					<p class="text-gray-400 mt-4">Loading series...</p>
				</div>
			{:else if error}
				<div class="error-container">
					<p class="text-red-400">Failed to load series: {error}</p>
					<a href="/" class="btn-primary mt-4">Go Back</a>
				</div>
			{:else if series}
				<!-- Back Button -->
				<BackButton href="/" label="Home" />

				<!-- Series Header -->
				<div class="series-header">
					<div class="series-cover">
						<img
							src={getCoverUrl(libraryId, series.cover_hash)}
							alt={series.series_name}
							class="cover-image"
						/>
					</div>

					<div class="series-info">
						<h1 class="series-title">{series.series_name}</h1>

						<div class="series-meta">
							{#if series.publisher}
								<div class="meta-item">
									<Tag class="w-4 h-4" />
									<span>{series.publisher}</span>
								</div>
							{/if}
							{#if series.year}
								<div class="meta-item">
									<Calendar class="w-4 h-4" />
									<span>{series.year}</span>
								</div>
							{/if}
							<div class="meta-item">
								<BookOpen class="w-4 h-4" />
								<span>{series.total_issues} {series.total_issues === 1 ? 'issue' : 'issues'}</span>
							</div>
						</div>

						{#if series.synopsis}
							<div class="series-synopsis">
								<p>{series.synopsis}</p>
							</div>
						{/if}

						<!-- Start/Continue Reading Button -->
						{#if nextVolumeToRead}
							<div class="reading-actions">
								<a
									href="/comic/{libraryId}/{nextVolumeToRead.id}/read"
									class="btn-reading"
								>
									<BookOpen class="w-5 h-5" />
									{hasStartedReading ? 'Continue Reading' : 'Start Reading'}
								</a>
							</div>
						{/if}

						<!-- Reading Progress -->
						<div class="reading-progress">
							<div class="progress-header">
								<span class="progress-label">Reading Progress</span>
								<span class="progress-stats">
									{series.completed_volumes} / {series.total_issues} completed
									({Math.round(series.overall_progress)}%)
								</span>
							</div>
							<div class="progress-bar">
								<div
									class="progress-fill"
									style="width: {series.overall_progress}%"
								/>
							</div>
						</div>
					</div>
				</div>

				<!-- Volumes Section -->
				<section class="volumes-section">
					<h2 class="section-title">Volumes</h2>
					<div class="volumes-grid">
						{#each sortedVolumes as volume}
							<ComicCard
								comic={{
									id: parseInt(volume.id),
									title: volume.title,
									hash: volume.hash,
									num_pages: volume.num_pages,
									current_page: volume.current_page,
									read: volume.is_completed
								}}
								{libraryId}
								variant="grid"
								showProgress={true}
							/>
						{/each}
					</div>
				</section>
			{/if}
		</div>
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

	.series-header {
		display: flex;
		gap: 2rem;
		margin-bottom: 3rem;
		padding: 2rem;
		background: var(--color-secondary-bg);
		border-radius: 12px;
	}

	.series-cover {
		flex-shrink: 0;
		width: 240px;
	}

	.cover-image {
		width: 100%;
		height: auto;
		border-radius: 8px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	.series-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.series-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.series-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1.5rem;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.series-synopsis {
		flex: 1;
	}

	.series-synopsis p {
		color: var(--color-text-secondary);
		line-height: 1.6;
		margin: 0;
	}

	.reading-actions {
		display: flex;
		gap: 1rem;
		margin-top: 1rem;
	}

	.btn-reading {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: #ff6740;
		color: white;
		font-weight: 600;
		font-size: 1rem;
		border-radius: 8px;
		text-decoration: none;
		transition: all 0.2s ease;
		box-shadow: 0 2px 8px rgba(255, 103, 64, 0.3);
	}

	.btn-reading:hover {
		background: #ff8a5c;
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(255, 103, 64, 0.4);
	}

	.btn-reading:active {
		transform: translateY(0);
	}

	.reading-progress {
		margin-top: auto;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.progress-label {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.progress-stats {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
	}

	.progress-bar {
		width: 100%;
		height: 8px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: var(--color-accent);
		border-radius: 4px;
		transition: width 0.3s ease;
	}

	.volumes-section {
		margin-top: 2rem;
	}

	.section-title {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 1.5rem;
	}

	.volumes-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
	}

	@media (max-width: 768px) {
		.series-header {
			flex-direction: column;
			padding: 1.5rem;
		}

		.series-cover {
			width: 100%;
			max-width: 240px;
			margin: 0 auto;
		}

		.series-title {
			font-size: 1.5rem;
		}

		.volumes-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}
	}
</style>
