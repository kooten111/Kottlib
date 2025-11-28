<script>
	import { Scan, ExternalLink, Tag, Trash2, RefreshCw } from "lucide-svelte";
	import { scanComic, clearMetadata } from "$lib/api/scanners";

	export let comic;
	export let libraryId;

	let isScanning = false;
	let isClearing = false;
	let scanResult = null;
	let error = null;

	async function handleScan(overwrite = false) {
		try {
			isScanning = true;
			error = null;
			scanResult = null;

			const result = await scanComic(comic.id, overwrite);

			if (result.success) {
				scanResult = result;
				// Refresh the page to show updated metadata
				window.location.reload();
			} else {
				error = result.error || "Scan failed";
			}
		} catch (err) {
			error = err.message;
		} finally {
			isScanning = false;
		}
	}

	async function handleClear() {
		if (!confirm("Clear scanner metadata for this comic?")) {
			return;
		}

		try {
			isClearing = true;
			error = null;

			await clearMetadata({
				comicIds: [comic.id],
				clearScannerInfo: true,
				clearTags: true,
				clearMetadata: false,
			});

			// Refresh the page
			window.location.reload();
		} catch (err) {
			error = err.message;
		} finally {
			isClearing = false;
		}
	}
</script>

<div class="scanner-metadata">
	{#if comic.scanner_source}
		<div class="metadata-content">
			<div class="metadata-row">
				<span class="label">Source:</span>
				<span class="value">{comic.scanner_source}</span>
			</div>

			{#if comic.scanner_source_id}
				<div class="metadata-row">
					<span class="label">Source ID:</span>
					<a
						href="/?q={comic.scanner_source_id}"
						class="value value-link"
					>
						{comic.scanner_source_id}
					</a>
				</div>
			{/if}

			{#if comic.scanner_source_url}
				<div class="metadata-row">
					<span class="label">Source URL:</span>
					<a
						href={comic.scanner_source_url}
						target="_blank"
						rel="noopener noreferrer"
						class="url-link"
					>
						View on {comic.scanner_source}
						<ExternalLink class="w-3 h-3" />
					</a>
				</div>
			{/if}

			{#if comic.scan_confidence !== null && comic.scan_confidence !== undefined}
				<div class="metadata-row">
					<span class="label">Confidence:</span>
					<span
						class="value confidence"
						class:high={comic.scan_confidence >= 0.7}
					>
						{Math.round(comic.scan_confidence * 100)}%
					</span>
				</div>
			{/if}

			{#if comic.scanned_at}
				<div class="metadata-row">
					<span class="label">Scanned:</span>
					<span class="value">
						{new Date(comic.scanned_at * 1000).toLocaleString()}
					</span>
				</div>
			{/if}

			{#if comic.tags}
				{@const tagsByType = comic.tags
					.split("\n")
					.filter((t) => t.trim())
					.reduce((acc, tagString) => {
						const [tagType, tagName] = tagString.includes(":")
							? tagString.split(":", 2)
							: ["tag", tagString];
						if (!acc[tagType]) acc[tagType] = [];
						acc[tagType].push(tagName);
						return acc;
					}, {})}

				<!-- Parodies/Series -->
				{#if tagsByType.parody && tagsByType.parody.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Parodies:</span>
						<div class="tags-list">
							{#each tagsByType.parody as tagName}
								<span class="tag-badge tag-parody"
									>{tagName}</span
								>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Characters -->
				{#if tagsByType.character && tagsByType.character.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Characters:</span>
						<div class="tags-list">
							{#each tagsByType.character as tagName}
								<span class="tag-badge tag-character"
									>{tagName}</span
								>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Artists -->
				{#if tagsByType.artist && tagsByType.artist.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Artists:</span>
						<div class="tags-list">
							{#each tagsByType.artist as tagName}
								<span class="tag-badge tag-artist"
									>{tagName}</span
								>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Groups/Circles -->
				{#if tagsByType.group && tagsByType.group.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Groups:</span>
						<div class="tags-list">
							{#each tagsByType.group as tagName}
								<span class="tag-badge tag-group"
									>{tagName}</span
								>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Languages -->
				{#if tagsByType.language && tagsByType.language.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Languages:</span>
						<div class="tags-list">
							{#each tagsByType.language as tagName}
								<span class="tag-badge tag-language"
									>{tagName}</span
								>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Categories -->
				{#if tagsByType.category && tagsByType.category.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Categories:</span>
						<div class="tags-list">
							{#each tagsByType.category as tagName}
								<span class="tag-badge tag-category"
									>{tagName}</span
								>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Content Tags -->
				{#if tagsByType.tag && tagsByType.tag.length > 0}
					<div class="metadata-row tags-section">
						<span class="label">Tags:</span>
						<div class="tags-list">
							{#each tagsByType.tag as tagName}
								<span class="tag-badge tag-tag">{tagName}</span>
							{/each}
						</div>
					</div>
				{/if}
			{/if}

			<!-- Dynamic Metadata from Scanner -->
			{#if comic.metadata && comic.metadata.items}
				<div class="dynamic-metadata-section">
					{#each comic.metadata.items as item}
						{#if item.display === "row"}
							<div class="metadata-row">
								<span class="label">{item.label}:</span>
								<span class="value">{item.value}</span>
							</div>
						{:else if item.display === "tag"}
							<div class="metadata-row tags-section">
								<span class="label">{item.label}:</span>
								<div class="tags-list">
									<span
										class="tag-badge"
										style="
										background: {item.color === 'green'
											? 'rgba(34, 197, 94, 0.2)'
											: item.color === 'blue'
												? 'rgba(59, 130, 246, 0.2)'
												: item.color === 'red'
													? 'rgba(239, 68, 68, 0.2)'
													: item.color === 'yellow'
														? 'rgba(234, 179, 8, 0.2)'
														: item.color ===
															  'orange'
															? 'rgba(249, 115, 22, 0.2)'
															: 'rgba(156, 163, 175, 0.2)'};
										color: {item.color === 'green'
											? '#22c55e'
											: item.color === 'blue'
												? '#3b82f6'
												: item.color === 'red'
													? '#ef4444'
													: item.color === 'yellow'
														? '#eab308'
														: item.color ===
															  'orange'
															? '#f97316'
															: '#9ca3af'};
									"
									>
										{item.value}
									</span>
								</div>
							</div>
						{:else if item.display === "list"}
							<div class="metadata-row list-section">
								<span class="label">{item.label}:</span>
								<div class="value-list">
									{#each item.value as val}
										<div class="list-item">{val}</div>
									{/each}
								</div>
							</div>
						{:else if item.display === "links"}
							<div class="metadata-row links-section">
								<span class="label">{item.label}:</span>
								<div class="links-list">
									{#each Object.entries(item.value) as [name, url]}
										<a
											href={url}
											target="_blank"
											rel="noopener noreferrer"
											class="external-link-badge"
										>
											{name}
											<ExternalLink
												class="w-3 h-3 ml-1"
											/>
										</a>
									{/each}
								</div>
							</div>
						{/if}
					{/each}
				</div>
			{/if}
		</div>

		<div class="metadata-actions">
			<button
				on:click={() => handleScan(true)}
				disabled={isScanning}
				class="btn-rescan"
			>
				<RefreshCw class="w-4 h-4" />
				{isScanning ? "Rescanning..." : "Rescan"}
			</button>
			<button
				on:click={handleClear}
				disabled={isClearing}
				class="btn-clear"
			>
				<Trash2 class="w-4 h-4" />
				{isClearing ? "Clearing..." : "Clear"}
			</button>
		</div>
	{:else}
		<div class="no-metadata">
			<p class="text-gray-400 text-sm mb-2">
				No scanner metadata available
			</p>
			<button
				on:click={() => handleScan(false)}
				disabled={isScanning}
				class="btn-scan"
			>
				<Scan class="w-4 h-4" />
				{isScanning ? "Scanning..." : "Scan for Metadata"}
			</button>
		</div>
	{/if}

	{#if error}
		<div class="error-message">
			{error}
		</div>
	{/if}

	{#if scanResult && scanResult.success}
		<div class="success-message">
			Scan successful! Updated {scanResult.fields_updated.length} field(s).
		</div>
	{/if}
</div>

<style>
	.scanner-metadata {
		background: rgba(255, 255, 255, 0.05);
		border-radius: 8px;
		padding: 1rem;
		margin-top: 1rem;
	}

	.metadata-content {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.metadata-row {
		display: flex;
		gap: 0.75rem;
		font-size: 0.875rem;
	}

	.metadata-row .label {
		color: #9ca3af;
		min-width: 90px;
		font-weight: 500;
	}

	.metadata-row .value {
		color: #e5e7eb;
		flex: 1;
	}

	.metadata-row .value-link {
		color: #60a5fa;
		text-decoration: none;
		transition: color 0.2s;
	}

	.metadata-row .value-link:hover {
		color: #93c5fd;
		text-decoration: underline;
	}

	.metadata-row .value.confidence {
		color: #fbbf24;
	}

	.metadata-row .value.confidence.high {
		color: #34d399;
	}

	.url-link {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		color: #60a5fa;
		text-decoration: none;
		transition: color 0.2s;
	}

	.url-link:hover {
		color: #93c5fd;
		text-decoration: underline;
	}

	.tags-section {
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 0.5rem;
	}

	.tags-section .label {
		font-weight: 600;
		color: #d1d5db;
		min-width: auto;
	}

	.tags-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.tag-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
		transition: all 0.2s;
	}

	.tag-badge:hover {
		transform: translateY(-1px);
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	/* Color-coded tag types */
	.tag-badge.tag-artist {
		background: rgba(236, 72, 153, 0.2);
		color: #ec4899;
	}

	.tag-badge.tag-character {
		background: rgba(168, 85, 247, 0.2);
		color: #a855f7;
	}

	.tag-badge.tag-parody {
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
	}

	.tag-badge.tag-group {
		background: rgba(249, 115, 22, 0.2);
		color: #f97316;
	}

	.tag-badge.tag-language {
		background: rgba(59, 130, 246, 0.2);
		color: #3b82f6;
	}

	.tag-badge.tag-category {
		background: rgba(234, 179, 8, 0.2);
		color: #eab308;
	}

	.tag-badge.tag-tag {
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
	}

	.metadata-actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid rgba(255, 255, 255, 0.1);
	}

	.btn-rescan,
	.btn-clear,
	.btn-scan {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		font-weight: 500;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-rescan {
		background: rgba(96, 165, 250, 0.2);
		color: #60a5fa;
	}

	.btn-rescan:hover:not(:disabled) {
		background: rgba(96, 165, 250, 0.3);
	}

	.btn-clear {
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
	}

	.btn-clear:hover:not(:disabled) {
		background: rgba(239, 68, 68, 0.3);
	}

	.btn-scan {
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
	}

	.btn-scan:hover:not(:disabled) {
		background: rgba(34, 197, 94, 0.3);
	}

	.btn-rescan:disabled,
	.btn-clear:disabled,
	.btn-scan:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.no-metadata {
		text-align: center;
		padding: 1rem;
	}

	.error-message {
		margin-top: 0.75rem;
		padding: 0.75rem;
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.success-message {
		margin-top: 0.75rem;
		padding: 0.75rem;
		background: rgba(34, 197, 94, 0.2);
		color: #22c55e;
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.list-section {
		align-items: flex-start;
	}

	.value-list {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.list-item {
		color: #d1d5db;
		font-size: 0.875rem;
	}

	.links-section {
		align-items: flex-start;
	}

	.links-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.external-link-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.5rem;
		background: rgba(75, 85, 99, 0.3);
		color: #9ca3af;
		border-radius: 4px;
		font-size: 0.75rem;
		text-decoration: none;
		transition: all 0.2s;
	}

	.external-link-badge:hover {
		background: rgba(75, 85, 99, 0.5);
		color: #e5e7eb;
	}
</style>
