<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let node;
	export let level = 0;
	export let isExpanded;
	export let activeNodeId;
	export let isRoot = false;

	$: hasChildren = node.children && node.children.length > 0;
	$: expanded = isExpanded(node.id);
	$: isActive = activeNodeId === node.id;

	function handleClick(event) {
		console.log('TreeNode handleClick:', node.name, node.id);
		dispatch('select', { node, event });
	}

	function handleToggle(event) {
		console.log('TreeNode handleToggle:', node.name, node.id, 'current expanded:', expanded);
		event.stopPropagation();
		dispatch('toggle', { nodeId: node.id });
	}
</script>

<div class="tree-node" style="--level: {level}">
	<div class="node-row">
		{#if hasChildren}
			{#if !isRoot}
				<button
					class="expand-icon"
					class:expanded
					on:click={handleToggle}
					type="button"
					aria-label={expanded ? 'Collapse' : 'Expand'}
				>
					▸
				</button>
			{:else}
				<!-- Root node: always expanded, no toggle icon -->
				<span class="node-spacer" />
			{/if}
		{:else}
			<span class="node-spacer" />
		{/if}
		<button
			class="node-button"
			class:active={isActive}
			class:has-children={hasChildren}
			on:click={handleClick}
			type="button"
		>
			<span class="node-name">{node.name}</span>
			{#if node.comic_count !== undefined}
				<span class="node-count">{node.comic_count}</span>
			{/if}
		</button>
	</div>

	{#if hasChildren && expanded}
		<div class="node-children">
			{#each node.children as child}
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

<style>
	.tree-node {
		width: 100%;
	}

	.node-row {
		display: flex;
		align-items: center;
		width: 100%;
		padding-left: calc(0.75rem + var(--level) * 1.25rem);
		border-left: 2px solid transparent;
	}

	.node-row:has(.node-button.active) {
		border-left-color: var(--color-accent);
	}

	.node-button {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		background: transparent;
		border: none;
		color: var(--color-text);
		font-size: 0.875rem;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s;
	}

	.node-button:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.node-button.active {
		background: rgba(255, 103, 64, 0.1);
		color: var(--color-accent);
	}

	.expand-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1rem;
		height: 1rem;
		padding: 0;
		margin: 0;
		background: transparent;
		border: none;
		color: inherit;
		font-size: 0.875rem;
		line-height: 1;
		text-align: center;
		transition: transform 0.2s;
		flex-shrink: 0;
		cursor: pointer;
		user-select: none;
	}

	.expand-icon:hover {
		color: var(--color-accent);
	}

	.expand-icon.expanded {
		transform: rotate(90deg);
	}

	.node-spacer {
		width: 1rem;
		flex-shrink: 0;
	}

	.node-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.node-count {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		flex-shrink: 0;
		padding: 0.125rem 0.5rem;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 10px;
	}

	.node-children {
		width: 100%;
	}
</style>
