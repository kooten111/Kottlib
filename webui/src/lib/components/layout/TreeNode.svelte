<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let node;
	export let level = 0;
	export let isExpanded;
	export let activeNodeId;

	$: hasChildren = node.children && node.children.length > 0;
	$: expanded = isExpanded(node.id);
	$: isActive = activeNodeId === node.id;

	function handleClick(event) {
		dispatch('select', { node, event });
	}

	function handleToggle(event) {
		event.stopPropagation();
		dispatch('toggle', { nodeId: node.id });
	}
</script>

<div class="tree-node" style="--level: {level}">
	<button
		class="node-button"
		class:active={isActive}
		class:has-children={hasChildren}
		on:click={handleClick}
		type="button"
	>
		{#if hasChildren}
			<span class="expand-icon" class:expanded on:click={handleToggle} role="button" tabindex="0">
				▸
			</span>
		{:else}
			<span class="node-spacer" />
		{/if}
		<span class="node-name">{node.name}</span>
		{#if node.comic_count !== undefined}
			<span class="node-count">{node.comic_count}</span>
		{/if}
	</button>

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

	.node-button {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		padding-left: calc(0.75rem + var(--level) * 1.25rem);
		background: transparent;
		border: none;
		color: var(--color-text);
		font-size: 0.875rem;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s;
		border-left: 2px solid transparent;
	}

	.node-button:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.node-button.active {
		background: rgba(255, 103, 64, 0.1);
		border-left-color: var(--color-accent);
		color: var(--color-accent);
	}

	.expand-icon {
		display: inline-block;
		width: 1rem;
		height: 1rem;
		line-height: 1rem;
		text-align: center;
		transition: transform 0.2s;
		flex-shrink: 0;
		cursor: pointer;
		user-select: none;
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
