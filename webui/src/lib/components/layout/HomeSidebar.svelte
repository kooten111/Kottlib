<script>
	import { createEventDispatcher } from "svelte";
	import {
		Library,
		FolderOpen,
		Heart,
		BookOpen,
		Layers,
		List,
		X,
	} from "lucide-svelte";
	import { tooltip } from "$lib/actions/tooltip";
	import SeriesTreeNode from "./SeriesTreeNode.svelte";
	import { treeExpandedNodes } from "$stores/library";
	import { uiStore } from "$stores/ui";

	import { goto } from "$app/navigation";
	import { browser } from "$app/environment";

	const dispatch = createEventDispatcher();

	// Resize state - read from localStorage synchronously to prevent FOUC
	let sidebarWidth = browser
		? parseInt(localStorage.getItem("sidebar-width") || "256", 10)
		: 256;
	let isResizing = false;

	function startResize(e) {
		isResizing = true;
		document.body.style.cursor = "col-resize";
		document.body.style.userSelect = "none";
		window.addEventListener("mousemove", handleResize);
		window.addEventListener("mouseup", stopResize);
	}

	function handleResize(e) {
		if (!isResizing) return;
		let newWidth = e.clientX;
		const MIN_WIDTH = 160;
		const MAX_WIDTH = 448;
		if (newWidth < MIN_WIDTH) newWidth = MIN_WIDTH;
		if (newWidth > MAX_WIDTH) newWidth = MAX_WIDTH;
		sidebarWidth = newWidth;
	}

	function stopResize() {
		isResizing = false;
		document.body.style.cursor = "";
		document.body.style.userSelect = "";
		window.removeEventListener("mousemove", handleResize);
		window.removeEventListener("mouseup", stopResize);
		localStorage.setItem("sidebar-width", sidebarWidth.toString());
	}

	export let libraries = [];
	export let seriesTree = [];
	export let currentFilter = null;
	export let currentView = "home"; // 'home', 'favorites', 'continue'

	$: visibleLibraries = libraries.filter((lib) => !lib.exclude_from_webui);

	// Derived state for folders
	// Use libraryId from both "library" and "folder" filter types
	$: selectedLibraryId =
		currentFilter?.type === "library" || currentFilter?.type === "folder"
			? currentFilter.libraryId
			: null;
	$: selectedLibraryNode = seriesTree.find(
		(node) => node.id === selectedLibraryId,
	);

	// Add paths to folder nodes for proper navigation links
	function addPathsToNodes(nodes, parentPath = "", libraryId = null) {
		if (!nodes) return [];
		return nodes.map((node) => {
			let currentPath = parentPath;
			if (node.type === "folder") {
				currentPath = parentPath
					? `${parentPath}/${node.name}`
					: node.name;
			}
			const newNode = {
				...node,
				path: currentPath,
				libraryId: libraryId || node.libraryId,
			};
			if (node.children && node.children.length > 0) {
				newNode.children = addPathsToNodes(
					node.children,
					currentPath,
					libraryId || node.libraryId,
				);
			}
			return newNode;
		});
	}

	$: folderNodes = addPathsToNodes(
		selectedLibraryNode?.children || [],
		"",
		selectedLibraryId,
	);

	// Helper to check if a library is active
	$: isLibraryActive = (libId) =>
		currentFilter?.type === "library" && currentFilter.libraryId === libId;
	$: isAllLibrariesActive = !currentFilter || currentFilter.type === "all";

	function handleLibraryClick(lib) {
		goto(`/library/${lib.id}/browse`);
	}

	function handleAllLibrariesClick() {
		goto("/");
	}

	function handleViewChange(view) {
		dispatch("viewChange", view);
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
			if (typeof window !== "undefined") {
				localStorage.setItem(
					"series-tree-expanded",
					JSON.stringify([...newNodes]),
				);
			}
			return newNodes;
		});
	}

	function handleSelect(event) {
		// Forward selection to parent
		const { node } = event.detail;
		if (node.type === "folder") {
			dispatch("filter", {
				type: "folder",
				libraryId: node.libraryId,
				folderId: node.folderId,
				folderName: node.name,
			});
		} else if (node.type === "comic") {
			dispatch("filter", {
				type: "comic",
				libraryId: node.libraryId,
				comicId: node.id,
				comicName: node.name,
			});
		}
	}

	$: isExpanded = (nodeId) => $treeExpandedNodes.has(nodeId);

	// Mobile breakpoint constant
	const MOBILE_BREAKPOINT = 1024;

	// Helper function to check if we're on mobile and close sidebar
	function closeSidebarOnMobile() {
		if (window.innerWidth < MOBILE_BREAKPOINT) {
			uiStore.closeSidebar();
		}
	}

	function handleLibraryClickWrapper(lib) {
		handleLibraryClick(lib);
		closeSidebarOnMobile();
	}

	function handleAllLibrariesClickWrapper() {
		handleAllLibrariesClick();
		closeSidebarOnMobile();
	}

	function handleViewChangeWrapper(view) {
		handleViewChange(view);
		closeSidebarOnMobile();
	}
</script>

<!-- Mobile Backdrop Overlay -->
{#if $uiStore.isSidebarOpen}
	<div
		class="sidebar-backdrop"
		on:click={() => uiStore.closeSidebar()}
		on:keydown={(e) => e.key === "Escape" && uiStore.closeSidebar()}
		role="button"
		tabindex="0"
		aria-label="Close sidebar"
	></div>
{/if}

<aside
	class="sidebar"
	class:sidebar-open={$uiStore.isSidebarOpen}
	style="width: {sidebarWidth}px;"
>
	<div class="sidebar-content">
		<!-- LIBRARIES SECTION -->
		<div class="sidebar-section">
			<div class="section-header">
				<span
					class="text-xs font-bold text-gray-500 uppercase tracking-wider"
					>Libraries</span
				>
				<button
					class="text-gray-500 hover:text-white"
					title="Add Library"
				>
					<!-- Plus icon would go here if we had add functionality implemented -->
				</button>
			</div>

			<div class="section-content">
				<div class="sidebar-item-container w-full">
					<button
						class="sidebar-item w-full"
						class:active={isAllLibrariesActive &&
							currentView === "home"}
						on:click={handleAllLibrariesClickWrapper}
						use:tooltip={{ content: "All Libraries" }}
					>
						<Layers class="w-4 h-4" />
						<span class="item-text">All Libraries</span>
					</button>
				</div>

				{#each visibleLibraries as lib}
					<div class="sidebar-item-container w-full">
						<button
							class="sidebar-item w-full"
							class:active={isLibraryActive(lib.id) &&
								currentView === "home"}
							on:click={() => handleLibraryClickWrapper(lib)}
							use:tooltip={{ content: lib.name }}
						>
							<Library class="w-4 h-4" />
							<span class="item-text">{lib.name}</span>
						</button>
					</div>
				{/each}
			</div>
		</div>

		<!-- FOLDERS SECTION -->
		<div class="sidebar-section flex-1 folders-section">
			<div class="section-header">
				<span
					class="text-xs font-bold text-gray-500 uppercase tracking-wider"
					>Folders</span
				>
				<div class="flex gap-2">
					<!-- Action icons could go here -->
				</div>
			</div>

			<div class="section-content folders-content">
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
						<div class="text-sm text-gray-500 px-3 py-2 italic">
							No folders
						</div>
					{/if}
				{:else}
					<div class="text-sm text-gray-500 px-3 py-2 italic">
						Select a library to view folders
					</div>
				{/if}
			</div>
		</div>

		<!-- READING LISTS SECTION -->
		<div class="sidebar-section mt-auto border-t border-gray-700">
			<div class="section-header">
				<span
					class="text-xs font-bold text-gray-500 uppercase tracking-wider"
					>Reading Lists</span
				>
			</div>

			<div class="section-content">
				<button
					class="sidebar-item"
					class:active={currentView === "favorites"}
					on:click={() => handleViewChangeWrapper("favorites")}
					use:tooltip={{ content: "Favorites" }}
				>
					<Heart class="w-4 h-4" />
					<span class="item-text">Favorites</span>
				</button>

				<button
					class="sidebar-item"
					class:active={currentView === "continue"}
					on:click={() => handleViewChangeWrapper("continue")}
					use:tooltip={{ content: "Continue Reading" }}
				>
					<BookOpen class="w-4 h-4" />
					<span class="item-text">Continue Reading</span>
				</button>
			</div>
		</div>
	</div>
	<!-- Resize Handle -->
	<div
		class="resize-handle"
		on:mousedown={startResize}
		on:keydown={(e) => {
			if (e.key === "ArrowLeft")
				sidebarWidth = Math.max(160, sidebarWidth - 10);
			if (e.key === "ArrowRight")
				sidebarWidth = Math.min(448, sidebarWidth + 10);
		}}
		role="slider"
		tabindex="0"
		aria-label="Resize sidebar"
		aria-orientation="horizontal"
		aria-valuemin="160"
		aria-valuemax="448"
		aria-valuenow={sidebarWidth}
	></div>
</aside>

<style>
	.sidebar {
		min-width: 10rem;
		max-width: 28rem;
		background: var(--color-secondary-bg);
		border-right: 1px solid rgb(55, 65, 81);
		display: flex;
		flex-direction: row;
		height: 100%;
		flex-shrink: 0;
		position: relative;
		overflow: hidden;
	}

	.sidebar-content {
		flex: 1;
		overflow: hidden;
		overflow-x: hidden;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.folders-section {
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.folders-content {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: hidden;
	}

	/* Mobile drawer styles */
	@media (max-width: 1023px) {
		.sidebar {
			position: fixed;
			top: 0;
			left: 0;
			bottom: 0;
			width: 280px;
			z-index: 100;
			transform: translateX(-100%);
			transition: transform 0.3s ease-in-out;
		}

		.sidebar.sidebar-open {
			transform: translateX(0);
		}

		.sidebar-content {
			overflow-y: auto;
		}

		.folders-section {
			display: block;
			min-height: auto;
		}

		.folders-content {
			flex: initial;
			min-height: auto;
			overflow: visible;
		}
	}

	.sidebar-backdrop {
		display: none;
	}

	@media (max-width: 1023px) {
		.sidebar-backdrop {
			display: block;
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, 0.5);
			z-index: 90;
			cursor: pointer;
		}
	}

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

	.resize-handle {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		width: 6px;
		cursor: col-resize;
		z-index: 100;
		background: rgba(255, 255, 255, 0.05);
		transition: background-color 0.2s;
	}

	.resize-handle:hover {
		background-color: var(--color-accent);
	}

	@media (max-width: 1023px) {
		.resize-handle {
			display: none;
		}
	}
</style>
