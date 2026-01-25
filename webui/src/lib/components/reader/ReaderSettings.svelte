<script>
	import { readerSettings } from '$lib/stores/reader';
	import { createEventDispatcher } from 'svelte';

	export let show = false;
	export let libraryId = null;

	const dispatch = createEventDispatcher();

	function updateSetting(key, value) {
		readerSettings.update((settings) => ({
			...settings,
			[key]: value
		}));
	}

	function handleClose() {
		dispatch('close');
	}

	function handleReset() {
		readerSettings.reset();
	}
</script>

{#if show}
	<div class="settings-panel">
		<div class="panel-header">
			<div>
				<h3>Reader Settings</h3>
				{#if libraryId}
					<p class="library-indicator">Library-specific defaults active</p>
				{/if}
			</div>
		<button class="close-btn" on:click={handleClose} aria-label="Close settings">
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
					<line x1="18" y1="6" x2="6" y2="18" />
					<line x1="6" y1="6" x2="18" y2="18" />
				</svg>
			</button>
		</div>

		<div class="panel-content">
			<!-- Fit Mode -->
			<div class="setting-group">
				<span class="setting-label">Fit Mode</span>
				<div class="radio-group" role="radiogroup" aria-label="Fit Mode">
					<label class="radio-label">
						<input
							type="radio"
							name="fitMode"
							value="fit-width"
							checked={$readerSettings.fitMode === 'fit-width'}
							on:change={() => updateSetting('fitMode', 'fit-width')}
						/>
						<span>Fit Width</span>
					</label>
					<label class="radio-label">
						<input
							type="radio"
							name="fitMode"
							value="fit-height"
							checked={$readerSettings.fitMode === 'fit-height'}
							on:change={() => updateSetting('fitMode', 'fit-height')}
						/>
						<span>Fit Height</span>
					</label>
					<label class="radio-label">
						<input
							type="radio"
							name="fitMode"
							value="original"
							checked={$readerSettings.fitMode === 'original'}
							on:change={() => updateSetting('fitMode', 'original')}
						/>
						<span>Original Size</span>
					</label>
				</div>
			</div>

			<!-- Reading Mode -->
			<div class="setting-group">
				<span class="setting-label">Reading Mode</span>
				<div class="radio-group" role="radiogroup" aria-label="Reading Mode">
					<label class="radio-label">
						<input
							type="radio"
							name="readingMode"
							value="single"
							checked={$readerSettings.readingMode === 'single'}
							on:change={() => updateSetting('readingMode', 'single')}
						/>
						<span>Single Page</span>
					</label>
					<label class="radio-label">
						<input
							type="radio"
							name="readingMode"
							value="double"
							checked={$readerSettings.readingMode === 'double'}
							on:change={() => updateSetting('readingMode', 'double')}
						/>
						<span>Double Page</span>
					</label>
					<label class="radio-label">
						<input
							type="radio"
							name="readingMode"
							value="continuous"
							checked={$readerSettings.readingMode === 'continuous'}
							on:change={() => updateSetting('readingMode', 'continuous')}
						/>
						<span>Continuous Scroll</span>
					</label>
				</div>
			</div>

			<!-- Reading Direction -->
			<div class="setting-group">
				<span class="setting-label">Reading Direction</span>
				<div class="radio-group" role="radiogroup" aria-label="Reading Direction">
					<label class="radio-label">
						<input
							type="radio"
							name="readingDirection"
							value="ltr"
							checked={$readerSettings.readingDirection === 'ltr'}
							on:change={() => updateSetting('readingDirection', 'ltr')}
						/>
						<span>Left to Right</span>
					</label>
					<label class="radio-label">
						<input
							type="radio"
							name="readingDirection"
							value="rtl"
							checked={$readerSettings.readingDirection === 'rtl'}
							on:change={() => updateSetting('readingDirection', 'rtl')}
						/>
						<span>Right to Left (Manga)</span>
					</label>
				</div>
			</div>

			<!-- Preload Pages -->
			<div class="setting-group">
				<label class="setting-label" for="preload-pages-input">
					Preload Pages
					<span class="setting-value">{$readerSettings.preloadPages}</span>
				</label>
				<input
					id="preload-pages-input"
					type="range"
					min="0"
					max="5"
					step="1"
					value={$readerSettings.preloadPages}
					on:input={(e) => updateSetting('preloadPages', parseInt(e.target.value))}
					class="range-input"
				/>
				<div class="range-labels">
					<span>0</span>
					<span>5</span>
				</div>
			</div>

			<!-- Background Color -->
			<div class="setting-group">
				<span class="setting-label">Background Color</span>
				<div class="color-options" role="group" aria-label="Background Color">
					{#each ['#1a1a1a', '#000000', '#242424', '#333333', '#ffffff'] as color}
						<button
							class="color-swatch"
							class:active={$readerSettings.backgroundColor === color}
							style="background-color: {color}"
							on:click={() => updateSetting('backgroundColor', color)}
						>
							{#if $readerSettings.backgroundColor === color}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke={color === '#ffffff' ? '#000000' : '#ffffff'}
									stroke-width="3"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<polyline points="20 6 9 17 4 12" />
								</svg>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<!-- Auto-hide Controls -->
			<div class="setting-group">
				<label class="checkbox-label">
					<input
						type="checkbox"
						checked={$readerSettings.autoHideControls}
						on:change={(e) => updateSetting('autoHideControls', e.target.checked)}
					/>
					<span>Auto-hide Controls</span>
				</label>
			</div>

			<!-- Keyboard Shortcuts Help -->
			<div class="setting-group">
				<span class="setting-label">Keyboard Shortcuts</span>
				<div class="shortcuts-help">
					<div class="shortcut">
						<kbd>←</kbd><kbd>→</kbd>
						<span>Navigate pages</span>
					</div>
					<div class="shortcut">
						<kbd>Space</kbd>
						<span>Next page</span>
					</div>
					<div class="shortcut">
						<kbd>F</kbd>
						<span>Toggle fullscreen</span>
					</div>
					<div class="shortcut">
						<kbd>S</kbd>
						<span>Toggle settings</span>
					</div>
					<div class="shortcut">
						<kbd>Esc</kbd>
						<span>Exit reader</span>
					</div>
					<div class="shortcut">
						<kbd>1-9</kbd>
						<span>Jump to 10%-90%</span>
					</div>
				</div>
			</div>
		</div>

		<div class="panel-footer">
			<button class="reset-btn" on:click={handleReset}>Reset to Defaults</button>
		</div>
	</div>
{/if}

<style>
	.settings-panel {
		position: fixed;
		right: 0;
		top: 0;
		bottom: 0;
		width: 100%;
		max-width: 380px;
		background: var(--color-secondary-bg);
		box-shadow: -4px 0 16px rgba(0, 0, 0, 0.4);
		display: flex;
		flex-direction: column;
		z-index: 50;
		animation: slideIn 0.3s ease;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.5rem;
		border-bottom: 1px solid var(--color-border);
	}

	.panel-header h3 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.library-indicator {
		margin: 0.25rem 0 0 0;
		font-size: 0.75rem;
		color: var(--color-accent);
		font-weight: 500;
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		transition: all 0.2s;
	}

	.close-btn:hover {
		background: var(--color-border);
		color: var(--color-text);
	}

	.panel-content {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
	}

	.setting-group {
		margin-bottom: 2rem;
	}

	.setting-label {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 0.75rem;
	}

	.setting-value {
		color: var(--color-accent);
		font-weight: 700;
	}

	.radio-group {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.radio-label {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 4px;
		transition: all 0.2s;
	}

	.radio-label:hover {
		background: var(--color-tertiary-bg);
		color: var(--color-text);
	}

	.radio-label input[type='radio'] {
		width: 18px;
		height: 18px;
		accent-color: var(--color-accent);
		cursor: pointer;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 4px;
		transition: all 0.2s;
	}

	.checkbox-label:hover {
		background: var(--color-tertiary-bg);
		color: var(--color-text);
	}

	.checkbox-label input[type='checkbox'] {
		width: 18px;
		height: 18px;
		accent-color: var(--color-accent);
		cursor: pointer;
	}

	.range-input {
		width: 100%;
		height: 6px;
		background: var(--color-border);
		border-radius: 3px;
		outline: none;
		cursor: pointer;
		-webkit-appearance: none;
		appearance: none;
	}

	.range-input::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 18px;
		height: 18px;
		background: var(--color-accent);
		border-radius: 50%;
		cursor: pointer;
	}

	.range-input::-moz-range-thumb {
		width: 18px;
		height: 18px;
		background: var(--color-accent);
		border-radius: 50%;
		cursor: pointer;
		border: none;
	}

	.range-labels {
		display: flex;
		justify-content: space-between;
		margin-top: 0.25rem;
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.color-options {
		display: flex;
		gap: 0.75rem;
	}

	.color-swatch {
		width: 48px;
		height: 48px;
		border-radius: 8px;
		border: 2px solid transparent;
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.color-swatch:hover {
		border-color: var(--color-accent);
		transform: scale(1.1);
	}

	.color-swatch.active {
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px var(--color-overlay-light);
	}

	.shortcuts-help {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 0.875rem;
	}

	.shortcut {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: var(--color-text-secondary);
	}

	kbd {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border-strong);
		border-radius: 4px;
		font-family: monospace;
		font-size: 0.75rem;
		color: var(--color-text);
		min-width: 2rem;
		text-align: center;
	}

	.panel-footer {
		padding: 1.5rem;
		border-top: 1px solid var(--color-border);
	}

	.reset-btn {
		width: 100%;
		padding: 0.75rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		color: var(--color-text);
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}

	.reset-btn:hover {
		background: var(--color-border);
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	@media (max-width: 640px) {
		.settings-panel {
			max-width: 100%;
		}
	}
</style>
