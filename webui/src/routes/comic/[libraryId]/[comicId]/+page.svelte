<script>
	import { onMount } from "svelte";
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import Navbar from "$lib/components/layout/Navbar.svelte";
	import DetailHeader from "$lib/components/common/DetailHeader.svelte";
	import ScannerMetadata from "$lib/components/comic/ScannerMetadata.svelte";
	import { getComicInfo } from "$lib/api/comics";
	import { addFavorite, removeFavorite } from "$lib/api/favorites";

	$: libraryId = parseInt($page.params.libraryId);
	$: comicId = parseInt($page.params.comicId);

	let comic = null;
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

			const comicData = await getComicInfo(libraryId, comicId);
			comic = comicData;
			isFavorite = comic.favorite || false;

			isLoading = false;
		} catch (err) {
			console.error("Failed to load comic:", err);
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
			console.error("Failed to toggle favorite:", err);
			favoriteLoading = false;
		}
	}

	function handleStartReading() {
		const currentPage = comic?.current_page || comic?.currentPage || 0;
		const pageQuery = currentPage > 0 ? `?page=${currentPage}` : "";
		goto(`/comic/${libraryId}/${comicId}/read${pageQuery}`);
	}

	function handleBack() {
		if (window.history.length > 1) {
			window.history.back();
		} else {
			goto("/");
		}
	}

	// Determine series name for navigation
	$: seriesName =
		comic?.series || getSeriesFromPath(comic?.path || comic?.file_name);

	function getSeriesFromPath(path) {
		if (!path) return null;
		const parts = path.split("/").filter((p) => p);
		return parts.length > 1 ? parts[0] : null;
	}

	// Prepare item for DetailHeader (mimic series structure)
	$: itemForHeader = comic
		? {
				...comic,
				type: "comic",
				name:
					comic.title ||
					comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, ""),
				cover_hash: comic.hash,
				total_issues: 1,
				overall_progress:
					comic.num_pages && comic.current_page
						? (comic.current_page / comic.num_pages) * 100
						: 0,
			}
		: null;
</script>

<svelte:head>
	<title
		>{comic
			? comic.title ||
				comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, "")
			: "Loading..."} - Kottlib</title
	>
</svelte:head>

<div class="comic-page">
	<Navbar />

	<main class="comic-content">
		{#if isLoading}
			<div class="loading-container">
				<div class="spinner"></div>
				<p class="loading-text">Loading comic...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="error-text">Failed to load comic: {error}</p>
				<a href="/" class="btn-back">Back to Home</a>
			</div>
		{:else if comic}
			<!-- Unified DetailHeader -->
			<DetailHeader
				item={itemForHeader}
				{libraryId}
				onBack={handleBack}
				onStartReading={handleStartReading}
			/>

			<!-- Scanner Metadata (optional enhancement) -->
			<div class="scanner-section">
				<ScannerMetadata {comic} on:updated={loadComicData} />
			</div>
		{/if}
	</main>
</div>

<style>
	.comic-page {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: var(--color-bg, #09090b);
	}

	.comic-content {
		flex: 1;
		overflow-y: auto;
	}

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
		border-top-color: #f97316;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.loading-text {
		color: #a1a1aa;
		margin-top: 1rem;
	}

	.error-text {
		color: #ef4444;
	}

	.btn-back {
		margin-top: 1rem;
		padding: 0.625rem 1.25rem;
		background: #f97316;
		color: white;
		font-weight: 600;
		border-radius: 0.5rem;
		text-decoration: none;
	}

	.scanner-section {
		max-width: 80rem;
		margin: 0 auto;
		padding: 0 1.5rem 2rem;
	}
</style>
