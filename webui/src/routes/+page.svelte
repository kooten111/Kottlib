<script>
	import { onMount } from 'svelte';
	import Navbar from '$components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import SeriesTree from '$lib/components/layout/SeriesTree.svelte';
	import { getLibraries, getSeries, getContinueReading, getLibrariesSeriesTree } from '$lib/api/libraries';
	import { BookOpen, Library, TrendingUp } from 'lucide-svelte';

	let libraries = [];
	let continueReading = [];
	let allSeries = [];
	let displayedSeries = [];
	let isLoading = true;
	let error = null;
	let seriesTree = [];
	let currentFilter = null;

	onMount(async () => {
		await loadHomeData();
	});

	async function loadHomeData() {
		try {
			isLoading = true;
			error = null;

			// Load libraries and series tree
			[libraries, seriesTree] = await Promise.all([
				getLibraries(),
				getLibrariesSeriesTree()
			]);

			if (!libraries || libraries.length === 0) {
				isLoading = false;
				return;
			}

			// Load continue reading from all libraries using dedicated API
			const continueReadingResults = await Promise.all(
				libraries.map(async (lib) => {
					try {
						const comics = await getContinueReading(lib.id, 100);
						return comics.map(comic => ({ ...comic, libraryId: lib.id }));
					} catch {
						return [];
					}
				})
			);

			continueReading = continueReadingResults.flat().slice(0, 10);

			// Load all series from all libraries
			const allSeriesResults = await Promise.all(
				libraries.map(async (lib) => {
					try {
						console.log(`Fetching series for library ${lib.id} (${lib.name})...`);
						const series = await getSeries(lib.id, 'recent');
						console.log(`Library ${lib.id} (${lib.name}) returned ${series.length} series`);
						return series.map(s => ({ ...s, libraryId: lib.id }));
					} catch (err) {
						console.error(`Failed to fetch series for library ${lib.id}:`, err);
						return [];
					}
				})
			);

			console.log('All series results:', allSeriesResults.map(r => r.length));

			// Interleave series from different libraries instead of concatenating sequentially
			// This ensures the "All Series" view shows a mix from all libraries
			const maxLength = Math.max(...allSeriesResults.map(r => r.length));
			allSeries = [];
			for (let i = 0; i < maxLength; i++) {
				for (const libraryResults of allSeriesResults) {
					if (i < libraryResults.length) {
						allSeries.push(libraryResults[i]);
					}
				}
			}

			console.log(`Total series after interleaving: ${allSeries.length}`);
			console.log('Library IDs in allSeries:', allSeries.slice(0, 30).map(s => s.libraryId));
			displayedSeries = allSeries.slice(0, 20);
			console.log(`Displayed series (first 20): ${displayedSeries.length}`);
			console.log('displayedSeries library breakdown:', displayedSeries.map(s => `${s.series_name} (lib:${s.libraryId})`));

			isLoading = false;
		} catch (err) {
			console.error('Failed to load data:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function handleTreeFilter(event) {
		const { type, libraryId, folderId, folderName, comicId } = event.detail;

		currentFilter = event.detail;

		if (type === 'all') {
			// Show all series from all libraries
			displayedSeries = allSeries.slice(0, 20);
		} else if (type === 'library') {
			// Filter to show only series from selected library
			displayedSeries = allSeries.filter(s => s.libraryId === libraryId);
		} else if (type === 'folder') {
			// Find all comics in this folder recursively from the tree
			const library = seriesTree.find(l => l.id === libraryId);
			if (library) {
				const allComics = [];

				// Helper function to collect all comics from a folder node
				function collectComics(node) {
					if (!node.children) return;

					for (const child of node.children) {
						if (child.type === 'comic') {
							allComics.push(child);
						} else if (child.type === 'folder') {
							// Recursively collect from subfolders
							collectComics(child);
						}
					}
				}

				// Find the folder node
				function findFolder(children) {
					for (const child of children) {
						if (child.type === 'folder' && child.folderId === folderId) {
							return child;
						}
						if (child.children) {
							const found = findFolder(child.children);
							if (found) return found;
						}
					}
					return null;
				}

				const folder = findFolder(library.children);
				if (folder) {
					collectComics(folder);

					// Convert comics to series format for display
					if (allComics.length > 0) {
						displayedSeries = [{
							series_name: folderName,
							libraryId: libraryId,
							first_comic_id: allComics[0]?.id,
							cover_hash: allComics[0]?.hash,
							total_issues: allComics.length,
							volumes: allComics
						}];
					} else {
						displayedSeries = [];
					}
				}
			}
		} else if (type === 'comic') {
			// Navigate to comic reader
			window.location.href = `/comic/${libraryId}/${comicId}/read`;
		}
	}

	function resetFilter() {
		currentFilter = null;
		displayedSeries = allSeries.slice(0, 20);
	}
</script>

<svelte:head>
	<title>Home - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<div class="flex flex-1 overflow-hidden">
		<!-- Left Sidebar -->
		<aside class="sidebar">
			<div class="sidebar-header">
				<Library class="w-5 h-5 text-accent-orange" />
				<h3 class="sidebar-title">Libraries</h3>
				{#if currentFilter}
					<button class="reset-button" on:click={resetFilter} title="Show all">
						✕
					</button>
				{/if}
			</div>

			{#if seriesTree.length > 0}
				<div class="tree-container">
					<SeriesTree tree={seriesTree} on:filter={handleTreeFilter} />
				</div>
			{:else}
				<p class="sidebar-empty">No libraries</p>
			{/if}
		</aside>

		<!-- Main Content -->
		<main class="flex-1 overflow-y-auto">
			<div class="container mx-auto px-4 py-8 max-w-content">
				{#if isLoading}
					<div class="loading-container">
						<div class="spinner" />
						<p class="text-gray-400 mt-4">Loading...</p>
					</div>
				{:else if error}
					<div class="error-container">
						<p class="text-red-400">Failed to load: {error}</p>
					</div>
				{:else}
					{#if continueReading.length > 0}
						<section class="section">
							<div class="section-header">
								<h2 class="section-title">
									<BookOpen class="w-6 h-6" />
									Continue Reading
								</h2>
								<a href="/continue-reading" class="see-all">See all →</a>
							</div>
							<div class="comics-grid">
								{#each continueReading as comic}
									<ComicCard {comic} libraryId={comic.libraryId} />
								{/each}
							</div>
						</section>
					{/if}

					{#if displayedSeries.length > 0}
						<section class="section">
							<div class="section-header">
								<h2 class="section-title">
									<TrendingUp class="w-6 h-6" />
									{#if currentFilter?.type === 'all'}
										All Series
									{:else if currentFilter?.type === 'library'}
										{currentFilter.libraryName}
									{:else if currentFilter?.type === 'folder'}
										{currentFilter.folderName}
									{:else}
										All Series
									{/if}
								</h2>
								{#if !currentFilter && currentFilter?.type !== 'all'}
									<a href="/browse" class="see-all">See all →</a>
								{/if}
							</div>
							<div class="comics-grid">
								{#if currentFilter?.type === 'folder'}
									<!-- Show individual comics when folder is selected -->
									{#each displayedSeries[0]?.volumes || [] as comic}
										<a href="/comic/{currentFilter.libraryId}/{comic.id}/read">
											<ComicCard
												comic={{
													id: comic.id,
													title: comic.name,
													hash: comic.hash,
													currentPage: comic.currentPage,
													totalPages: comic.totalPages
												}}
												libraryId={currentFilter.libraryId}
												showProgress={true}
											/>
										</a>
									{/each}
								{:else}
									<!-- Show series cards -->
									{#each displayedSeries as series}
										<a href="/series/{series.libraryId}/{encodeURIComponent(series.series_name)}">
											<ComicCard
												comic={{
													id: series.first_comic_id,
													title: series.series_name,
													hash: series.cover_hash,
													itemCount: series.total_issues
												}}
												libraryId={series.libraryId}
												showProgress={false}
												isFolder={true}
												itemCount={series.total_issues}
											/>
										</a>
									{/each}
								{/if}
							</div>
						</section>
					{/if}

					{#if continueReading.length === 0 && allSeries.length === 0}
						<div class="empty-state">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="64"
								height="64"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								class="text-gray-500 mb-4"
							>
								<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
								<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
							</svg>
							<p class="text-gray-400 mb-4">No comics yet!</p>
							<a href="/browse" class="btn-primary">Browse Libraries</a>
						</div>
					{/if}
				{/if}
			</div>
		</main>
	</div>
</div>

<style>
	.sidebar {
		width: 280px;
		background: var(--color-secondary-bg);
		border-right: 1px solid rgba(255, 255, 255, 0.05);
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		overflow-y: auto;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1.5rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
	}

	.sidebar-title {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
		flex: 1;
	}

	.reset-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		padding: 0;
		background: rgba(255, 255, 255, 0.1);
		border: none;
		border-radius: 4px;
		color: var(--color-text);
		cursor: pointer;
		transition: background 0.2s;
		font-size: 14px;
	}

	.reset-button:hover {
		background: rgba(255, 255, 255, 0.2);
	}

	.tree-container {
		flex: 1;
		padding: 0.5rem;
		overflow-y: auto;
	}

	.libraries-nav {
		flex: 1;
		padding: 0.5rem;
		overflow-y: auto;
	}

	.library-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		border-radius: 6px;
		text-decoration: none;
		color: var(--color-text);
		transition: background 0.2s;
		margin-bottom: 0.25rem;
	}

	.library-item:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.library-item-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: rgba(255, 103, 64, 0.1);
		border-radius: 6px;
		color: var(--color-accent);
		flex-shrink: 0;
	}

	.library-item-content {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.library-item-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.library-item-count {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.sidebar-footer {
		padding: 1rem;
		border-top: 1px solid rgba(255, 255, 255, 0.05);
	}

	.sidebar-link {
		display: block;
		text-align: center;
		padding: 0.5rem;
		color: var(--color-accent);
		text-decoration: none;
		font-size: 0.875rem;
		transition: opacity 0.2s;
	}

	.sidebar-link:hover {
		opacity: 0.8;
	}

	.sidebar-empty {
		padding: 1rem;
		text-align: center;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.loading-container,
	.error-container,
	.empty-state {
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
		to {transform: rotate(360deg);}
	}

	.section {
		margin-bottom: 3rem;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.5rem;
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
	}

	.see-all {
		font-size: 0.875rem;
		color: var(--color-accent);
		text-decoration: none;
		transition: opacity 0.2s;
	}

	.see-all:hover {
		opacity: 0.8;
	}

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
	}

	@media (max-width: 768px) {
		.sidebar {
			display: none;
		}

		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}

		.section-title {
			font-size: 1.25rem;
		}
	}
</style>
