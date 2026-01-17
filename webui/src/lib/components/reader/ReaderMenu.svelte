<script>
	import { createEventDispatcher } from 'svelte';
	import { readerSettings } from '$lib/stores/reader';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let currentPage = 1;
	export let totalPages = 1;
	export let chapters = []; // Array of chapter metadata

	let pageInput = currentPage;

	$: if (show) {
		pageInput = currentPage;
	}

	function handlePageJump() {
		const targetPage = parseInt(pageInput);
		if (targetPage >= 1 && targetPage <= totalPages) {
			dispatch('pageChange', targetPage);
			show = false;
		}
	}

	function handleSliderChange(e) {
		const targetPage = parseInt(e.target.value);
		pageInput = targetPage;
	}

	function handleChapterClick(startPage) {
		dispatch('pageChange', startPage);
		show = false;
	}

	function handleClose() {
		dispatch('close');
	}

	function handleOverlayClick(e) {
		if (e.target === e.currentTarget) {
			handleClose();
		}
	}

	function cycleFitMode() {
		const modes = ['fit-width', 'fit-height', 'original'];
		const currentIndex = modes.indexOf($readerSettings.fitMode);
		const nextIndex = (currentIndex + 1) % modes.length;
		readerSettings.update(s => ({ ...s, fitMode: modes[nextIndex] }));
	}

	function toggleReadingDirection() {
		readerSettings.update(s => ({
			...s,
			readingDirection: s.readingDirection === 'ltr' ? 'rtl' : 'ltr'
		}));
	}

	function getFitModeLabel() {
		switch ($readerSettings.fitMode) {
			case 'fit-width': return 'Fit Width';
			case 'fit-height': return 'Fit Height';
			case 'original': return 'Original Size';
			default: return 'Fit Width';
		}
	}
</script>

{#if show}
<div class="reader-menu-overlay" on:click={handleOverlayClick} role="presentation">
	<div class="reader-menu" on:click|stopPropagation on:keydown={(e) => e.key === 'Escape' && handleClose()} role="dialog" tabindex="-1">
		<!-- Page Navigator -->
		<div class="menu-section">
			<h3 class="section-title">Jump to Page</h3>
			<div class="page-controls">
				<input
					type="number"
					min="1"
					max={totalPages}
					bind:value={pageInput}
					on:change={handlePageJump}
					class="page-input"
				/>
				<span class="page-total">/ {totalPages}</span>
			</div>
			<input
				type="range"
				min="1"
				max={totalPages}
				value={pageInput}
				on:input={handleSliderChange}
				on:change={handlePageJump}
				class="page-slider"
			/>
		</div>

		<!-- Chapter Navigator -->
		{#if chapters && chapters.length > 0}
		<div class="menu-section">
			<h3 class="section-title">Chapters</h3>
			<ul class="chapter-list">
				{#each chapters as chapter}
				<li>
					<button
						class="chapter-item"
						on:click={() => handleChapterClick(chapter.startPage)}
						type="button"
					>
						<span class="chapter-name">{chapter.name}</span>
						<span class="chapter-page">Page {chapter.startPage}</span>
					</button>
				</li>
				{/each}
			</ul>
		</div>
		{/if}

		<!-- Quick Settings -->
		<div class="menu-section">
			<h3 class="section-title">Quick Settings</h3>
			<div class="settings-buttons">
				<button class="setting-button" on:click={cycleFitMode} type="button">
					<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
						<line x1="9" y1="3" x2="9" y2="21"/>
					</svg>
					<span>{getFitModeLabel()}</span>
				</button>
				<button class="setting-button" on:click={toggleReadingDirection} type="button">
					<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<polyline points="17 11 21 7 17 3"/>
						<path d="M21 7H9a4 4 0 0 0-4 4v0a4 4 0 0 0 4 4h12"/>
					</svg>
					<span>{$readerSettings.readingDirection === 'ltr' ? 'Left to Right' : 'Right to Left'}</span>
				</button>
			</div>
		</div>

		<!-- Close Button -->
		<button class="close-button" on:click={handleClose} type="button">
			Close
		</button>
	</div>
</div>
{/if}

<style>
	.reader-menu-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.8);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		backdrop-filter: blur(4px);
	}

	.reader-menu {
		background: #1a1a1a;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		padding: 2rem;
		width: 90%;
		max-width: 500px;
		max-height: 80vh;
		overflow-y: auto;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}

	.menu-section {
		margin-bottom: 2rem;
	}

	.menu-section:last-of-type {
		margin-bottom: 1.5rem;
	}

	.section-title {
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 1rem 0;
	}

	.page-controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.page-input {
		flex: 1;
		padding: 0.75rem;
		background: #242424;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: var(--color-text);
		font-size: 1rem;
		text-align: center;
	}

	.page-input:focus {
		outline: none;
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px rgba(255, 103, 64, 0.1);
	}

	.page-total {
		color: var(--color-text-secondary);
		font-size: 1rem;
	}

	.page-slider {
		width: 100%;
		height: 6px;
		background: #242424;
		border-radius: 3px;
		outline: none;
		appearance: none;
		-webkit-appearance: none;
	}

	.page-slider::-webkit-slider-thumb {
		appearance: none;
		-webkit-appearance: none;
		width: 18px;
		height: 18px;
		background: var(--color-accent);
		border-radius: 50%;
		cursor: pointer;
	}

	.page-slider::-moz-range-thumb {
		width: 18px;
		height: 18px;
		background: var(--color-accent);
		border-radius: 50%;
		cursor: pointer;
		border: none;
	}

	.chapter-list {
		list-style: none;
		padding: 0;
		margin: 0;
		max-height: 200px;
		overflow-y: auto;
	}

	.chapter-item {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: transparent;
		border: none;
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
		color: var(--color-text);
		cursor: pointer;
		transition: background 0.15s;
		text-align: left;
	}

	.chapter-item:hover {
		background: rgba(255, 103, 64, 0.1);
	}

	.chapter-name {
		font-size: 0.875rem;
		font-weight: 500;
	}

	.chapter-page {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.settings-buttons {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.setting-button {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem 1rem;
		background: #242424;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: var(--color-text);
		cursor: pointer;
		transition: all 0.15s;
		font-size: 0.875rem;
	}

	.setting-button:hover {
		background: #2a2a2a;
		border-color: var(--color-accent);
	}

	.close-button {
		width: 100%;
		padding: 0.875rem;
		background: var(--color-accent);
		border: none;
		border-radius: 6px;
		color: white;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: opacity 0.15s;
	}

	.close-button:hover {
		opacity: 0.9;
	}

	/* Scrollbar styling */
	.reader-menu::-webkit-scrollbar,
	.chapter-list::-webkit-scrollbar {
		width: 8px;
	}

	.reader-menu::-webkit-scrollbar-track,
	.chapter-list::-webkit-scrollbar-track {
		background: transparent;
	}

	.reader-menu::-webkit-scrollbar-thumb,
	.chapter-list::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.2);
		border-radius: 4px;
	}

	.reader-menu::-webkit-scrollbar-thumb:hover,
	.chapter-list::-webkit-scrollbar-thumb:hover {
		background: rgba(255, 255, 255, 0.3);
	}
</style>
