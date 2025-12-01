<script>
	import { createEventDispatcher } from 'svelte';
	import { Library, FolderOpen, Heart, BookOpen, Layers, List } from 'lucide-svelte';
	import SeriesTreeNode from './SeriesTreeNode.svelte';
	import { treeExpandedNodes } from '$stores/library';

	const dispatch = createEventDispatcher();

	export let libraries = [];
	export let seriesTree = [];
	export let currentFilter = null;
	export let currentView = 'home'; // 'home', 'favorites', 'continue'

	// Derived state for folders
	$: selectedLibraryId = currentFilter?.type === 'library' ? currentFilter.libraryId : null;
	$: selectedLibraryNode = seriesTree.find((node) => node.id === selectedLibraryId);
	$: folderNodes = selectedLibraryNode?.children || [];

	// Helper to check if a library is active
	$: isLibraryActive = (libId) =>
		currentFilter?.type === 'library' && currentFilter.libraryId === libId;
	$: isAllLibrariesActive = !currentFilter || currentFilter.type === 'all';

	function handleLibraryClick(lib) {
		dispatch('filter', {
			type: 'library',
			libraryId: lib.id,
			libraryName: lib.name
		});
	}

	function handleAllLibrariesClick() {
		dispatch('filter', { type: 'all' });
	}

	function handleViewChange(view) {
		dispatch('viewChange', view);
	}

	// Forward events from SeriesTreeNode
	function handleToggle(event) {
		// We need to update the store here since SeriesTreeNode just dispatches
		const nodeId = event.detail.nodeId;
		treeExpandedNodes.update((nodes) => {
			const newNodes = new Set(nodes);
			if (newNodes.has(nodeId)) {
				newNodes.delete(nodeId);
			} else {
				newNodes.add(nodeId);
			}
			// Persist to localStorage
			if (typeof window !== 'undefined') {
				localStorage.setItem('series-tree-expanded', JSON.stringify([...newNodes]));
			}
			return newNodes;
		});
	}

	function handleSelect(event) {
		// Forward selection to parent
		const { node } = event.detail;
		if (node.type === 'folder') {
			dispatch('filter', {
				type: 'folder',
				libraryId: node.libraryId,
				folderId: node.folderId,
				folderName: node.name
			});
		} else if (node.type === 'comic') {
			dispatch('filter', {
				type: 'comic',
				libraryId: node.libraryId,
				comicId: node.id,
				comicName: node.name
			});
		}
	}

	$: isExpanded = (nodeId) => $treeExpandedNodes.has(nodeId);
</script>

<aside
	class="w-64 bg-dark-bg-secondary border-r border-gray-700 flex flex-col h-full overflow-y-auto shrink-0"
>
	<!-- LIBRARIES SECTION -->
	<div class="sidebar-section">
		<div class="section-header">
			<span class="text-xs font-bold text-gray-500 uppercase tracking-wider">Libraries</span>
			<button class="text-gray-500 hover:text-white" title="Add Library">
				<!-- Plus icon would go here if we had add functionality implemented -->
			</button>
		</div>

		<div class="section-content">
			<button
				class="sidebar-item"
				class:active={isAllLibrariesActive && currentView === 'home'}
				on:click={handleAllLibrariesClick}
			>
				<Layers class="w-4 h-4" />
				<span class="truncate">All Libraries</span>
			</button>

			{#each libraries as lib}
				<button
					class="sidebar-item"
					class:active={isLibraryActive(lib.id) && currentView === 'home'}
					on:click={() => handleLibraryClick(lib)}
				>
					<Library class="w-4 h-4" />
					<span class="truncate">{lib.name}</span>
				</button>
			{/each}
		</div>
	</div>

	<!-- FOLDERS SECTION -->
	<div class="sidebar-section flex-1">
		<div class="section-header">
			<span class="text-xs font-bold text-gray-500 uppercase tracking-wider">Folders</span>
			<div class="flex gap-2">
				<!-- Action icons could go here -->
			</div>
		</div>

		<div class="section-content">
			{#if selectedLibraryId}
				{#if folderNodes.length > 0}
					{#each folderNodes as node (node.id)}
						<SeriesTreeNode
							{node}
							level={0}
							{isExpanded}
							activeNodeId={currentFilter?.folderId}
							on:toggle={handleToggle}
							on:select={handleSelect}
						/>
					{/each}
				{:else}
					<div class="text-sm text-gray-500 px-3 py-2 italic">No folders</div>
				{/if}
			{:else}
				<div class="text-sm text-gray-500 px-3 py-2 italic">Select a library to view folders</div>
			{/if}
		</div>
	</div>

	<!-- READING LISTS SECTION -->
	<div class="sidebar-section mt-auto border-t border-gray-700">
		<div class="section-header">
			<span class="text-xs font-bold text-gray-500 uppercase tracking-wider">Reading Lists</span>
		</div>

		<div class="section-content">
			<button
				class="sidebar-item"
				class:active={currentView === 'favorites'}
				on:click={() => handleViewChange('favorites')}
			>
				<Heart class="w-4 h-4" />
				<span>Favorites</span>
			</button>

			<button
				class="sidebar-item"
				class:active={currentView === 'continue'}
				on:click={() => handleViewChange('continue')}
			>
				<BookOpen class="w-4 h-4" />
				<span>Continue Reading</span>
			</button>
		</div>
	</div>
</aside>

<style>
	.sidebar-section {
		padding: 1rem 0;
	}

	.section-header {
		padding: 0 1rem 0.5rem;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.section-content {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.sidebar-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 1rem;
		width: 100%;
		text-align: left;
		color: var(--color-text-secondary);
		transition: all 0.2s;
		border-left: 3px solid transparent;
	}

	.sidebar-item:hover {
		background: rgba(255, 255, 255, 0.05);
		color: var(--color-text);
	}

	.sidebar-item.active {
		background: rgba(255, 103, 64, 0.1);
		color: var(--color-accent);
		border-left-color: var(--color-accent);
	}
</style>
