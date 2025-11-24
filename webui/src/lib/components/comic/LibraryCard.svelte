<script>
	export let library;

	$: comicCount = library.comicCount || 0;
</script>

<a href="/" class="library-card">
	<div class="library-icon">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="48"
			height="48"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
		</svg>
	</div>

	<div class="library-info">
		<h3 class="library-name">{library.name}</h3>
		<p class="library-path">{library.path}</p>
		<p class="library-stats">{comicCount.toLocaleString()} comics</p>
	</div>

	<div class="library-arrow">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
		>
			<path d="M9 18l6-6-6-6" />
		</svg>
	</div>
</a>

<style>
	.library-card {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		padding: 1.5rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
		transition: all 0.2s ease;
		text-decoration: none;
		color: inherit;
		border: 1px solid transparent;
	}

	.library-card:hover {
		background: #2a2a2a;
		border-color: var(--color-accent);
		transform: translateX(4px);
	}

	.library-icon {
		flex-shrink: 0;
		width: 64px;
		height: 64px;
		background: var(--color-accent);
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
	}

	.library-info {
		flex: 1;
		min-width: 0;
	}

	.library-name {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.25rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.library-path {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0 0 0.5rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: monospace;
	}

	.library-stats {
		font-size: 0.875rem;
		color: var(--color-accent);
		margin: 0;
		font-weight: 600;
	}

	.library-arrow {
		flex-shrink: 0;
		color: var(--color-text-secondary);
		transition: transform 0.2s ease;
	}

	.library-card:hover .library-arrow {
		transform: translateX(4px);
		color: var(--color-accent);
	}

	@media (max-width: 640px) {
		.library-card {
			padding: 1rem;
			gap: 1rem;
		}

		.library-icon {
			width: 48px;
			height: 48px;
		}

		.library-icon svg {
			width: 32px;
			height: 32px;
		}
	}
</style>
