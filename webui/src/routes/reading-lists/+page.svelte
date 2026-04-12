<script>
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import HomeSidebar from '$lib/components/layout/HomeSidebar.svelte';
	import { getReadingLists, createReadingList, deleteReadingList } from '$lib/api/readingLists';
	import { getLibraries, getLibrariesSeriesTree } from '$lib/api/libraries';
	import { List, Plus, Trash2, BookOpen, Grid, Loader2 } from 'lucide-svelte';
	import { goto } from '$app/navigation';

	let allLists = [];
	let libraryMap = {};
	let isLoading = true;
	let error = null;

	// Create new list
	let showCreateForm = false;
	let newListName = '';
	let newListLibraryId = null;
	let isCreating = false;

	// Delete confirmation
	let deleteConfirmId = null;
	let isDeleting = false;

	// Sidebar data
	let libraries = [];
	let seriesTree = [];

	onMount(async () => {
		await Promise.all([loadData(), loadSidebarData()]);
	});

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

	async function loadData() {
		try {
			isLoading = true;
			error = null;

			const libs = await getLibraries();
			libraries = libs || [];

			// Filter out hidden libraries
			const visibleLibraries = libraries.filter(lib => !lib.exclude_from_webui);

			// Build library lookup
			libraryMap = {};
			for (const lib of libraries) {
				libraryMap[lib.id] = lib;
			}

			// Fetch reading lists from visible libraries in parallel
			const results = await Promise.all(
				visibleLibraries.map(lib => getReadingLists(lib.id).catch(() => []))
			);

			// Merge all lists, each already has libraryId from the API
			allLists = results.flat().sort((a, b) => (a.name || '').localeCompare(b.name || ''));

			// Default new-list library to first visible library
			if (visibleLibraries.length > 0 && !newListLibraryId) {
				newListLibraryId = visibleLibraries[0].id;
			}
		} catch (err) {
			console.error('Failed to load reading lists:', err);
			error = err.message;
		} finally {
			isLoading = false;
		}
	}

	async function handleCreate() {
		if (!newListName.trim() || !newListLibraryId) return;
		try {
			isCreating = true;
			const result = await createReadingList(newListLibraryId, newListName.trim());
			if (result?.success) {
				newListName = '';
				showCreateForm = false;
				await loadData();
			}
		} catch (err) {
			console.error('Failed to create reading list:', err);
			error = err.message;
		} finally {
			isCreating = false;
		}
	}

	async function handleDelete(list) {
		try {
			isDeleting = true;
			await deleteReadingList(list.libraryId, list.id);
			deleteConfirmId = null;
			await loadData();
		} catch (err) {
			console.error('Failed to delete reading list:', err);
			error = err.message;
		} finally {
			isDeleting = false;
		}
	}

	function getLibraryName(libraryId) {
		return libraryMap[libraryId]?.name || 'Unknown Library';
	}
</script>

<svelte:head>
	<title>Reading Lists - Kottlib</title>
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]">
	<Navbar />
	<div class="flex flex-1 overflow-hidden">

		<HomeSidebar
			{libraries}
			{seriesTree}
			currentFilter={{ type: 'reading-lists' }}
		/>

		<main class="flex-1 overflow-y-auto px-4 pb-8 scrollbar-thin scrollbar-thumb-[var(--color-border)] scrollbar-track-transparent">
			<div class="w-full pt-4">
				<!-- Page Header -->
				<div class="page-header">
					<div class="header-title-section">
						<div class="icon-wrapper">
							<List class="w-8 h-8 text-accent-orange" />
						</div>
						<div>
							<h1 class="page-title">Reading Lists</h1>
							{#if !isLoading && allLists.length > 0}
								<p class="page-subtitle">{allLists.length} {allLists.length === 1 ? 'list' : 'lists'}</p>
							{/if}
						</div>
					</div>

					<div class="view-controls">
						<button
							class="btn-create"
							on:click={() => { showCreateForm = !showCreateForm; }}
						>
							<Plus class="w-5 h-5" />
							<span>New List</span>
						</button>
					</div>
				</div>

				<!-- Create Form -->
				{#if showCreateForm}
					<div class="create-form-container">
						<form on:submit|preventDefault={handleCreate} class="create-form">
							<input
								type="text"
								bind:value={newListName}
								placeholder="Reading list name..."
								class="create-input"
								disabled={isCreating}
							/>
						{#if libraries.filter(l => !l.exclude_from_webui).length > 1}
							<select bind:value={newListLibraryId} class="library-select" disabled={isCreating}>
								{#each libraries.filter(l => !l.exclude_from_webui) as lib}
										<option value={lib.id}>{lib.name}</option>
									{/each}
								</select>
							{/if}
							<button
								type="submit"
								class="btn-submit"
								disabled={!newListName.trim() || isCreating}
							>
								{#if isCreating}
									<Loader2 class="w-4 h-4 animate-spin" />
								{:else}
									<Plus class="w-4 h-4" />
								{/if}
								Create
							</button>
							<button
								type="button"
								class="btn-cancel"
								on:click={() => { showCreateForm = false; newListName = ''; }}
							>
								Cancel
							</button>
						</form>
					</div>
				{/if}

				<!-- Content -->
				{#if isLoading}
					<div class="loading-container">
						<div class="spinner"></div>
						<p class="text-gray-400 mt-4">Loading reading lists...</p>
					</div>
				{:else if error}
					<div class="error-container">
						<p class="text-red-400">Failed to load reading lists: {error}</p>
						<button class="btn-primary mt-4" on:click={loadData}>Try Again</button>
					</div>
				{:else if allLists.length > 0}
					<div class="lists-grid">
						{#each allLists as list, listIndex (`${list.libraryId || "library"}::${list.id}::${listIndex}`)}
							<div class="list-card">
								<button
									class="list-card-body"
									on:click={() => goto(`/reading-lists/${list.libraryId}/${list.id}`)}
								>
									<div class="list-card-icon">
										<BookOpen class="w-6 h-6" />
									</div>
									<div class="list-card-info">
										<h3 class="list-card-name">{list.name}</h3>
										{#if list.description}
											<p class="list-card-desc">{list.description}</p>
										{/if}
										<div class="list-card-meta">
											<span class="meta-badge">{list.comicCount || 0} {(list.comicCount || 0) === 1 ? 'comic' : 'comics'}</span>
											{#if libraries.filter(l => !l.exclude_from_webui).length > 1}
												<span class="meta-badge library-badge">{getLibraryName(list.libraryId)}</span>
											{/if}
										</div>
									</div>
								</button>

								<!-- Delete Button -->
								<div class="list-card-actions">
									{#if deleteConfirmId === list.id}
										<div class="delete-confirm">
											<span class="text-sm text-red-400">Delete?</span>
											<button
												class="btn-confirm-delete"
												on:click={() => handleDelete(list)}
												disabled={isDeleting}
											>
												{#if isDeleting}
													<Loader2 class="w-4 h-4 animate-spin" />
												{:else}
													Yes
												{/if}
											</button>
											<button
												class="btn-confirm-cancel"
												on:click={() => { deleteConfirmId = null; }}
											>
												No
											</button>
										</div>
									{:else}
										<button
											class="btn-delete"
											on:click|stopPropagation={() => { deleteConfirmId = list.id; }}
											aria-label="Delete list"
										>
											<Trash2 class="w-4 h-4" />
										</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="empty-state">
						<BookOpen class="w-16 h-16 text-gray-500 mb-4" />
						<p class="text-gray-400 mb-4">You haven't created any reading lists yet</p>
						<p class="text-gray-500 text-sm mb-6">
							Create a reading list to organize your comics, or use the "Add to List" button on any comic
						</p>
						<button class="btn-primary" on:click={() => { showCreateForm = true; }}>
							<Plus class="w-5 h-5" />
							Create Your First List
						</button>
					</div>
				{/if}
			</div>
		</main>
	</div>
</div>

<style>
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 2rem;
		gap: 2rem;
	}

	.header-title-section {
		display: flex;
		align-items: center;
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
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.page-subtitle {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0.25rem 0 0 0;
	}

	.view-controls {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.btn-create {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: var(--color-accent, #f97316);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.btn-create:hover {
		opacity: 0.9;
	}

	/* Create Form */
	.create-form-container {
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-border, #333);
		border-radius: 12px;
		padding: 1rem 1.25rem;
		margin-bottom: 1.5rem;
	}

	.create-form {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.create-input {
		flex: 1;
		min-width: 200px;
		padding: 0.5rem 0.75rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border, #333);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 0.875rem;
		outline: none;
		transition: border-color 0.2s;
	}

	.create-input:focus {
		border-color: var(--color-accent, #f97316);
	}

	.create-input::placeholder {
		color: var(--color-text-secondary);
	}

	.library-select {
		padding: 0.5rem 0.75rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border, #333);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.btn-submit {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.5rem 0.75rem;
		background: var(--color-accent, #f97316);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.btn-submit:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-cancel {
		padding: 0.5rem 0.75rem;
		background: transparent;
		border: 1px solid var(--color-border, #333);
		border-radius: 8px;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-cancel:hover {
		border-color: var(--color-text-secondary);
		color: var(--color-text);
	}

	/* Lists Grid */
	.lists-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 1rem;
	}

	.list-card {
		display: flex;
		align-items: stretch;
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-border, #333);
		border-radius: 12px;
		overflow: hidden;
		transition: all 0.2s;
	}

	.list-card:hover {
		border-color: var(--color-accent, #f97316);
	}

	.list-card-body {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 1.25rem;
		text-align: left;
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		min-width: 0;
	}

	.list-card-icon {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		background: rgba(249, 115, 22, 0.1);
		border-radius: 10px;
		color: var(--color-accent, #f97316);
	}

	.list-card-info {
		flex: 1;
		min-width: 0;
	}

	.list-card-name {
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.list-card-desc {
		font-size: 0.8rem;
		color: var(--color-text-secondary);
		margin: 0.2rem 0 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.list-card-meta {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.5rem;
		flex-wrap: wrap;
	}

	.meta-badge {
		font-size: 0.75rem;
		padding: 0.15rem 0.5rem;
		background: rgba(255, 255, 255, 0.06);
		border-radius: 4px;
		color: var(--color-text-secondary);
	}

	.library-badge {
		background: rgba(249, 115, 22, 0.12);
		color: var(--color-accent, #f97316);
	}

	.list-card-actions {
		display: flex;
		align-items: center;
		padding: 0 0.75rem;
		border-left: 1px solid var(--color-border, #333);
	}

	.btn-delete {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 6px;
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-delete:hover {
		background: rgba(239, 68, 68, 0.15);
		color: #ef4444;
	}

	.delete-confirm {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.btn-confirm-delete {
		padding: 0.25rem 0.5rem;
		background: #ef4444;
		color: white;
		border: none;
		border-radius: 4px;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.btn-confirm-delete:disabled {
		opacity: 0.5;
		cursor: wait;
	}

	.btn-confirm-cancel {
		padding: 0.25rem 0.5rem;
		background: var(--color-border, #333);
		color: var(--color-text);
		border: none;
		border-radius: 4px;
		font-size: 0.75rem;
		cursor: pointer;
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

		.lists-grid {
			grid-template-columns: 1fr;
		}

		.create-form {
			flex-direction: column;
		}

		.create-input {
			min-width: 0;
			width: 100%;
		}
	}
</style>
