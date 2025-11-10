<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import Breadcrumbs from '$lib/components/common/Breadcrumbs.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibraries, getSeries, getFolderTree } from '$lib/api/libraries';
	import { Grid, List, SortAsc } from 'lucide-svelte';

	let allLibraries = [];
	let allSeries = [];
	let isLoading = true;
	let error = null;
	let breadcrumbs = [];
	let viewMode = 'grid'; // 'grid' or 'list'
	let sortBy = 'name'; // 'name', 'recent', 'progress'
	let folderTrees = {};
	let selectedLibraryId = null;

	onMount(async () => {
		await loadAllData();
	});

	$: sortedSeries = sortSeries(allSeries, sortBy);
	$: filteredSeries = selectedLibraryId
		? sortedSeries.filter(s => s.libraryId === selectedLibraryId)
		: sortedSeries;

	async function loadAllData() {
		try {
			isLoading = true;
			error = null;

			// Load all libraries
			allLibraries = await getLibraries();

			// Load series from all libraries
			const allSeriesResults = await Promise.all(
				allLibraries.map(async (lib) => {
					try {
						const series = await getSeries(lib.id, sortBy);
						return series.map(s => ({ ...s, libraryId: lib.id }));
					} catch {
						return [];
					}
				})
			);

			allSeries = allSeriesResults.flat();

			// Load folder trees for all libraries
			await Promise.all(
				allLibraries.map(async (lib) => {
					try {
						const tree = await getFolderTree(lib.id);
						folderTrees[lib.id] = tree;
					} catch (err) {
						console.error(`Failed to load tree for library ${lib.id}:`, err);
					}
				})
			);

			// Build breadcrumbs
			breadcrumbs = [
				{ label: 'Home', href: '/' },
				{ label: 'Browse', href: '/browse' }
			];

			isLoading = false;
		} catch (err) {
			console.error('Failed to load data:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function sortSeries(seriesList, sortType) {
		const sorted = [...seriesList];
		switch (sortType) {
			case 'name':
				return sorted.sort((a, b) => (a.series_name || '').localeCompare(b.series_name || ''));
			case 'recent':
				return sorted.sort((a, b) => (b.first_comic_id || 0) - (a.first_comic_id || 0));
			case 'progress':
				return sorted.sort((a, b) => {
					const progressA = (a.volumes || []).filter(v => v.is_completed).length / (a.total_issues || 1);
					const progressB = (b.volumes || []).filter(v => v.is_completed).length / (b.total_issues || 1);
					return progressA - progressB;
				});
			default:
				return sorted;
		}
	}

	function toggleViewMode() {
		viewMode = viewMode === 'grid' ? 'list' : 'grid';
	}
</script>

<svelte:head>
	<title>Browse - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 overflow-y-auto">
			<div class="container mx-auto px-4 py-8 max-w-content">
				{#if isLoading}
					<div class="loading-container">
						<div class="spinner" />
						<p class="text-gray-400 mt-4">Loading library...</p>
					</div>
				{:else if error}
					<div class="error-container">
						<p class="text-red-400">Failed to load library: {error}</p>
						<a href="/" class="btn-primary mt-4">Go Home</a>
					</div>
				{:else}
					<!-- Breadcrumbs -->
					<Breadcrumbs items={breadcrumbs} />

					<!-- Library Header with Controls -->
					<div class="library-header">
						<div>
							<h1 class="library-title">
								{selectedLibraryId
									? allLibraries.find(l => l.id === selectedLibraryId)?.name || 'Browse'
									: 'All Series'}
							</h1>
							<p class="library-stats">
								{filteredSeries.length} series
							</p>
						</div>

						<!-- View Controls -->
						<div class="view-controls">
							<!-- Sort Dropdown -->
							<select bind:value={sortBy} class="control-select">
								<option value="name">Sort: Name</option>
								<option value="recent">Sort: Recently Added</option>
								<option value="progress">Sort: Progress</option>
							</select>

							<!-- View Toggle -->
							<button
								class="control-button"
								on:click={toggleViewMode}
								aria-label="Toggle view mode"
							>
								{#if viewMode === 'grid'}
									<Grid class="w-5 h-5" />
								{:else}
									<List class="w-5 h-5" />
								{/if}
							</button>
						</div>
					</div>

					<!-- Series Section -->
					{#if filteredSeries.length > 0}
						<section>
							<div class="comics-{viewMode}">
								{#each filteredSeries as series}
									<a href="/series/{series.libraryId}/{encodeURIComponent(series.series_name)}">
										<ComicCard
											comic={{
												id: series.first_comic_id,
												title: series.series_name,
												hash: series.cover_hash,
												itemCount: series.total_issues
											}}
											libraryId={series.libraryId}
											variant={viewMode}
											showProgress={false}
											isFolder={true}
											itemCount={series.total_issues}
										/>
									</a>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Empty State -->
					{#if filteredSeries.length === 0}
						<div class="empty-state">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="64"
								height="64"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								class="text-gray-500 mb-4"
							>
								<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
								<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
							</svg>
							<p class="text-gray-400">No series found</p>
						</div>
					{/if}
				{/if}
			</div>
		</main>
</div>

<style>
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
		to {
			transform: rotate(360deg);
		}
	}

	.library-header {
		margin-bottom: 2rem;
	}

	.library-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin-bottom: 0.5rem;
	}

	.library-stats {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
	}

	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 1rem;
	}

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
	}

	.comics-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	@media (max-width: 640px) {
		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}

		.library-title {
			font-size: 1.5rem;
		}
	}
</style>
