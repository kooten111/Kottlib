<script>
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import Navbar from "$lib/components/layout/Navbar.svelte";
	import HomeSidebar from "$lib/components/layout/HomeSidebar.svelte";
	import DetailHeader from "$lib/components/common/DetailHeader.svelte";
	import ComicCard from "$lib/components/comic/ComicCard.svelte";
	import ScannerMetadata from "$lib/components/comic/ScannerMetadata.svelte";
	import { addFavorite, removeFavorite } from "$lib/api/favorites";
	import { BookOpen } from "lucide-svelte";

	export let data;

	// Server-side loaded data
	$: comic = data.comic;
	$: libraries = data.libraries || [];
	$: seriesTree = data.seriesTree || [];
	$: libraryId = data.libraryId;
	$: comicId = data.comicId;
	$: error = data.error;

	let isFavorite = false;
	let favoriteLoading = false;

	$: if (comic) {
		isFavorite = comic.favorite || false;
	}

	async function handleFavoriteToggle() {
		try {
			favoriteLoading = true;

			if (isFavorite) {
				await removeFavorite(comicId);
				isFavorite = false;
			} else {
				await addFavorite(comicId);
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

	// Construct currentFilter for sidebar highlighting
	$: currentFilter = {
		type: "comic",
		libraryId,
		comicId,
	};

	function handleViewChange(e) {
		const view = e.detail;
		if (view === "favorites") goto("/favorites");
		else if (view === "continue") goto("/continue-reading");
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

	// Prepare comic as a single "volume" for the grid
	$: volumes = comic
		? [
				{
					id: comic.id,
					title:
						comic.title ||
						comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, ""),
					hash: comic.hash,
					num_pages: comic.num_pages,
					current_page: comic.current_page,
					is_completed: comic.read || comic.is_completed,
				},
			]
		: [];

	// Reload comic data after scanner update
	async function reloadComic() {
		// Force page refresh to get updated data from server
		window.location.reload();
	}
</script>

<svelte:head>
	<title
		>{comic
			? comic.title ||
				comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, "")
			: "Loading..."} - Kottlib</title
	>
</svelte:head>

<div
	class="h-screen flex flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]"
>
	<!-- Navbar at Top -->
	<Navbar />

	<!-- Sidebar + Main Content Row -->
	<div class="flex-1 flex overflow-hidden">
		<!-- Sidebar -->
		<HomeSidebar
			{libraries}
			{seriesTree}
			{currentFilter}
			currentView="home"
			on:viewChange={handleViewChange}
		/>

		<!-- Main Content -->
		<main
			class="flex-1 overflow-y-auto px-4 pb-8 scrollbar-thin scrollbar-thumb-[var(--color-border)] scrollbar-track-transparent"
		>
			<div class="max-w-7xl mx-auto w-full pt-4">
				{#if error}
					<div
						class="flex flex-col items-center justify-center py-20"
					>
						<p class="text-[var(--color-error)] text-lg mb-4">
							{error}
						</p>
						<a
							href="/library/{libraryId}/browse"
							class="px-4 py-2 bg-[var(--color-bg-secondary)] rounded hover:bg-[var(--color-bg-tertiary)] transition"
							>Return to Library</a
						>
					</div>
				{:else if comic}
					<!-- Detail Header (Hero) -->
					<DetailHeader
						item={itemForHeader}
						{libraryId}
						onBack={handleBack}
						onStartReading={handleStartReading}
					/>

					<!-- Volumes Section (single comic as "series of one") -->
					<section class="mt-8">
						<div class="flex items-center gap-2 mb-4 px-1">
							<BookOpen
								class="w-5 h-5 text-[var(--color-accent)]"
							/>
							<h2 class="text-xl font-bold text-white">
								Volumes
							</h2>
						</div>
						<div
							class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
							style="grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));"
						>
							{#each volumes as volume (volume.id)}
								<ComicCard
									comic={volume}
									{libraryId}
									variant="grid"
									showProgress={true}
									href={`/comic/${libraryId}/${volume.id}/read`}
								/>
							{/each}
						</div>
					</section>

					<!-- Scanner Metadata Section -->
					<section class="mt-8">
						<ScannerMetadata {comic} on:updated={reloadComic} />
					</section>
				{:else}
					<!-- Loading State -->
					<div
						class="flex flex-col items-center justify-center py-20"
					>
						<div
							class="w-10 h-10 border-4 border-[var(--color-border)] border-t-[var(--color-accent)] rounded-full animate-spin"
						></div>
						<p class="mt-4 text-[var(--color-text-muted)]">
							Loading comic...
						</p>
					</div>
				{/if}
			</div>
		</main>
	</div>
</div>
