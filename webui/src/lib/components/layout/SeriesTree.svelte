<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import { browser } from '$app/environment';
	import SeriesTreeNode from './SeriesTreeNode.svelte';

	const dispatch = createEventDispatcher();

	export let tree = []; // Array of library nodes from API

	let expandedNodes = new Set(['libraries-root']); // Expand root by default
	let activeNodeId = null;
	let filteredTree = [];

	// Filter tree to remove individual comic files, keeping only libraries and folders
	function filterTreeNodes(nodes) {
		if (!nodes) return [];

		return nodes.map(node => {
			// If node has children, filter them recursively
			if (node.children && node.children.length > 0) {
				// Remove comic-type children, keep folders and libraries
				const filteredChildren = node.children
					.filter(child => child.type !== 'comic')
					.map(child => filterTreeNodes([child])[0])
					.filter(Boolean);

				return {
					...node,
					children: filteredChildren
				};
			}
			return node;
		}).filter(Boolean);
	}

	// Update filtered tree when tree changes
	$: filteredTree = filterTreeNodes(tree);

	// Load expanded state from localStorage
	onMount(() => {
		if (browser) {
			const saved = localStorage.getItem('series-tree-expanded');
			if (saved) {
				try {
					const savedSet = new Set(JSON.parse(saved));
					// Always keep root expanded, merge with saved state
					expandedNodes = new Set(['libraries-root', ...savedSet]);
				} catch (e) {
					console.error('Failed to load tree state:', e);
					expandedNodes = new Set(['libraries-root']);
				}
			}
		}
	});

	// Save expanded state to localStorage
	function saveExpandedState() {
		if (browser) {
			localStorage.setItem(
				'series-tree-expanded',
				JSON.stringify([...expandedNodes])
			);
		}
	}

	function toggleNode(nodeId) {
		if (expandedNodes.has(nodeId)) {
			expandedNodes.delete(nodeId);
		} else {
			expandedNodes.add(nodeId);
		}
		// Create a new Set to trigger Svelte reactivity
		expandedNodes = new Set(expandedNodes);
		saveExpandedState();
	}

	function handleNodeClick(node, event) {
		event.stopPropagation();

		// Set active node
		activeNodeId = node.id;

		// Dispatch filter event based on node type
		// Note: We don't toggle expansion here - only the chevron does that
		if (node.type === 'root') {
			// Show all series from all libraries
			dispatch('filter', {
				type: 'all'
			});
		} else if (node.type === 'library') {
			// Show all series in this library
			dispatch('filter', {
				type: 'library',
				libraryId: node.id,
				libraryName: node.name
			});
		} else if (node.type === 'folder') {
			// Show all comics in this folder and its subfolders
			dispatch('filter', {
				type: 'folder',
				libraryId: node.libraryId,
				folderId: node.folderId,
				folderName: node.name
			});
		} else if (node.type === 'comic') {
			// Navigate to comic reader
			dispatch('filter', {
				type: 'comic',
				libraryId: node.libraryId,
				comicId: node.id,
				comicName: node.name
			});
		}
	}

	// Make isExpanded reactive by recreating it when expandedNodes changes
	$: isExpanded = (nodeId) => expandedNodes.has(nodeId);

	function handleToggle(event) {
		toggleNode(event.detail.nodeId);
	}

	function handleSelect(event) {
		handleNodeClick(event.detail.node, event.detail.event);
	}
</script>

<div class="series-tree">
	{#if filteredTree && filteredTree.length > 0}
		<!-- Root "Libraries" node -->
		<SeriesTreeNode
			node={{
				id: 'libraries-root',
				name: 'Libraries',
				type: 'root',
				children: filteredTree
			}}
			level={0}
			{isExpanded}
			{activeNodeId}
			on:toggle={handleToggle}
			on:select={handleSelect}
		/>
	{:else}
		<div class="tree-loading">
			<p class="text-gray-400">Loading library tree...</p>
		</div>
	{/if}
</div>

<style>
	.series-tree {
		width: 100%;
		overflow-y: auto;
		overflow-x: hidden;
	}

	.tree-loading {
		padding: 1rem;
		text-align: center;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	/* Scrollbar styling */
	.series-tree::-webkit-scrollbar {
		width: 8px;
	}

	.series-tree::-webkit-scrollbar-track {
		background: transparent;
	}

	.series-tree::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.2);
		border-radius: 4px;
	}

	.series-tree::-webkit-scrollbar-thumb:hover {
		background: rgba(255, 255, 255, 0.3);
	}
</style>
