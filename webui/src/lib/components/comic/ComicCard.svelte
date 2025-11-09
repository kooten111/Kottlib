<script>
	import { getCoverUrl } from '$lib/api/comics';

	export let comic;
	export let libraryId;
	export let variant = 'grid'; // 'grid' or 'list'
	export let showProgress = true;

	$: hash = comic.hash || comic.coverHash || comic.first_comic_hash;
	$: coverUrl = hash ? getCoverUrl(libraryId, hash) : null;
	$: progress = comic.current_page && comic.num_pages ? (comic.current_page / comic.num_pages) * 100 : 0;
	$: hasProgress = comic.current_page > 0;
	$: title = comic.title || comic.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, '') || 'Untitled';
</script>

<a href="/comic/{libraryId}/{comic.id}" class="comic-card {variant}">
	<div class="cover-container">
		{#if coverUrl}
			<img src={coverUrl} alt={comic.title} class="cover-image" loading="lazy" />
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
					<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
				</svg>
			</div>
		{/if}

		{#if showProgress && hasProgress}
			<div class="progress-overlay">
				<div class="progress-bar" style="width: {progress}%" />
			</div>
		{/if}
	</div>

	<div class="comic-info">
		<h3 class="comic-title">{title}</h3>
		{#if showProgress && hasProgress}
			<p class="comic-progress">
				Page {comic.current_page} of {comic.num_pages}
			</p>
		{/if}
	</div>
</a>

<style>
	.comic-card {
		display: flex;
		flex-direction: column;
		background: var(--color-secondary-bg);
		border-radius: 8px;
		overflow: hidden;
		transition: all 0.2s ease;
		text-decoration: none;
		color: inherit;
	}

	.comic-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
	}

	.comic-card.grid {
		flex-direction: column;
	}

	.comic-card.list {
		flex-direction: row;
	}

	.cover-container {
		position: relative;
		background: #1a1a1a;
		overflow: hidden;
	}

	.comic-card.grid .cover-container {
		aspect-ratio: 2/3;
		width: 100%;
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

	.comic-info {
		padding: 1rem;
		flex: 1;
	}

	.comic-card.list .comic-info {
		display: flex;
		flex-direction: column;
		justify-content: center;
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
</style>
