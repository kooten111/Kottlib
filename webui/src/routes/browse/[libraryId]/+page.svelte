<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import Breadcrumbs from '$lib/components/common/Breadcrumbs.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibrary, getFolderContents } from '$lib/api/libraries';
	import { getCoverUrl } from '$lib/api/comics';
	import { Grid, List, SortAsc, Filter, Folder as FolderIcon } from 'lucide-svelte';

	$: libraryId = parseInt($page.params.libraryId);
	$: folderId = parseInt($page.url.searchParams.get('folder') || '0');

	let library = null;
	let folders = [];
	let comics = [];
	let isLoading = true;
	let error = null;
	let breadcrumbs = [];
	let sidebarOpen = false;
	let viewMode = 'grid'; // 'grid' or 'list'
	let sortBy = 'name'; // 'name', 'date', 'progress'

	// Filters
	let filters = {
		series: [],
		tags: [],
		status: [] // 'unread', 'reading', 'completed'
	};

	onMount(async () => {
		await loadLibraryData();
	});

	$: if (libraryId || folderId) {
		loadLibraryData();
	}

	$: sortedComics = sortComics(comics, sortBy);

	async function loadLibraryData() {
		try {
			isLoading = true;
			error = null;

			// Load library info
			library = await getLibrary(libraryId);

			// Load folder contents - API returns flat array with type field
			const items = await getFolderContents(libraryId, folderId);

			// Separate folders and comics based on type
			folders = items.filter(item => item.type === 'folder');
			comics = items.filter(item => item.type === 'comic');

			// Build breadcrumbs (simplified for now)
			breadcrumbs = [
				{ label: 'Home', href: '/' },
				{ label: library.name, href: `/browse/${libraryId}` }
			];

			isLoading = false;
		} catch (err) {
			console.error('Failed to load library:', err);
			error = err.message;
			isLoading = false;
		}
	}

	function handleFolderClick(folder) {
		window.location.href = `/browse/${libraryId}?folder=${folder.id}`;
	}

	function sortComics(comicsList, sortType) {
		const sorted = [...comicsList];
		switch (sortType) {
			case 'name':
				return sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
			case 'date':
				return sorted.sort((a, b) => (b.dateAdded || 0) - (a.dateAdded || 0));
			case 'progress':
				return sorted.sort((a, b) => {
					const progressA = a.currentPage / a.numPages || 0;
					const progressB = b.currentPage / b.numPages || 0;
					return progressB - progressA;
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
	<title>{library ? library.name : 'Loading...'} - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<div class="flex flex-1">
		<!-- Sidebar with Filters -->
		<Sidebar bind:open={sidebarOpen}>
			<div class="sidebar-content">
				<h3 class="filter-section-title">Filters</h3>

				<!-- Series Filter -->
				<div class="filter-section">
					<h4 class="filter-label">Series</h4>
					<div class="filter-options">
						<!-- TODO: Populate with actual series from library -->
						<label class="filter-checkbox">
							<input type="checkbox" />
							<span>All Series</span>
						</label>
					</div>
				</div>

				<!-- Tags Filter -->
				<div class="filter-section">
					<h4 class="filter-label">Tags</h4>
					<div class="filter-options">
						<!-- TODO: Populate with actual tags -->
						<label class="filter-checkbox">
							<input type="checkbox" />
							<span>All Tags</span>
						</label>
					</div>
				</div>

				<!-- Reading Status Filter -->
				<div class="filter-section">
					<h4 class="filter-label">Status</h4>
					<div class="filter-options">
						<label class="filter-checkbox">
							<input type="checkbox" />
							<span>Unread</span>
						</label>
						<label class="filter-checkbox">
							<input type="checkbox" />
							<span>Reading</span>
						</label>
						<label class="filter-checkbox">
							<input type="checkbox" />
							<span>Completed</span>
						</label>
					</div>
				</div>
			</div>
		</Sidebar>

		<!-- Main Content Area -->
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
							<h1 class="library-title">{library.name}</h1>
							<p class="library-stats">
								{folders.length} folders • {comics.length} comics
							</p>
						</div>

						<!-- View Controls -->
						<div class="view-controls">
							<!-- Sort Dropdown -->
							<select bind:value={sortBy} class="control-select">
								<option value="name">Sort: Name</option>
								<option value="date">Sort: Date Added</option>
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

							<!-- Filter Toggle (Mobile) -->
							<button
								class="control-button lg:hidden"
								on:click={() => sidebarOpen = !sidebarOpen}
								aria-label="Toggle filters"
							>
								<Filter class="w-5 h-5" />
							</button>
						</div>
					</div>

					<!-- Folders Section -->
					{#if folders.length > 0}
						<section class="mb-8">
							<h2 class="section-title">Folders</h2>
							<div class="folders-grid">
								{#each folders as folder}
									<button class="folder-card" on:click={() => handleFolderClick(folder)}>
										<div class="folder-cover">
											{#if folder.first_comic_hash}
												<img
													src={getCoverUrl(libraryId, folder.first_comic_hash)}
													alt={folder.folder_name}
													class="folder-cover-image"
													loading="lazy"
												/>
												<div class="folder-overlay">
													<FolderIcon class="w-8 h-8 text-white" />
												</div>
											{:else}
												<div class="folder-placeholder">
													<FolderIcon class="w-12 h-12 text-gray-500" />
												</div>
											{/if}
										</div>
										<div class="folder-info">
											<p class="folder-name">{folder.folder_name}</p>
											{#if folder.num_children > 0}
												<p class="folder-count">{folder.num_children} items</p>
											{/if}
										</div>
									</button>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Comics Section -->
					{#if sortedComics.length > 0}
						<section>
							<h2 class="section-title">Comics</h2>
							<div class="comics-{viewMode}">
								{#each sortedComics as comic}
									<ComicCard {comic} {libraryId} variant={viewMode} />
								{/each}
							</div>
						</section>
					{/if}

					<!-- Empty State -->
					{#if folders.length === 0 && comics.length === 0}
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
							<p class="text-gray-400">This folder is empty</p>
						</div>
					{/if}
				{/if}
			</div>
		</main>
	</div>
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

	.folders-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	.folder-card {
		display: flex;
		flex-direction: column;
		background: var(--color-secondary-bg);
		border-radius: 8px;
		border: 1px solid transparent;
		cursor: pointer;
		transition: all 0.2s ease;
		overflow: hidden;
	}

	.folder-card:hover {
		border-color: var(--color-accent);
		transform: translateY(-4px);
		box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
	}

	.folder-cover {
		position: relative;
		aspect-ratio: 2/3;
		background: #1a1a1a;
		overflow: hidden;
	}

	.folder-cover-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.folder-overlay {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.7));
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.folder-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--color-secondary-bg);
	}

	.folder-info {
		padding: 1rem;
	}

	.folder-name {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.25rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.folder-count {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin: 0;
	}

	.comics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1.5rem;
	}

	@media (max-width: 640px) {
		.comics-grid,
		.folders-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}

		.library-title {
			font-size: 1.5rem;
		}
	}
</style>
