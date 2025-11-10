<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import { browser } from '$app/environment';
	import TreeNode from './TreeNode.svelte';

	const dispatch = createEventDispatcher();

	export let libraryId = null;
	export let tree = null; // Tree data from API

	let expandedNodes = new Set();
	let activeNodeId = null;

	// Debug: Log when tree changes
	$: if (tree) {
		console.log('LibraryTree received tree:', tree);
	}

	// Load expanded state from localStorage
	onMount(() => {
		if (browser) {
			const saved = localStorage.getItem(`library-tree-expanded-${libraryId}`);
			if (saved) {
				try {
					expandedNodes = new Set(JSON.parse(saved));
				} catch (e) {
					console.error('Failed to load tree state:', e);
				}
			}
		}
	});

	// Save expanded state to localStorage
	function saveExpandedState() {
		if (browser && libraryId) {
			localStorage.setItem(
				`library-tree-expanded-${libraryId}`,
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
		expandedNodes = expandedNodes; // Trigger reactivity
		saveExpandedState();
	}

	function handleNodeClick(node, event) {
		event.stopPropagation();

		if (node.type === 'folder') {
			// Toggle expand/collapse
			toggleNode(node.id);
			// Also dispatch filter event
			dispatch('filter', { folderId: node.id, folderName: node.name });
			activeNodeId = node.id;
		} else {
			// For non-folder nodes, just filter
			dispatch('filter', { folderId: node.id, folderName: node.name });
			activeNodeId = node.id;
		}
	}

	function isExpanded(nodeId) {
		return expandedNodes.has(nodeId);
	}

	function handleToggle(event) {
		toggleNode(event.detail.nodeId);
	}

	function handleSelect(event) {
		handleNodeClick(event.detail.node, event.detail.event);
	}
</script>

<div class="library-tree">
	{#if tree}
		<TreeNode
			node={tree}
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
	.library-tree {
		width: 100%;
		overflow-y: auto;
		overflow-x: hidden;
	}

	.tree-loading {
		padding: 1rem;
		text-align: center;
	}

	/* Scrollbar styling */
	.library-tree::-webkit-scrollbar {
		width: 8px;
	}

	.library-tree::-webkit-scrollbar-track {
		background: transparent;
	}

	.library-tree::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.2);
		border-radius: 4px;
	}

	.library-tree::-webkit-scrollbar-thumb:hover {
		background: rgba(255, 255, 255, 0.3);
	}
</style>
