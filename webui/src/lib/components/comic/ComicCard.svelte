<script>
	import { getCoverUrl } from "$lib/api/comics";

	export let comic;
	export let libraryId;
	export let variant = "grid"; // 'grid' or 'list'
	export let showProgress = true;
	export let isFolder = false; // New prop to indicate if this is a folder/series
	export let itemCount = 0; // Number of items in folder
	export let href = null; // Optional custom href for the card

	$: hash =
		comic.hash ||
		comic.coverHash ||
		comic.cover_hash ||
		comic.first_comic_hash;
	$: coverUrl = hash ? getCoverUrl(libraryId, hash) : null;
	$: progress =
		comic.current_page && comic.num_pages
			? (comic.current_page / comic.num_pages) * 100
			: 0;
	$: hasProgress = comic.current_page > 0;
	$: title =
		comic.name ||
		comic.series_name ||
		comic.title ||
		comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, "") ||
		"Untitled";
	$: actualItemCount = itemCount || comic.itemCount || comic.item_count || 0;
	// Always link directly to the reader
	$: cardHref = href || `/comic/${libraryId}/${comic.id}/read`;
</script>

<a href={cardHref} class="comic-card {variant}" class:folder-card={isFolder}>
	<div class="cover-container" class:folder-cover={isFolder}>
		{#if coverUrl}
			<img
				src={coverUrl}
				alt={comic.title}
				class="cover-image"
				loading="lazy"
				decoding="async"
			/>
		{:else}
			<div class="cover-placeholder">
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
					<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
					<path
						d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
					/>
				</svg>
			</div>
		{/if}

		{#if isFolder && variant === "grid"}
			<div class="folder-info-bar">
				<div class="series-name">{title}</div>
				<div class="item-count">
					{actualItemCount}
					{actualItemCount === 1 ? "comic" : "comics"}
				</div>
			</div>
		{:else if showProgress && hasProgress && variant === "grid"}
			<div class="progress-overlay">
				<div class="progress-bar" style="width: {progress}%"></div>
			</div>
		{/if}
	</div>

	{#if variant === "list" && isFolder}
		<div class="list-info">
			<div class="list-header">
				<h3 class="list-title">{title}</h3>
				<div class="list-meta">
					<span class="meta-badge">
						{actualItemCount}
						{actualItemCount === 1 ? "volume" : "volumes"}
					</span>
					{#if comic.writer}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path
									d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"
								></path>
								<circle cx="12" cy="7" r="4"></circle>
							</svg>
							{comic.writer}
						</span>
					{/if}
					{#if comic.artist && comic.artist !== comic.writer}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path
									d="m15 5 4 4L7 21l-4.3-4.3a1 1 0 0 1 0-1.4l9.7-9.7a1 1 0 0 1 1.4 0Z"
								></path>
								<path d="m9 11 4 4"></path>
							</svg>
							{comic.artist}
						</span>
					{/if}
					{#if comic.year}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<rect
									x="3"
									y="4"
									width="18"
									height="18"
									rx="2"
									ry="2"
								></rect>
								<line x1="16" y1="2" x2="16" y2="6"></line>
								<line x1="8" y1="2" x2="8" y2="6"></line>
								<line x1="3" y1="10" x2="21" y2="10"></line>
							</svg>
							{comic.year}
						</span>
					{/if}
					{#if comic.publisher}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="m7.5 4.27 9 5.15"></path>
								<path
									d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"
								></path>
								<path d="m3.3 7 8.7 5 8.7-5"></path>
								<path d="M12 22V12"></path>
							</svg>
							{comic.publisher}
						</span>
					{/if}
					{#if comic.genre}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="m3 7 5 5-5 5V7"></path>
								<path d="m21 7-5 5 5 5V7"></path>
								<path d="M12 20v2"></path>
								<path d="M12 14v2"></path>
								<path d="M12 8v2"></path>
								<path d="M12 2v2"></path>
							</svg>
							{comic.genre}
						</span>
					{/if}
				</div>
			</div>
			{#if comic.synopsis}
				<p class="list-synopsis">{comic.synopsis}</p>
			{/if}
			<div class="list-actions">
				<button class="action-btn primary">Continue Reading</button>
			</div>
		</div>
	{:else if !isFolder}
		<div class="comic-info">
			<h3 class="comic-title">{title}</h3>
			{#if variant === "list"}
				<div class="list-meta">
					{#if comic.volume}
						<span class="meta-badge">
							Vol. {comic.volume}
						</span>
					{/if}
					{#if comic.series}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
								<path
									d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
								/>
							</svg>
							{comic.series}
						</span>
					{/if}
					{#if comic.writer}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path
									d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"
								></path>
								<circle cx="12" cy="7" r="4"></circle>
							</svg>
							{comic.writer}
						</span>
					{/if}
					{#if comic.year}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<rect
									x="3"
									y="4"
									width="18"
									height="18"
									rx="2"
									ry="2"
								></rect>
								<line x1="16" y1="2" x2="16" y2="6"></line>
								<line x1="8" y1="2" x2="8" y2="6"></line>
								<line x1="3" y1="10" x2="21" y2="10"></line>
							</svg>
							{comic.year}
						</span>
					{/if}
					{#if comic.num_pages}
						<span class="meta-item">
							<svg
								class="meta-icon"
								xmlns="http://www.w3.org/2000/svg"
								width="14"
								height="14"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path
									d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
								></path>
								<polyline points="14 2 14 8 20 8"></polyline>
							</svg>
							{comic.num_pages} pages
						</span>
					{/if}
				</div>
			{/if}

			{#if variant === "grid"}
				<div class="grid-badges">
					{#if comic.is_standalone}
						<span class="meta-badge pill">Standalone</span>
					{/if}
					{#if comic.volume}
						<span class="meta-badge pill">Vol. {comic.volume}</span>
					{/if}
					{#if comic.series && !comic.volume}
						<span class="meta-badge pill">{comic.series}</span>
					{/if}
				</div>
			{/if}

			{#if showProgress && hasProgress}
				<p class="comic-progress">
					Page {comic.current_page} of {comic.num_pages}
				</p>
			{/if}
		</div>
	{/if}
</a>

<style>
	.comic-card {
		display: flex;
		flex-direction: column;
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		overflow: hidden;
		transition: all 0.2s ease;
		text-decoration: none;
		color: inherit;
	}

	.comic-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
		border-color: var(--color-border-strong);
	}

	.comic-card.grid {
		flex-direction: column;
	}

	.comic-card.list {
		flex-direction: row;
		padding: calc(1rem + (0.25rem * var(--cover-size-multiplier, 1)));
		gap: calc(1.25rem + (0.25rem * var(--cover-size-multiplier, 1)));
		min-height: 200px;
	}

	.cover-container {
		position: relative;
		background: var(--color-bg);
		overflow: hidden;
	}

	/* Folder stacked effect */
	.folder-cover::before,
	.folder-cover::after {
		content: "";
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		z-index: -1;
	}

	.folder-cover::before {
		transform: translate(-4px, -4px);
		opacity: 0.6;
	}

	.folder-cover::after {
		transform: translate(-8px, -8px);
		opacity: 0.3;
	}

	.folder-card:hover .folder-cover::before {
		transform: translate(-6px, -6px);
		transition: transform 0.2s ease;
	}

	.folder-card:hover .folder-cover::after {
		transform: translate(-10px, -10px);
		transition: transform 0.2s ease;
	}

	.comic-card.grid .cover-container {
		aspect-ratio: 1 / 1.414; /* ISO 216 paper ratio (1:√2), standard for books */
		width: 100%;
		background: var(
			--color-tertiary-bg
		); /* Show background before image loads */
	}

	.comic-card.list .cover-container {
		width: 100px;
		height: 150px;
		flex-shrink: 0;
	}

	.cover-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
		object-position: top;
		display: block;
	}

	.cover-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--color-text-secondary);
	}

	.progress-overlay {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 4px;
		background: rgba(0, 0, 0, 0.5);
	}

	.progress-bar {
		height: 100%;
		background: var(--color-accent);
		transition: width 0.3s ease;
	}

	/* Folder info bar */
	.folder-info-bar {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		background: var(--color-overlay);
		backdrop-filter: blur(8px);
		padding: 0.5rem 0.75rem;
		z-index: 2;
	}

	.folder-info-bar .series-name {
		font-weight: 600;
		font-size: 0.875rem;
		color: var(--color-text);
		margin-bottom: 0.125rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.folder-info-bar .item-count {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.comic-info {
		padding: 1rem;
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.comic-card.list .comic-info {
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 0;
	}

	.comic-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.25rem 0;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.comic-card.list .comic-title {
		-webkit-line-clamp: 1;
	}

	.comic-progress {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin: 0;
	}

	/* List view specific styles */
	.list-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		padding: 0.5rem 0;
	}

	.list-header {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.list-title {
		font-size: 1.25rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0 0 0.75rem 0;
		line-height: 1.3;
	}

	.list-meta {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.meta-badge {
		padding: 0.375rem 0.875rem;
		background: color-mix(in srgb, var(--color-accent) 15%, transparent);
		color: var(--color-accent);
		border-radius: 16px;
		font-size: 0.813rem;
		font-weight: 600;
		letter-spacing: 0.01em;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		line-height: 1.4;
		font-weight: 500;
	}

	.meta-icon {
		flex-shrink: 0;
		opacity: 0.6;
		width: 16px;
		height: 16px;
	}

	.list-synopsis {
		margin: 0.875rem 0 0 0;
		color: var(--color-text-secondary);
		font-size: 0.938rem;
		line-height: 1.6;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		text-overflow: ellipsis;
		font-weight: 400;
	}

	.list-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: auto;
		padding-top: 1rem;
	}

	.action-btn {
		padding: 0.625rem 1.25rem;
		border: none;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
		white-space: nowrap;
	}

	.action-btn.primary {
		background: var(--color-accent);
		color: white;
		box-shadow: 0 2px 4px
			color-mix(in srgb, var(--color-accent) 20%, transparent);
	}

	.action-btn.primary:hover {
		background: var(--color-accent-hover);
		transform: translateY(-1px);
		box-shadow: 0 4px 8px
			color-mix(in srgb, var(--color-accent) 30%, transparent);
	}

	/* List view cover size - scales with multiplier but with limits */
	.comic-card.list .cover-container {
		width: calc(120px + (20px * var(--cover-size-multiplier, 1)));
		height: calc(180px + (30px * var(--cover-size-multiplier, 1)));
		flex-shrink: 0;
		border-radius: 6px;
		overflow: hidden;
	}

	.grid-badges {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.meta-badge.pill {
		padding: 0.15rem 0.5rem;
		font-size: 0.7rem;
		border-radius: 4px;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		color: var(--color-text-secondary);
	}
</style>
