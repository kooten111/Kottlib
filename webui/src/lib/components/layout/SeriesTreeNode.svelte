<script>
	import { createEventDispatcher } from "svelte";
	import {
		ChevronRight,
		ChevronDown,
		Library,
		FolderOpen,
		Book,
	} from "lucide-svelte";
	import { tooltip } from "$lib/actions/tooltip";

	const dispatch = createEventDispatcher();

	export let node = null;
	export let level = 0;
	export let isExpanded = () => false;
	export let activeNodeId = null;

	function handleToggle(e) {
		e.stopPropagation();
		dispatch("toggle", { nodeId: node.id });
	}

	function handleSelect(e) {
		e.stopPropagation();
		dispatch("select", { node, event: e });
	}

	function getHref(node) {
		if (!node) return "#";
		if (node.type === "root") return "/";
		if (node.type === "library") return `/library/${node.id}/browse`;
		if (node.type === "folder") {
			if (node.name === "__ROOT__") {
				return `/library/${node.libraryId}/browse`;
			}
			const browsePath = node.idPath || `${node.id}`;
			return `/library/${node.libraryId}/browse/${browsePath}`;
		}
		if (node.type === "comic") {
			return `/comic/${node.libraryId}/${node.id}/read`;
		}
		return "#";
	}

	function getIcon(nodeType) {
		if (nodeType === "root") return Library;
		if (nodeType === "library") return Library;
		if (nodeType === "folder") return FolderOpen;
		return Book;
	}

	$: hasChildren = node && node.children && node.children.length > 0;
	$: expanded = isExpanded(node?.id);
	$: isActive = node && node.id === activeNodeId;
	$: Icon = getIcon(node?.type);
</script>

{#if node}
	<div class="tree-node" style="--level: {level}">
		<div class="node-row">
			<!-- Expand/Collapse Icon -->
			{#if hasChildren}
				<button
					class="toggle-button"
					on:click={handleToggle}
					type="button"
				>
					{#if expanded}
						<ChevronDown class="w-4 h-4" />
					{:else}
						<ChevronRight class="w-4 h-4" />
					{/if}
				</button>
			{:else}
				<span class="toggle-spacer"></span>
			{/if}

			<!-- Node content -->
			<a
				href={getHref(node)}
				class="node-button"
				class:active={isActive}
				class:has-children={hasChildren}
				on:click={handleSelect}
				use:tooltip={{ content: node.name }}
			>
				<!-- Node Icon -->
				<span
					class="node-icon"
					class:root={node.type === "root"}
					class:library={node.type === "library"}
					class:folder={node.type === "folder"}
				>
					<svelte:component this={Icon} class="w-4 h-4" />
				</span>

				<!-- Node Label -->
				<div class="flex-1 min-w-0 flex flex-col items-start">
					<span class="item-text text-left w-full">{node.name}</span>
				</div>

				<!-- Comic Count Badge (for libraries and folders) -->
				{#if (node.type === "folder" || node.type === "library") && node.comicCount}
					<span class="count-badge">{node.comicCount}</span>
				{/if}
			</a>
		</div>

		<!-- Children (recursively rendered) -->
		{#if hasChildren && expanded}
			<div class="children">
				{#each node.children as child, childIndex (child.path ? `${child.path}::${child.id}` : `${child.name || "node"}::${child.id}::${childIndex}`)}
					<svelte:self
						node={child}
						level={level + 1}
						{isExpanded}
						{activeNodeId}
						on:toggle
						on:select
					/>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.tree-node {
		width: 100%;
	}

	.node-row {
		display: flex;
		align-items: center;
		width: 100%;
		padding-left: calc(0.5rem + var(--level) * 1rem);
	}

	.node-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
		padding: 0.5rem;
		background: none;
		border: none;
		color: var(--color-text);
		text-align: left;
		cursor: pointer;
		transition: background 0.2s;
		border-radius: 4px;
		font-size: 0.875rem;
	}

	.node-button:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.node-button.active {
		background: rgba(255, 103, 64, 0.15);
		color: var(--color-accent);
	}

	.toggle-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		padding: 0;
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		flex-shrink: 0;
	}

	.toggle-button:hover {
		color: var(--color-text);
	}

	.toggle-spacer {
		width: 20px;
		flex-shrink: 0;
	}

	.node-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--color-text-secondary);
		flex-shrink: 0;
	}

	.node-icon.root {
		color: var(--color-accent);
	}

	.node-icon.library {
		color: var(--color-accent);
	}

	.node-icon.folder {
		color: #888;
	}

	.count-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 20px;
		height: 18px;
		padding: 0 6px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 9px;
		font-size: 0.7rem;
		color: var(--color-text-secondary);
		flex-shrink: 0;
	}

	.children {
		width: 100%;
	}
</style>
