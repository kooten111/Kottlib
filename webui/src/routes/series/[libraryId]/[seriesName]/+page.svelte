<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import BackButton from '$lib/components/common/BackButton.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getSeriesDetail, getLibrary } from '$lib/api/libraries';
	import { getCoverUrl } from '$lib/api/comics';
	import { BookOpen, Calendar, User, Tag, Search, Check, X } from 'lucide-svelte';
	import { navigationContext } from '$lib/stores/library';

	$: libraryId = parseInt($page.params.libraryId);
	$: seriesName = decodeURIComponent($page.params.seriesName);

	let series = null;
	let library = null;
	let scannerConfig = null;
	let isLoading = true;
	let error = null;
	let sortedVolumes = [];
	let nextVolumeToRead = null;
	let hasStartedReading = false;
	
	// Scanner state
	let isScanning = false;
	let scanResult = null;
	let scanError = null;
	let showMetadata = false;

	onMount(async () => {
		await loadSeriesData();
		await loadScannerConfig();
	});

	$: if (libraryId || seriesName) {
		loadSeriesData();
		loadScannerConfig();
	}

	async function loadScannerConfig() {
		try {
			const response = await fetch('/v2/scanners/libraries');
			if (!response.ok) throw new Error('Failed to load scanner config');
			const configs = await response.json();
			scannerConfig = configs.find(c => c.library_id === libraryId);
		} catch (err) {
			console.error('Failed to load scanner config:', err);
		}
	}

	async function scanSeriesMetadata() {
		try {
			isScanning = true;
			scanError = null;
			scanResult = null;

			const response = await fetch(`/v2/scanners/scan/series?library_id=${libraryId}&series_name=${encodeURIComponent(seriesName)}&overwrite=false`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || errorData.error || 'Scan failed');
			}

			const data = await response.json();
			
			if (!data.success) {
				throw new Error(data.error || 'Scan failed');
			}

			scanResult = {
				confidence: data.confidence,
				metadata: data.metadata,
				source_url: data.source_url,
				fields_updated: data.fields_updated
			};
			showMetadata = true;

			// Reload series data to show updated metadata
			await loadSeriesData();

		} catch (err) {
			console.error('Scan error:', err);
			scanError = err.message;
		} finally {
			isScanning = false;
		}
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
					<div class="spinner"></div>
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
						<h1 class="series-title">{series.display_name || series.series_name}</h1>

						<div class="series-meta">
							{#if series.writer}
								<div class="meta-item">
									<User class="w-4 h-4" />
									<span>{series.writer}</span>
								</div>
							{/if}
							{#if series.artist}
								<div class="meta-item">
									<User class="w-4 h-4" />
									<span>{series.artist}</span>
								</div>
							{/if}
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
							{#if series.genre}
								<div class="meta-item">
									<Tag class="w-4 h-4" />
									<span>{series.genre}</span>
								</div>
							{/if}
							{#if series.status}
								<div class="meta-item">
									<Tag class="w-4 h-4" />
									<span>{series.status}</span>
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
						
						{#if series.scanner_source_url}
							<div class="series-source">
								<a href={series.scanner_source_url} target="_blank" rel="noopener noreferrer" class="source-link">
									View on {series.scanner_source || 'source'}
								</a>
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
								></div>
							</div>
						</div>
					</div>
				</div>

				<!-- Scanner Section -->
				{#if scannerConfig?.primary_scanner && scannerConfig?.scan_level === 'series'}
					<div class="scanner-section">
						<div class="scanner-header">
							<h3 class="scanner-title">Series Metadata Scanner</h3>
							<button
								on:click={scanSeriesMetadata}
								disabled={isScanning}
								class="btn-scan-series"
							>
								<Search class="w-4 h-4" />
								{isScanning ? 'Scanning...' : 'Scan Metadata'}
							</button>
						</div>

						{#if scanError}
							<div class="scan-error">
								<X class="w-4 h-4" />
								<span>{scanError}</span>
							</div>
						{/if}

						{#if scanResult && showMetadata}
							<div class="scan-result">
								<div class="result-header">
									<div class="result-title">
										<Check class="w-5 h-5 text-green-400" />
										<span>Metadata Saved</span>
									</div>
									<div class="confidence-badge" class:high={scanResult.confidence >= 0.7}>
										{Math.round(scanResult.confidence * 100)}% Match
									</div>
								</div>

								<div class="fields-saved">
									<span class="saved-label">Updated Fields:</span>
									<span class="saved-count">{scanResult.fields_updated?.length || 0} fields</span>
								</div>

								<div class="metadata-grid">
									{#if scanResult.metadata?.title}
										<div class="metadata-item">
											<span class="metadata-label">Title:</span>
											<span class="metadata-value">{scanResult.metadata.title}</span>
										</div>
									{/if}
									{#if scanResult.metadata?.writer}
										<div class="metadata-item">
											<span class="metadata-label">Writer:</span>
											<span class="metadata-value">{scanResult.metadata.writer}</span>
										</div>
									{/if}
									{#if scanResult.metadata?.artist}
										<div class="metadata-item">
											<span class="metadata-label">Artist:</span>
											<span class="metadata-value">{scanResult.metadata.artist}</span>
										</div>
									{/if}
									{#if scanResult.metadata?.genre}
										<div class="metadata-item">
											<span class="metadata-label">Genres:</span>
											<span class="metadata-value">{scanResult.metadata.genre}</span>
										</div>
									{/if}
									{#if scanResult.metadata?.year}
										<div class="metadata-item">
											<span class="metadata-label">Year:</span>
											<span class="metadata-value">{scanResult.metadata.year}</span>
										</div>
									{/if}
									{#if scanResult.metadata?.status}
										<div class="metadata-item">
											<span class="metadata-label">Status:</span>
											<span class="metadata-value">{scanResult.metadata.status}</span>
										</div>
									{/if}
									{#if scanResult.metadata?.description}
										<div class="metadata-item full-width">
											<span class="metadata-label">Description:</span>
											<p class="metadata-description">{scanResult.metadata.description}</p>
										</div>
									{/if}
									{#if scanResult.source_url}
										<div class="metadata-item full-width">
											<span class="metadata-label">Source:</span>
											<a href={scanResult.source_url} target="_blank" class="metadata-link">
												{scanResult.source_url}
											</a>
										</div>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				{/if}

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

	.series-source {
		margin-top: 0.5rem;
	}

	.source-link {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		color: #60a5fa;
		font-size: 0.875rem;
		text-decoration: none;
		transition: color 0.2s;
	}

	.source-link:hover {
		color: #93c5fd;
		text-decoration: underline;
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

	.scanner-section {
		background: var(--color-secondary-bg);
		border-radius: 12px;
		padding: 2rem;
		margin-bottom: 3rem;
	}

	.scanner-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.scanner-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
	}

	.btn-scan-series {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
		border: 1px solid rgba(96, 165, 250, 0.3);
		border-radius: 8px;
		font-weight: 600;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-scan-series:hover:not(:disabled) {
		background: rgba(96, 165, 250, 0.3);
		border-color: rgba(96, 165, 250, 0.5);
	}

	.btn-scan-series:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.scan-error {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
		border-radius: 8px;
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.scan-result {
		background: rgba(0, 0, 0, 0.2);
		border-radius: 8px;
		padding: 1.5rem;
	}

	.result-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	}

	.result-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.confidence-badge {
		padding: 0.375rem 0.875rem;
		background: rgba(251, 191, 36, 0.2);
		color: #fbbf24;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.confidence-badge.high {
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
	}

	.fields-saved {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: rgba(34, 197, 94, 0.1);
		border-radius: 6px;
		margin-bottom: 1rem;
	}

	.saved-label {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
	}

	.saved-count {
		font-size: 0.875rem;
		font-weight: 600;
		color: #22c55e;
	}

	.metadata-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.metadata-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.metadata-item.full-width {
		grid-column: 1 / -1;
	}

	.metadata-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--color-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.metadata-value {
		color: var(--color-text);
		font-size: 0.875rem;
	}

	.metadata-description {
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		line-height: 1.6;
		margin: 0.5rem 0 0 0;
	}

	.metadata-link {
		color: #60a5fa;
		font-size: 0.875rem;
		text-decoration: none;
		word-break: break-all;
	}

	.metadata-link:hover {
		text-decoration: underline;
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

		.scanner-header {
			flex-direction: column;
			align-items: flex-start;
			gap: 1rem;
		}

		.btn-scan-series {
			width: 100%;
			justify-content: center;
		}

		.metadata-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
