<script>
	import Button from '$lib/components/common/Button.svelte';
	import { createEventDispatcher } from 'svelte';

	export let currentPage = 1;
	export let totalPages = 1;
	export let isFullscreen = false;
	export let showSettings = false;

	const dispatch = createEventDispatcher();

	$: canGoPrev = currentPage > 1;
	$: canGoNext = currentPage < totalPages;
	$: progress = totalPages > 0 ? (currentPage / totalPages) * 100 : 0;

	function handlePrevious() {
		if (canGoPrev) {
			dispatch('previous');
		}
	}

	function handleNext() {
		if (canGoNext) {
			dispatch('next');
		}
	}

	function handlePageChange(event) {
		const page = parseInt(event.target.value);
		if (page >= 1 && page <= totalPages) {
			dispatch('pageChange', page);
		}
	}

	function handleSliderChange(event) {
		const page = parseInt(event.target.value);
		dispatch('pageChange', page);
	}

	function toggleFullscreen() {
		dispatch('toggleFullscreen');
	}

	function toggleSettings() {
		dispatch('toggleSettings');
	}

	function handleExit() {
		dispatch('exit');
	}
</script>

<div class="reader-controls">
	<!-- Top Bar -->
	<div class="top-bar">
		<div class="left">
			<Button variant="ghost" size="sm" on:click={handleExit}>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="20"
					height="20"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M19 12H5M12 19l-7-7 7-7" />
				</svg>
				<span class="ml-2">Exit</span>
			</Button>
		</div>

		<div class="center">
			<span class="page-info">
				Page <input
					type="number"
					min="1"
					max={totalPages}
					value={currentPage}
					on:change={handlePageChange}
					class="page-input"
				/> of {totalPages}
			</span>
		</div>

		<div class="right">
			<Button
				variant="ghost"
				size="sm"
				on:click={toggleSettings}
				class={showSettings ? 'active' : ''}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="20"
					height="20"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<circle cx="12" cy="12" r="3" />
					<path
						d="M12 1v6m0 6v6m5.196-14.196l-4.242 4.242m0 5.908l-4.242 4.242M23 12h-6m-6 0H1m20.196 5.196l-4.242-4.242m-5.908 0l-4.242 4.242"
					/>
				</svg>
				<span class="ml-2">Settings</span>
			</Button>

			<Button variant="ghost" size="sm" on:click={toggleFullscreen}>
				{#if isFullscreen}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
					</svg>
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
					</svg>
				{/if}
			</Button>
		</div>
	</div>

	<!-- Bottom Bar -->
	<div class="bottom-bar">
		<Button variant="ghost" size="sm" on:click={handlePrevious} disabled={!canGoPrev}>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="20"
				height="20"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<path d="M15 18l-6-6 6-6" />
			</svg>
			<span class="ml-2">Previous</span>
		</Button>

		<div class="slider-container">
			<input
				type="range"
				min="1"
				max={totalPages}
				value={currentPage}
				on:input={handleSliderChange}
				class="page-slider"
			/>
			<div class="progress-bar" style="width: {progress}%" />
		</div>

		<Button variant="ghost" size="sm" on:click={handleNext} disabled={!canGoNext}>
			<span class="mr-2">Next</span>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="20"
				height="20"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<path d="M9 18l6-6-6-6" />
			</svg>
		</Button>
	</div>
</div>

<style>
	.reader-controls {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		pointer-events: none;
		z-index: 10;
	}

	.top-bar,
	.bottom-bar {
		position: absolute;
		left: 0;
		right: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.5rem;
		background: linear-gradient(to bottom, rgba(0, 0, 0, 0.8), transparent);
		pointer-events: all;
		transition: opacity 0.3s ease;
	}

	.top-bar {
		top: 0;
	}

	.bottom-bar {
		bottom: 0;
		background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
		gap: 1rem;
	}

	.top-bar .left,
	.top-bar .center,
	.top-bar .right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.top-bar .center {
		flex: 1;
		justify-content: center;
	}

	.page-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: white;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.page-input {
		width: 4rem;
		padding: 0.25rem 0.5rem;
		background: rgba(255, 255, 255, 0.1);
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 4px;
		color: white;
		text-align: center;
		font-size: 0.875rem;
	}

	.page-input:focus {
		outline: none;
		border-color: #ff6740;
		background: rgba(255, 255, 255, 0.15);
	}

	.slider-container {
		position: relative;
		flex: 1;
		height: 32px;
		display: flex;
		align-items: center;
	}

	.page-slider {
		width: 100%;
		height: 8px;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 4px;
		outline: none;
		cursor: pointer;
		-webkit-appearance: none;
		appearance: none;
		position: relative;
		z-index: 2;
	}

	.page-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 20px;
		height: 20px;
		background: #ff6740;
		border-radius: 50%;
		cursor: pointer;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	.page-slider::-moz-range-thumb {
		width: 20px;
		height: 20px;
		background: #ff6740;
		border-radius: 50%;
		cursor: pointer;
		border: none;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}

	.progress-bar {
		position: absolute;
		left: 0;
		top: 50%;
		transform: translateY(-50%);
		height: 8px;
		background: #ff6740;
		border-radius: 4px;
		pointer-events: none;
		z-index: 1;
		transition: width 0.2s ease;
	}

	:global(.reader-controls Button.active) {
		background: rgba(255, 103, 64, 0.2);
	}
</style>
