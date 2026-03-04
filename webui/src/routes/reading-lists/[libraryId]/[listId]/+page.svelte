<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import HomeSidebar from '$lib/components/layout/HomeSidebar.svelte';
	import ComicCard from '$lib/components/comic/ComicCard.svelte';
	import {
		getReadingListInfo,
		getReadingListContent,
		updateReadingList,
		deleteReadingList,
		removeComicFromReadingList
	} from '$lib/api/readingLists';
	import { getLibraries, getLibrariesSeriesTree } from '$lib/api/libraries';
	import {
		BookOpen, ArrowLeft, Grid, List, Trash2, Pencil, X, Check,
		Loader2, Minus
	} from 'lucide-svelte';

	$: libraryId = parseInt($page.params.libraryId);
	$: listId = parseInt($page.params.listId);

	let listInfo = null;
	let comics = [];
	let isLoading = true;
	let error = null;
	let viewMode = 'grid';
	let sortBy = 'position';

	// Edit state
	let isEditing = false;
	let editName = '';
	let editDescription = '';
	let isSaving = false;

	// Delete state
	let showDeleteConfirm = false;
	let isDeleting = false;

	// Remove comic state
	let removingComicId = null;

	// Sidebar data
	let libraries = [];
	let seriesTree = [];

	onMount(async () => {
		await Promise.all([loadListData(), loadSidebarData()]);
	});

	// Reload when route params change
	$: if (libraryId && listId) {
		loadListData();
	}

	async function loadSidebarData() {
		try {
			const [libs, tree] = await Promise.all([
				getLibraries(),
				getLibrariesSeriesTree()
			]);
			libraries = libs || [];
			seriesTree = tree || [];
		} catch (err) {
			console.error('Failed to load sidebar data:', err);
		}
	}

	async function loadListData() {
		try {
			isLoading = true;
			error = null;

			const [info, content] = await Promise.all([
				getReadingListInfo(libraryId, listId),
				getReadingListContent(libraryId, listId)
			]);

			listInfo = info;
			comics = content || [];
		} catch (err) {
			console.error('Failed to load reading list:', err);
			error = err.message;
		} finally {
			isLoading = false;
		}
	}

	function startEditing() {
		editName = listInfo?.name || '';
		editDescription = listInfo?.description || '';
		isEditing = true;
	}

	function cancelEditing() {
		isEditing = false;
	}

	async function saveEdits() {
		if (!editName.trim()) return;
		try {
			isSaving = true;
			const result = await updateReadingList(libraryId, listId, {
				name: editName.trim(),
				description: editDescription.trim()
			});
			if (result?.success) {
				listInfo = { ...listInfo, name: result.name, description: result.description };
				isEditing = false;
			}
		} catch (err) {
			console.error('Failed to update reading list:', err);
			error = err.message;
		} finally {
			isSaving = false;
		}
	}

	async function handleDelete() {
		try {
			isDeleting = true;
			await deleteReadingList(libraryId, listId);
			goto('/reading-lists');
		} catch (err) {
			console.error('Failed to delete reading list:', err);
			error = err.message;
			isDeleting = false;
		}
	}

	async function handleRemoveComic(comicId) {
		try {
			removingComicId = comicId;
			await removeComicFromReadingList(libraryId, listId, comicId);
			comics = comics.filter(c => c.id !== comicId);
			if (listInfo) {
				listInfo = { ...listInfo, comicCount: (listInfo.comicCount || 1) - 1 };
			}
		} catch (err) {
			console.error('Failed to remove comic:', err);
			error = err.message;
		} finally {
			removingComicId = null;
		}
	}

	function toggleViewMode() {
		viewMode = viewMode === 'grid' ? 'list' : 'grid';
	}

	function encodePath(path) {
		if (!path) return '';
		return path
			.split('/')
			.map((segment) => encodeURIComponent(segment))
			.join('/');
	}

	function getComicOverviewHref(comic) {
		const targetLibraryId = comic.libraryId || comic.library_id || libraryId;
		const rawPath =
			comic.browse_path ||
			comic.browsePath ||
			comic.name ||
			comic.title ||
			comic.series ||
			comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '');

		if (targetLibraryId && rawPath) {
			return `/library/${targetLibraryId}/browse/${encodePath(rawPath)}`;
		}

		return `/comic/${targetLibraryId}/${comic.id}/read`;
	}

	function sortComics(comicList, sortType) {
		const sorted = [...comicList];
		switch (sortType) {
			case 'position':
				return sorted; // Already ordered by position from API
			case 'title':
				return sorted.sort((a, b) => (a.name || a.title || '').localeCompare(b.name || b.title || ''));
			case 'series':
				return sorted.sort((a, b) => (a.series || '').localeCompare(b.series || ''));
			default:
				return sorted;
		}
	}

	$: sortedComics = sortComics(comics, sortBy);
</script>

<svelte:head>
	<title>{listInfo?.name || 'Reading List'} - Kottlib</title>
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]">
	<Navbar />

	<div class="flex-1 flex overflow-hidden">
		<HomeSidebar
			{libraries}
			{seriesTree}
			currentFilter={{ type: 'reading-lists' }}
		/>

		<main class="flex-1 overflow-y-auto px-4 pb-8 scrollbar-thin scrollbar-thumb-[var(--color-border)] scrollbar-track-transparent">
			<div class="w-full pt-4">
				<!-- Back Link -->
				<button class="back-link" on:click={() => goto('/reading-lists')}>
					<ArrowLeft class="w-4 h-4" />
					All Reading Lists
				</button>

				{#if isLoading}
					<div class="loading-container">
						<div class="spinner"></div>
						<p class="text-gray-400 mt-4">Loading reading list...</p>
					</div>
				{:else if error && !listInfo}
					<div class="error-container">
						<p class="text-red-400">Failed to load reading list: {error}</p>
						<button class="btn-primary mt-4" on:click={loadListData}>Try Again</button>
					</div>
				{:else if listInfo}
					<!-- Page Header -->
					<div class="page-header">
						<div class="header-title-section">
							<div class="icon-wrapper">
								<BookOpen class="w-8 h-8 text-accent-orange" />
							</div>
							<div>
								{#if isEditing}
									<form on:submit|preventDefault={saveEdits} class="edit-form">
										<input
											type="text"
											bind:value={editName}
											class="edit-name-input"
											placeholder="List name..."
											disabled={isSaving}
										/>
										<input
											type="text"
											bind:value={editDescription}
											class="edit-desc-input"
											placeholder="Description (optional)..."
											disabled={isSaving}
										/>
										<div class="edit-actions">
											<button type="submit" class="btn-save" disabled={!editName.trim() || isSaving}>
												{#if isSaving}
													<Loader2 class="w-4 h-4 animate-spin" />
												{:else}
													<Check class="w-4 h-4" />
												{/if}
												Save
											</button>
											<button type="button" class="btn-cancel-edit" on:click={cancelEditing}>
												<X class="w-4 h-4" />
												Cancel
											</button>
										</div>
									</form>
								{:else}
									<h1 class="page-title">{listInfo.name}</h1>
									{#if listInfo.description}
										<p class="page-description">{listInfo.description}</p>
									{/if}
									<p class="page-subtitle">{listInfo.comicCount || 0} {(listInfo.comicCount || 0) === 1 ? 'comic' : 'comics'}</p>
								{/if}
							</div>
						</div>

						{#if !isEditing}
							<div class="view-controls">
								<button class="control-button" on:click={startEditing} aria-label="Edit list">
									<Pencil class="w-5 h-5" />
								</button>
								{#if !showDeleteConfirm}
									<button class="control-button delete-btn" on:click={() => { showDeleteConfirm = true; }} aria-label="Delete list">
										<Trash2 class="w-5 h-5" />
									</button>
								{:else}
									<div class="delete-confirm-inline">
										<span class="text-sm text-red-400">Delete this list?</span>
										<button class="btn-confirm-yes" on:click={handleDelete} disabled={isDeleting}>
											{#if isDeleting}
												<Loader2 class="w-4 h-4 animate-spin" />
											{:else}
												Yes
											{/if}
										</button>
										<button class="btn-confirm-no" on:click={() => { showDeleteConfirm = false; }}>No</button>
									</div>
								{/if}

								{#if comics.length > 0}
									<select bind:value={sortBy} class="control-select">
										<option value="position">Sort: List Order</option>
										<option value="title">Sort: Title</option>
										<option value="series">Sort: Series</option>
									</select>
									<button class="control-button" on:click={toggleViewMode} aria-label="Toggle view mode">
										{#if viewMode === 'grid'}
											<Grid class="w-5 h-5" />
										{:else}
											<List class="w-5 h-5" />
										{/if}
									</button>
								{/if}
							</div>
						{/if}
					</div>

					<!-- Error banner (non-blocking) -->
					{#if error}
						<div class="error-banner">
							<p class="text-red-400 text-sm">{error}</p>
							<button class="text-red-300 text-sm underline" on:click={() => { error = null; }}>Dismiss</button>
						</div>
					{/if}

					<!-- Comics -->
					{#if sortedComics.length > 0}
						<div class="comics-{viewMode}">
							{#each sortedComics as comic (comic.id)}
								<div class="comic-item-wrapper">
									<ComicCard
										{comic}
										{libraryId}
										variant={viewMode}
										href={getComicOverviewHref(comic)}
									/>
									<button
										class="remove-btn"
										class:removing={removingComicId === comic.id}
										on:click|stopPropagation|preventDefault={() => handleRemoveComic(comic.id)}
										disabled={removingComicId === comic.id}
										aria-label="Remove from list"
									>
										{#if removingComicId === comic.id}
											<Loader2 class="w-3.5 h-3.5 animate-spin" />
										{:else}
											<Minus class="w-3.5 h-3.5" />
										{/if}
									</button>
								</div>
							{/each}
						</div>
					{:else}
						<div class="empty-state">
							<BookOpen class="w-16 h-16 text-gray-500 mb-4" />
							<p class="text-gray-400 mb-4">This reading list is empty</p>
							<p class="text-gray-500 text-sm mb-6">
								Use the "Add to List" button on any comic to add it here
							</p>
							<a href="/library/all/browse" class="btn-primary">Browse Comics</a>
						</div>
					{/if}
				{/if}
			</div>
		</main>
	</div>
</div>

<style>
	.back-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		padding: 0.25rem 0;
		margin-bottom: 1rem;
		background: none;
		border: none;
		cursor: pointer;
		transition: color 0.2s;
	}

	.back-link:hover {
		color: var(--color-accent, #f97316);
	}

	.page-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		margin-bottom: 2rem;
		gap: 2rem;
	}

	.header-title-section {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
	}

	.icon-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 56px;
		height: 56px;
		background: var(--color-secondary-bg);
		border-radius: 12px;
		flex-shrink: 0;
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.page-description {
		font-size: 0.9rem;
		color: var(--color-text-secondary);
		margin: 0.25rem 0 0 0;
	}

	.page-subtitle {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0.25rem 0 0 0;
	}

	/* Edit Form */
	.edit-form {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.edit-name-input {
		padding: 0.5rem 0.75rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border, #333);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 1.25rem;
		font-weight: 600;
		outline: none;
		transition: border-color 0.2s;
	}

	.edit-name-input:focus {
		border-color: var(--color-accent, #f97316);
	}

	.edit-desc-input {
		padding: 0.4rem 0.75rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border, #333);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 0.875rem;
		outline: none;
		transition: border-color 0.2s;
	}

	.edit-desc-input:focus {
		border-color: var(--color-accent, #f97316);
	}

	.edit-actions {
		display: flex;
		gap: 0.5rem;
	}

	.btn-save {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.4rem 0.75rem;
		background: var(--color-accent, #f97316);
		color: white;
		border: none;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
	}

	.btn-save:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-cancel-edit {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.4rem 0.75rem;
		background: transparent;
		border: 1px solid var(--color-border, #333);
		border-radius: 6px;
		color: var(--color-text-secondary);
		font-size: 0.8rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-cancel-edit:hover {
		border-color: var(--color-text-secondary);
		color: var(--color-text);
	}

	/* View Controls */
	.view-controls {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.control-select {
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		background: var(--color-secondary-bg);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 4px;
		color: var(--color-text);
		cursor: pointer;
	}

	.control-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: 4px;
		background: var(--color-secondary-bg);
		border: 1px solid transparent;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.control-button:hover {
		border-color: var(--color-accent);
		color: var(--color-text);
	}

	.control-button.delete-btn:hover {
		border-color: #ef4444;
		color: #ef4444;
	}

	/* Delete Confirm */
	.delete-confirm-inline {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.btn-confirm-yes {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.35rem 0.65rem;
		background: #ef4444;
		color: white;
		border: none;
		border-radius: 4px;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.btn-confirm-yes:disabled {
		opacity: 0.5;
		cursor: wait;
	}

	.btn-confirm-no {
		padding: 0.35rem 0.65rem;
		background: var(--color-border, #333);
		color: var(--color-text);
		border: none;
		border-radius: 4px;
		font-size: 0.8rem;
		cursor: pointer;
	}

	/* Error banner */
	.error-banner {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 1rem;
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		border-radius: 8px;
		margin-bottom: 1rem;
	}

	/* Comics with remove button */
	.comic-item-wrapper {
		position: relative;
	}

	.remove-btn {
		position: absolute;
		top: 6px;
		right: 6px;
		z-index: 10;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.7);
		border: 1px solid rgba(255, 255, 255, 0.15);
		color: var(--color-text-secondary);
		cursor: pointer;
		opacity: 0;
		transition: all 0.2s;
	}

	.comic-item-wrapper:hover .remove-btn {
		opacity: 1;
	}

	.remove-btn:hover {
		background: rgba(239, 68, 68, 0.9);
		color: white;
		border-color: #ef4444;
	}

	.remove-btn.removing {
		opacity: 1;
		background: rgba(0, 0, 0, 0.7);
	}

	/* Grid and list */
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

	.comics-list .comic-item-wrapper .remove-btn {
		opacity: 1;
		position: static;
		width: auto;
		height: auto;
		padding: 0.3rem 0.6rem;
		border-radius: 6px;
		background: rgba(239, 68, 68, 0.1);
		color: #ef4444;
		border: 1px solid rgba(239, 68, 68, 0.2);
	}

	.comics-list .comic-item-wrapper {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	/* States */
	.loading-container,
	.error-container,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
		text-align: center;
	}

	.btn-primary {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		background: var(--color-accent, #f97316);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		text-decoration: none;
		transition: opacity 0.2s;
	}

	.btn-primary:hover {
		opacity: 0.9;
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

	:global(.text-accent-orange) {
		color: var(--color-accent, #f97316);
	}

	@media (max-width: 768px) {
		.page-header {
			flex-direction: column;
			align-items: flex-start;
		}

		.page-title {
			font-size: 1.5rem;
		}

		.icon-wrapper {
			width: 48px;
			height: 48px;
		}

		.comics-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 1rem;
		}

		.view-controls {
			flex-wrap: wrap;
		}
	}
</style>
