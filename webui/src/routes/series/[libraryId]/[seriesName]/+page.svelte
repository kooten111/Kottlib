<script>
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import Navbar from "$lib/components/layout/Navbar.svelte";
	import DetailHeader from "$lib/components/common/DetailHeader.svelte";
	import ComicCard from "$lib/components/comic/ComicCard.svelte";
	import { getSeriesDetail, getLibrary } from "$lib/api/libraries";
	import { getCoverUrl } from "$lib/api/comics";
	import { Search, Check, X } from "lucide-svelte";
	import { navigationContext } from "$lib/stores/library";

	export let data;

	// Safe URI decoding that handles malformed URIs (e.g., series names with % in them)
	function safeDecodeURIComponent(str) {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			// If decoding fails, return the original string
			return str;
		}
	}

	$: libraryId = parseInt($page.params.libraryId);
	$: seriesName = safeDecodeURIComponent($page.params.seriesName);

	// Initialize from SSR data
	$: series = data.series;
	$: error = data.error;

	let scannerConfig = null;
	let library = null;
	let isLoading = false; // Data is already loaded via SSR
	let sortedVolumes = [];
	let nextVolumeToRead = null;
	let hasStartedReading = false;

	// Scanner state
	let isScanning = false;
	let scanResult = null;
	let scanError = null;
	let showMetadata = false;

	onMount(async () => {
		await loadScannerConfig();
		// Process volumes immediately since data is available
		if (series) {
			processVolumes();
		}
	});

	$: if (series) {
		processVolumes();
	}

	async function processVolumes() {
		// Sort volumes by volume number first (volumes before chapters), then by issue number
		// Volumes have a volume number (>0), chapters have issue_number but volume=0/null
		// When metadata is missing, detect from filename patterns
		if (series && series.volumes) {
			sortedVolumes = [...series.volumes].sort((a, b) => {
				const getSortKey = (v) => {
					// Folders always come first
					if (v.type === "folder") {
						return [-1, 0, 0];
					}

					const vol = parseInt(v.volume) || 0;
					const issue = parseInt(v.issue_number) || 0;
					const title = (v.title || "").toLowerCase();

					// If metadata exists, use it
					if (vol > 0) {
						// Has volume metadata - it's a volume
						return [0, vol, issue];
					} else if (issue > 0) {
						// Has issue metadata but no volume - likely a chapter
						// But check title for volume patterns first (in case metadata is incomplete)
						const volMatch =
							title.match(/\bv(?:ol)?\.?\s*(\d+)/i) ||
							title.match(/\bvolume\s+(\d+)/i);
						if (volMatch) {
							const volNum = parseInt(volMatch[1]);
							return [0, volNum, 0];
						}
						// It's a chapter
						return [1, issue, 0];
					} else {
						// No metadata - rely on filename patterns
						// Check for volume patterns: v01, vol01, volume 1, etc.
						const volMatch =
							title.match(/\bv(?:ol)?\.?\s*(\d+)/i) ||
							title.match(/\bvolume\s+(\d+)/i);
						if (volMatch) {
							const volNum = parseInt(volMatch[1]);
							return [0, volNum, 0];
						}
						// Check for chapter patterns: c001, ch01, chapter 1, etc.
						const chMatch =
							title.match(/\bc(?:h|hapter)?\.?\s*(\d+)/i) ||
							title.match(/\bchapter\s+(\d+)/i);
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
			const volumeWithProgress = sortedVolumes.find(
				(v) => v.current_page > 0 && !v.is_completed,
			);
			const firstUnread = sortedVolumes.find((v) => !v.is_completed);
			nextVolumeToRead =
				volumeWithProgress || firstUnread || sortedVolumes[0];

			// Check if user has started reading any volume
			hasStartedReading = sortedVolumes.some((v) => v.current_page > 0);
		}

		// Update navigation context for continue reading filtering
		navigationContext.set({
			type: "series",
			libraryId: libraryId,
			seriesName: seriesName,
			seriesNames: [seriesName],
		});
	}

	async function loadScannerConfig() {
		try {
			const response = await fetch("/v2/scanners/libraries");
			if (!response.ok) throw new Error("Failed to load scanner config");
			const configs = await response.json();
			scannerConfig = configs.find((c) => c.library_id === libraryId);
		} catch (err) {
			console.error("Failed to load scanner config:", err);
		}
	}

	async function scanSeriesMetadata() {
		try {
			isScanning = true;
			scanError = null;
			scanResult = null;

			const response = await fetch(
				`/v2/scanners/scan/series?library_id=${libraryId}&series_name=${encodeURIComponent(seriesName)}&overwrite=false`,
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
				},
			);

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					errorData.detail || errorData.error || "Scan failed",
				);
			}

			const data = await response.json();

			if (!data.success) {
				throw new Error(data.error || "Scan failed");
			}

			scanResult = {
				confidence: data.confidence,
				metadata: data.metadata,
				source_url: data.source_url,
				fields_updated: data.fields_updated,
			};
			showMetadata = true;

			// Reload series data to show updated metadata
			await loadSeriesData();
		} catch (err) {
			console.error("Scan error:", err);
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
						const title = (v.title || "").toLowerCase();

						// If metadata exists, use it
						if (vol > 0) {
							// Has volume metadata - it's a volume
							return [0, vol, issue];
						} else if (issue > 0) {
							// Has issue metadata but no volume - likely a chapter
							// But check title for volume patterns first (in case metadata is incomplete)
							const volMatch =
								title.match(/\bv(?:ol)?\.?\s*(\d+)/i) ||
								title.match(/\bvolume\s+(\d+)/i);
							if (volMatch) {
								const volNum = parseInt(volMatch[1]);
								return [0, volNum, 0];
							}
							// It's a chapter
							return [1, issue, 0];
						} else {
							// No metadata - rely on filename patterns
							// Check for volume patterns: v01, vol01, volume 1, etc.
							const volMatch =
								title.match(/\bv(?:ol)?\.?\s*(\d+)/i) ||
								title.match(/\bvolume\s+(\d+)/i);
							if (volMatch) {
								const volNum = parseInt(volMatch[1]);
								return [0, volNum, 0];
							}
							// Check for chapter patterns: c001, ch01, chapter 1, etc.
							const chMatch =
								title.match(/\bc(?:h|hapter)?\.?\s*(\d+)/i) ||
								title.match(/\bchapter\s+(\d+)/i);
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
				const volumeWithProgress = sortedVolumes.find(
					(v) => v.current_page > 0 && !v.is_completed,
				);
				const firstUnread = sortedVolumes.find((v) => !v.is_completed);
				nextVolumeToRead =
					volumeWithProgress || firstUnread || sortedVolumes[0];

				// Check if user has started reading any volume
				hasStartedReading = sortedVolumes.some(
					(v) => v.current_page > 0,
				);
			}

			// Update navigation context for continue reading filtering
			navigationContext.set({
				type: "series",
				libraryId: libraryId,
				seriesName: seriesName,
				seriesNames: [seriesName],
			});

			isLoading = false;
		} catch (err) {
			console.error("Failed to load series:", err);
			error = err.message;
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>{series ? series.series_name : "Loading..."} - Kottlib</title>
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
				<!-- Enhanced Series Header -->
				<DetailHeader
					item={{
						...series,
						name: series.series_name,
						nextVolumeToRead,
					}}
					{libraryId}
					onBack={() => goto("/")}
					onStartReading={nextVolumeToRead
						? () => {
								const page =
									nextVolumeToRead.current_page > 0
										? `?page=${nextVolumeToRead.current_page}`
										: "";
								goto(
									`/comic/${libraryId}/${nextVolumeToRead.id}/read${page}`,
								);
							}
						: null}
				/>

				<!-- Scanner button (show if metadata missing) -->
				{#if scannerConfig?.primary_scanner && scannerConfig?.scan_level === "series" && !series.writer && !series.artist && !series.synopsis}
					<div class="scanner-action">
						<button
							on:click={scanSeriesMetadata}
							disabled={isScanning}
							class="btn-scan"
						>
							<Search class="w-4 h-4" />
							{isScanning ? "Scanning..." : "Get Metadata"}
						</button>
					</div>
				{/if}

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
						<span
							>Metadata updated successfully! ({Math.round(
								scanResult.confidence * 100,
							)}% match)</span
						>
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
									read: volume.is_completed,
								}}
								{libraryId}
								variant="grid"
								showProgress={true}
								isFolder={volume.type === "folder"}
								itemCount={volume.item_count}
								href={volume.type === "folder"
									? `/series/${libraryId}/${encodeURIComponent(volume.title)}`
									: null}
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

	/* Scanner action button */
	.scanner-action {
		display: flex;
		justify-content: center;
		margin-bottom: 1.5rem;
	}

	.btn-scan {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		background: rgba(96, 165, 250, 0.15);
		color: #60a5fa;
		border: 1px solid rgba(96, 165, 250, 0.3);
		border-radius: 0.5rem;
		font-weight: 500;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-scan:hover:not(:disabled) {
		background: rgba(96, 165, 250, 0.25);
		border-color: rgba(96, 165, 250, 0.5);
	}

	.btn-scan:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
		.volumes-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}
	}
</style>
