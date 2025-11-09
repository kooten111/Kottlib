<script>
	import { onMount } from 'svelte';
	import Navbar from '$components/layout/Navbar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import { getLibraries, getFolderContents, getContinueReading } from '$lib/api/libraries';
	import { BookOpen, Library, TrendingUp } from 'lucide-svelte';

	let libraries = [];
	let continueReading = [];
	let recentlyAdded = [];
	let isLoading = true;
	let error = null;

	onMount(async () => {
		await loadHomeData();
	});

	async function loadHomeData() {
		try {
			isLoading = true;
			error = null;

			libraries = await getLibraries();

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

			// Load recently added from root folders
			const allComicsResults = await Promise.all(
				libraries.map(async (lib) => {
					try {
						const items = await getFolderContents(lib.id, 0);
						return items
							.filter(item => item.type === 'comic')
							.map(comic => ({ ...comic, libraryId: lib.id }));
					} catch {
						return [];
					}
				})
			);

			const allComics = allComicsResults.flat();

			recentlyAdded = allComics
				.sort((a, b) => (b.added || 0) - (a.added || 0))
				.slice(0, 20);

			isLoading = false;
		} catch (err) {
			console.error('Failed to load data:', err);
			error = err.message;
			isLoading = false;
		}
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
			</div>

			{#if libraries.length > 0}
				<nav class="libraries-nav">
					{#each libraries as library}
						<a href="/browse/{library.id}" class="library-item">
							<div class="library-item-icon">
								<Library class="w-4 h-4" />
							</div>
							<div class="library-item-content">
								<span class="library-item-name">{library.name}</span>
								<span class="library-item-count">{library.comicCount || 0}</span>
							</div>
						</a>
					{/each}
				</nav>

				<div class="sidebar-footer">
					<a href="/browse" class="sidebar-link">Browse All →</a>
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

					{#if recentlyAdded.length > 0}
						<section class="section">
							<div class="section-header">
								<h2 class="section-title">
									<TrendingUp class="w-6 h-6" />
									Recently Added
								</h2>
							</div>
							<div class="comics-grid">
								{#each recentlyAdded as comic}
									<ComicCard {comic} libraryId={comic.libraryId} showProgress={false} />
								{/each}
							</div>
						</section>
					{/if}

					{#if continueReading.length === 0 && recentlyAdded.length === 0}
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
