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

			// Sort volumes by volume number first (volumes before chapters), then by issue number
			// Volumes have a volume number (>0), chapters have issue_number but volume=0/null
			// When metadata is missing, detect from filename patterns
			if (series && series.volumes) {
				sortedVolumes = [...series.volumes].sort((a, b) => {
					const getSortKey = (v) => {
						const vol = parseInt(v.volume) || 0;
						const issue = parseInt(v.issue_number) || 0;
						const title = (v.title || '').toLowerCase();

						// If metadata exists, use it
						if (vol > 0) {
							// Has volume metadata - it's a volume
							return [0, vol, issue];
						} else if (issue > 0) {
							// Has issue metadata but no volume - likely a chapter
							// But check title for volume patterns first (in case metadata is incomplete)
							const volMatch = title.match(/\bv(?:ol)?\.?\s*(\d+)/i) || title.match(/\bvolume\s+(\d+)/i);
							if (volMatch) {
								const volNum = parseInt(volMatch[1]);
								return [0, volNum, 0];
							}
							// It's a chapter
							return [1, issue, 0];
						} else {
							// No metadata - rely on filename patterns
							// Check for volume patterns: v01, vol01, volume 1, etc.
							const volMatch = title.match(/\bv(?:ol)?\.?\s*(\d+)/i) || title.match(/\bvolume\s+(\d+)/i);
							if (volMatch) {
								const volNum = parseInt(volMatch[1]);
								return [0, volNum, 0];
							}
							// Check for chapter patterns: c001, ch01, chapter 1, etc.
							const chMatch = title.match(/\bc(?:h|hapter)?\.?\s*(\d+)/i) || title.match(/\bchapter\s+(\d+)/i);
							if (chMatch) {
								const chNum = parseInt(chMatch[1]);
								return [1, chNum, 0];
							}
							// Fallback: sort by title
							return [2, 0, 0];
						}
					};

					const keyA = getSortKey(a);
					const keyB = getSortKey(b);

					// Compare arrays element by element
					for (let i = 0; i < 3; i++) {
						if (keyA[i] !== keyB[i]) {
							return keyA[i] - keyB[i];
						}
					}
					return 0;
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
						<div class="title-row">
							<h1 class="series-title">{series.display_name || series.series_name}</h1>

							<!-- Show scanner button if metadata is missing and scanner is configured -->
							{#if scannerConfig?.primary_scanner && scannerConfig?.scan_level === 'series' && (!series.writer && !series.artist && !series.synopsis)}
								<button
									on:click={scanSeriesMetadata}
									disabled={isScanning}
									class="btn-scan-compact"
									title="Scan for metadata"
								>
									<Search class="w-4 h-4" />
									{isScanning ? 'Scanning...' : 'Get Metadata'}
								</button>
							{/if}
						</div>

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
									href="/comic/{libraryId}/{nextVolumeToRead.id}/read{nextVolumeToRead.current_page > 0 ? `?page=${nextVolumeToRead.current_page}` : ''}"
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

				<!-- Scan error/result feedback -->
				{#if scanError}
					<div class="scan-feedback error">
						<X class="w-4 h-4" />
						<span>{scanError}</span>
					</div>
				{/if}

				{#if scanResult && showMetadata}
					<div class="scan-feedback success">
						<Check class="w-4 h-4" />
						<span>Metadata updated successfully! ({Math.round(scanResult.confidence * 100)}% match)</span>
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

	.title-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.series-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
		flex: 1;
	}

	.btn-scan-compact {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: rgba(96, 165, 250, 0.15);
		color: #60a5fa;
		border: 1px solid rgba(96, 165, 250, 0.3);
		border-radius: 6px;
		font-weight: 500;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.2s;
		flex-shrink: 0;
	}

	.btn-scan-compact:hover:not(:disabled) {
		background: rgba(96, 165, 250, 0.25);
		border-color: rgba(96, 165, 250, 0.5);
	}

	.btn-scan-compact:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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

	.scan-feedback {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 1.5rem;
		border-radius: 8px;
		font-size: 0.875rem;
		margin-bottom: 2rem;
		animation: slideDown 0.3s ease-out;
	}

	.scan-feedback.error {
		background: rgba(239, 68, 68, 0.15);
		color: #ef4444;
		border: 1px solid rgba(239, 68, 68, 0.3);
	}

	.scan-feedback.success {
		background: rgba(34, 197, 94, 0.15);
		color: #22c55e;
		border: 1px solid rgba(34, 197, 94, 0.3);
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
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

		.title-row {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.75rem;
		}

		.series-title {
			font-size: 1.5rem;
		}

		.btn-scan-compact {
			width: 100%;
			justify-content: center;
		}

		.volumes-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}
	}
</style>
