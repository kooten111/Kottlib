<script>
	import { createEventDispatcher, onMount } from "svelte";
	import { browser } from "$app/environment";
	import { treeExpandedNodes } from "$lib/stores/library";
	import SeriesTreeNode from "./SeriesTreeNode.svelte";

	const dispatch = createEventDispatcher();

	export let tree = []; // Array of library nodes from API
	export let currentFilter = null;

	let activeNodeId = null;
	let filteredTree = [];

	// Update activeNodeId based on currentFilter
	$: if (currentFilter) {
		if (currentFilter.type === "all") {
			activeNodeId = "libraries-root";
		} else if (currentFilter.type === "library") {
			activeNodeId = currentFilter.libraryId;
		} else if (currentFilter.type === "folder") {
			activeNodeId = currentFilter.folderId;
		}
	} else {
		activeNodeId = null;
	}

	// Filter tree to remove individual comic files and add paths
	function filterTreeNodes(nodes, parentPath = "") {
		if (!nodes) return [];

		return nodes
			.map((node) => {
				let currentPath = parentPath;

				// Calculate path for this node
				if (node.type === "folder") {
					// Encode node name for path construction? No, keep raw for display/logic, encode in href
					currentPath = parentPath
						? `${parentPath}/${node.name}`
						: node.name;
				}

				const newNode = { ...node, path: currentPath };

				// If node has children, filter them recursively
				if (node.children && node.children.length > 0) {
					// For library nodes, reset path for children (they start at root)
					const childPath =
						node.type === "library" ? "" : currentPath;

					// Remove comic-type children, keep folders and libraries
					const filteredChildren = node.children
						.filter((child) => child.type !== "comic")
						.map((child) => filterTreeNodes([child], childPath)[0])
						.filter(Boolean);

					newNode.children = filteredChildren;
				}
				return newNode;
			})
			.filter(Boolean);
	}

	// Update filtered tree when tree changes
	$: filteredTree = filterTreeNodes(tree);

	// Load expanded state from localStorage
	onMount(() => {
		if (browser) {
			const saved = localStorage.getItem("series-tree-expanded");
			if (saved) {
				try {
					const savedSet = new Set(JSON.parse(saved));
					// Always keep root expanded, merge with saved state
					treeExpandedNodes.set(
						new Set(["libraries-root", ...savedSet]),
					);
				} catch (e) {
					console.error("Failed to load tree state:", e);
					treeExpandedNodes.set(new Set(["libraries-root"]));
				}
			}
		}
	});

	// Save expanded state to localStorage
	function saveExpandedState(nodes) {
		if (browser) {
			localStorage.setItem(
				"series-tree-expanded",
				JSON.stringify([...nodes]),
			);
		}
	}

	function toggleNode(nodeId) {
		treeExpandedNodes.update((nodes) => {
			const newNodes = new Set(nodes);
			if (newNodes.has(nodeId)) {
				newNodes.delete(nodeId);
			} else {
				newNodes.add(nodeId);
			}
			saveExpandedState(newNodes);
			return newNodes;
		});
	}

	function handleNodeClick(node, event) {
		event.stopPropagation();

		// Set active node
		activeNodeId = node.id;

		// Dispatch filter event based on node type
		// Note: We don't toggle expansion here - only the chevron does that
		if (node.type === "root") {
			// Show all series from all libraries
			dispatch("filter", {
				type: "all",
			});
		} else if (node.type === "library") {
			// Show all series in this library
			dispatch("filter", {
				type: "library",
				libraryId: node.id,
				libraryName: node.name,
			});
		} else if (node.type === "folder") {
			// Show all comics in this folder and its subfolders
			dispatch("filter", {
				type: "folder",
				libraryId: node.libraryId,
				folderId: node.folderId,
				folderName: node.name,
			});
		} else if (node.type === "comic") {
			// Navigate to comic reader
			dispatch("filter", {
				type: "comic",
				libraryId: node.libraryId,
				comicId: node.id,
				comicName: node.name,
			});
		}
	}

	import { getFolderTree } from "$lib/api/libraries";

	// Make isExpanded reactive by recreating it when treeExpandedNodes changes
	$: isExpanded = (nodeId) => $treeExpandedNodes.has(nodeId);

	async function handleToggle(event) {
		const { nodeId, node } = event.detail;
		toggleNode(nodeId);

		// If expanding and no children loaded, fetch them
		if (
			$treeExpandedNodes.has(nodeId) &&
			(!node.children || node.children.length === 0)
		) {
			console.log("Lazy loading children for node:", node.name);
			try {
				let children = [];
				// If it's a library node
				if (node.type === "library") {
					// Fetch library root folders
					// We use a specific call for shallow tree
					const response = await getFolderTree(node.id, 0); // 0 = shallow/1-level
					children = response.children || [];
				}
				// If it's a folder node
				else if (node.type === "folder") {
					// We need to fetch children of this folder
					// Refactor getFolderTree to accept folderId or use getLibraryFolders
					// Using getFolderTree with folder_id param (to be implemented in API wrapper)
					const response = await getFolderTree(
						node.libraryId || node.parent_id,
						0,
						node.id,
					);
					children = response.children || [];
				}

				if (children.length > 0) {
					// Update the tree with new children
					// We need to find the node in the tree structure and update it
					updateNodeChildren(tree, nodeId, children);
					tree = [...tree]; // Trigger reactivity
				}
			} catch (err) {
				console.error("Failed to lazy load tree nodes:", err);
			}
		}
	}

	function updateNodeChildren(nodes, targetId, children) {
		for (let node of nodes) {
			if (node.id === targetId) {
				node.children = children;
				return true;
			}
			if (node.children && node.children.length > 0) {
				if (updateNodeChildren(node.children, targetId, children))
					return true;
			}
		}
		return false;
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
				id: "libraries-root",
				name: "Libraries",
				type: "root",
				children: filteredTree,
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
