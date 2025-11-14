<script>
	import { Scan, RefreshCw, Trash2, Settings, AlertCircle } from 'lucide-svelte';
	import { scanLibrary, clearMetadata, getLibraryConfigs } from '$lib/api/scanners';

	export let libraryId;
	export let libraryName;

	let isScanning = false;
	let isClearing = false;
	let scanProgress = null;
	let error = null;
	let showOptions = false;
	let scanOptions = {
		overwrite: false,
		rescanExisting: false,
		confidenceThreshold: null
	};
	let clearOptions = {
		clearScannerInfo: true,
		clearTags: true,
		clearMetadata: false
	};
	let scannerConfig = null;

	// Load scanner configuration
	async function loadConfig() {
		try {
			const configs = await getLibraryConfigs();
			scannerConfig = configs.find(c => c.library_id === libraryId);
		} catch (err) {
			console.error('Failed to load scanner config:', err);
		}
	}

	loadConfig();

	async function handleScanLibrary() {
		if (!confirm(`Scan all comics in library "${libraryName}"?\n\nThis may take a while for large libraries.`)) {
			return;
		}

		try {
			isScanning = true;
			error = null;
			scanProgress = null;

			const result = await scanLibrary(
				libraryId,
				scanOptions.overwrite,
				scanOptions.rescanExisting,
				scanOptions.confidenceThreshold
			);

			scanProgress = result;

			// Show completion message
			alert(
				`Library scan complete!\n\n` +
				`Total: ${result.total_comics}\n` +
				`Scanned: ${result.scanned}\n` +
				`Failed: ${result.failed}\n` +
				`Skipped: ${result.skipped}`
			);

			// Optionally reload the page to show updated data
			if (result.scanned > 0) {
				window.location.reload();
			}
		} catch (err) {
			error = err.message;
		} finally {
			isScanning = false;
		}
	}

	async function handleClearLibrary() {
		if (!confirm(
			`Clear metadata from all comics in library "${libraryName}"?\n\n` +
			`This will:\n` +
			`${clearOptions.clearScannerInfo ? '✓ Clear scanner info\n' : ''}` +
			`${clearOptions.clearTags ? '✓ Clear tags\n' : ''}` +
			`${clearOptions.clearMetadata ? '✓ Clear all metadata\n' : ''}` +
			`\nThis action cannot be undone!`
		)) {
			return;
		}

		try {
			isClearing = true;
			error = null;

			const result = await clearMetadata({
				libraryId: libraryId,
				...clearOptions
			});

			alert(`Successfully cleared metadata from ${result.cleared_count} comic(s)`);

			// Reload the page
			window.location.reload();
		} catch (err) {
			error = err.message;
		} finally {
			isClearing = false;
		}
	}
</script>

<div class="library-scanner-panel">
	<div class="panel-header">
		<h3 class="panel-title">
			<Scan class="w-5 h-5" />
			Scanner Controls
		</h3>
		<button
			on:click={() => showOptions = !showOptions}
			class="btn-options"
			title="Toggle options"
		>
			<Settings class="w-4 h-4" />
		</button>
	</div>

	{#if scannerConfig && !scannerConfig.primary_scanner}
		<div class="warning-message">
			<AlertCircle class="w-4 h-4" />
			<span>No scanner configured for this library. Configure it in the <a href="/admin/scanners">Scanner Admin</a> page.</span>
		</div>
	{:else if scannerConfig}
		<div class="scanner-info">
			<span class="info-label">Scanner:</span>
			<span class="info-value">{scannerConfig.primary_scanner}</span>
		</div>
	{/if}

	{#if showOptions}
		<div class="options-panel">
			<h4 class="options-title">Scan Options</h4>
			<label class="option-checkbox">
				<input type="checkbox" bind:checked={scanOptions.overwrite} />
				<span>Overwrite existing metadata</span>
			</label>
			<label class="option-checkbox">
				<input type="checkbox" bind:checked={scanOptions.rescanExisting} />
				<span>Rescan already scanned comics</span>
			</label>
			<div class="option-input">
				<label for="threshold">Confidence threshold (optional):</label>
				<input
					id="threshold"
					type="number"
					min="0"
					max="1"
					step="0.1"
					bind:value={scanOptions.confidenceThreshold}
					placeholder={scannerConfig ? scannerConfig.confidence_threshold : '0.4'}
				/>
			</div>

			<h4 class="options-title mt-4">Clear Options</h4>
			<label class="option-checkbox">
				<input type="checkbox" bind:checked={clearOptions.clearScannerInfo} />
				<span>Clear scanner info</span>
			</label>
			<label class="option-checkbox">
				<input type="checkbox" bind:checked={clearOptions.clearTags} />
				<span>Clear tags</span>
			</label>
			<label class="option-checkbox">
				<input type="checkbox" bind:checked={clearOptions.clearMetadata} />
				<span>Clear all metadata (destructive)</span>
			</label>
		</div>
	{/if}

	<div class="panel-actions">
		<button
			on:click={handleScanLibrary}
			disabled={isScanning || !scannerConfig?.primary_scanner}
			class="btn-scan"
		>
			<span class:spinning={isScanning}>
				<RefreshCw class="w-4 h-4" />
			</span>
			{isScanning ? 'Scanning...' : 'Scan Library'}
		</button>
		<button
			on:click={handleClearLibrary}
			disabled={isClearing}
			class="btn-clear"
		>
			<Trash2 class="w-4 h-4" />
			{isClearing ? 'Clearing...' : 'Clear Metadata'}
		</button>
	</div>

	{#if error}
		<div class="error-message">
			{error}
		</div>
	{/if}

	{#if scanProgress}
		<div class="progress-message">
			<p>Scan complete!</p>
			<ul>
				<li>Total: {scanProgress.total_comics}</li>
				<li>Scanned: {scanProgress.scanned}</li>
				<li>Failed: {scanProgress.failed}</li>
				<li>Skipped: {scanProgress.skipped}</li>
			</ul>
		</div>
	{/if}
</div>

<style>
	.library-scanner-panel {
		background: rgba(255, 255, 255, 0.05);
		border-radius: 8px;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.panel-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1.125rem;
		font-weight: 600;
		color: #e5e7eb;
	}

	.btn-options {
		background: rgba(255, 255, 255, 0.1);
		border: none;
		border-radius: 6px;
		padding: 0.5rem;
		color: #9ca3af;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-options:hover {
		background: rgba(255, 255, 255, 0.15);
		color: #e5e7eb;
	}

	.scanner-info {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1rem;
		padding: 0.75rem;
		background: rgba(96, 165, 250, 0.1);
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.info-label {
		color: #9ca3af;
		font-weight: 500;
	}

	.info-value {
		color: #60a5fa;
		font-weight: 600;
	}

	.warning-message {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: rgba(251, 191, 36, 0.2);
		color: #fbbf24;
		border-radius: 6px;
		font-size: 0.875rem;
		margin-bottom: 1rem;
	}

	.warning-message a {
		color: #60a5fa;
		text-decoration: underline;
	}

	.options-panel {
		padding: 1rem;
		background: rgba(0, 0, 0, 0.2);
		border-radius: 6px;
		margin-bottom: 1rem;
	}

	.options-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: #e5e7eb;
		margin-bottom: 0.5rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.option-checkbox {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin: 0.5rem 0;
		color: #e5e7eb;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.option-checkbox input[type="checkbox"] {
		width: 1rem;
		height: 1rem;
		cursor: pointer;
	}

	.option-input {
		margin: 0.75rem 0;
	}

	.option-input label {
		display: block;
		color: #9ca3af;
		font-size: 0.875rem;
		margin-bottom: 0.25rem;
	}

	.option-input input[type="number"] {
		width: 100%;
		padding: 0.5rem;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: #e5e7eb;
		font-size: 0.875rem;
	}

	.panel-actions {
		display: flex;
		gap: 0.75rem;
	}

	.btn-scan,
	.btn-clear {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		font-size: 0.875rem;
		font-weight: 600;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-scan {
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
	}

	.btn-scan:hover:not(:disabled) {
		background: rgba(34, 197, 94, 0.3);
	}

	.btn-clear {
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
	}

	.btn-clear:hover:not(:disabled) {
		background: rgba(239, 68, 68, 0.3);
	}

	.btn-scan:disabled,
	.btn-clear:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinning {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	.error-message {
		margin-top: 1rem;
		padding: 0.75rem;
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.progress-message {
		margin-top: 1rem;
		padding: 0.75rem;
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.progress-message p {
		font-weight: 600;
		margin-bottom: 0.5rem;
	}

	.progress-message ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.progress-message li {
		margin: 0.25rem 0;
	}

	.mt-4 {
		margin-top: 1rem;
	}
</style>
