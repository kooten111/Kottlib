<script>
	import { onMount } from "svelte";
	import Navbar from "$lib/components/layout/Navbar.svelte";
	import Card from "$lib/components/common/Card.svelte";
	import ConfigInput from "$lib/components/common/ConfigInput.svelte";
	import {
		Scan,
		Settings,
		PlayCircle,
		CheckCircle,
		XCircle,
		AlertCircle,
	} from "lucide-svelte";

	let availableScanners = [];
	let libraryConfigs = [];
	let isLoading = true;
	let error = null;

	// Scan test state
	let testQuery = "";
	let testLibraryId = null;
	let testResult = null;
	let isScanning = false;
	let scanError = null;

	// Bulk scan state
	let bulkQueries = "";
	let bulkResults = null;
	let isBulkScanning = false;

	// Library scan state
	let selectedLibraryToScan = null;
	let libraryScanOptions = {
		overwrite: false,
		rescanExisting: false,
		confidenceThreshold: null,
	};
	let isLibraryScanning = false;
	let libraryScanResult = null;
	let libraryScanError = null;
	let scanProgress = {
		processed: 0,
		scanned: 0,
		total: 0,
		failed: 0,
		skipped: 0,
		error: null,
	};
	let progressInterval = null;

	// Configuration modal state
	let showConfigModal = false;
	let configLibrary = null;
	let configForm = {
		primary_scanner: "",
		fallback_scanners: [],
		confidence_threshold: 0.4,
		fallback_threshold: 0.7,
		scanner_configs: {},
	};
	let isSavingConfig = false;
	let configError = null;

	onMount(async () => {
		await loadScannerData();
	});

	async function loadScannerData() {
		try {
			isLoading = true;
			error = null;

			console.log("[loadScannerData] Fetching scanner data...");

			// Fetch available scanners
			const scannersRes = await fetch("/v2/scanners/available");
			if (!scannersRes.ok) throw new Error("Failed to load scanners");
			availableScanners = await scannersRes.json();

			// Fetch library configurations
			const configsRes = await fetch("/v2/scanners/libraries");
			if (!configsRes.ok)
				throw new Error("Failed to load configurations");
			libraryConfigs = await configsRes.json();

			console.log("[loadScannerData] Raw response:", libraryConfigs);
			console.log(
				"[loadScannerData] Threshold values:",
				libraryConfigs.map((c) => ({
					id: c.library_id,
					name: c.library_name,
					confidence_threshold: c.confidence_threshold,
					confidence_type: typeof c.confidence_threshold,
					fallback_threshold: c.fallback_threshold,
					fallback_type: typeof c.fallback_threshold,
				})),
			);

			console.log(
				"[loadScannerData] Scanner capabilities:",
				availableScanners.map((s) => ({
					name: s.name,
					provided_fields: s.provided_fields,
					primary_fields: s.primary_fields,
					description: s.description,
				})),
			);

			// Set default test library to first library with a configured scanner
			if (!testLibraryId && libraryConfigs.length > 0) {
				// Try to find a library with a scanner configured
				const configuredLib = libraryConfigs.find(
					(lib) => lib.primary_scanner,
				);
				testLibraryId = configuredLib
					? configuredLib.library_id
					: libraryConfigs[0].library_id;
			}

			isLoading = false;
		} catch (err) {
			console.error("[loadScannerData] Error:", err);
			error = err.message;
			isLoading = false;
		}
	}

	async function runTestScan() {
		if (!testQuery.trim()) {
			scanError = "Please enter a filename to scan";
			return;
		}

		try {
			isScanning = true;
			scanError = null;
			testResult = null;

			const response = await fetch("/v2/scanners/scan", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					query: testQuery,
					library_id: testLibraryId,
				}),
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || "Scan failed");
			}

			testResult = await response.json();
			isScanning = false;
		} catch (err) {
			console.error("Scan failed:", err);
			scanError = err.message;
			isScanning = false;
		}
	}

	async function runBulkScan() {
		const queries = bulkQueries.split("\n").filter((q) => q.trim());

		if (queries.length === 0) {
			return;
		}

		try {
			isBulkScanning = true;
			bulkResults = null;

			const response = await fetch("/v2/scanners/scan/bulk", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					queries: queries,
					library_id: testLibraryId,
					confidence_threshold: 0.4,
				}),
			});

			if (!response.ok) {
				throw new Error("Bulk scan failed");
			}

			bulkResults = await response.json();
			isBulkScanning = false;
		} catch (err) {
			console.error("Bulk scan failed:", err);
			isBulkScanning = false;
		}
	}

	async function pollScanProgress(libraryId) {
		try {
			const response = await fetch(
				`/v2/scanners/scan/library/${libraryId}/progress`,
			);
			if (response.ok) {
				const progress = await response.json();
				console.log("[SCAN PROGRESS]", progress);
				scanProgress = {
					processed: progress.processed ?? progress.scanned ?? 0,
					scanned: progress.scanned ?? 0,
					total: progress.total ?? 0,
					failed: progress.failed ?? 0,
					skipped: progress.skipped ?? 0,
					error: progress.error ?? null,
				};
				return progress;
			} else {
				console.error(
					"Progress endpoint returned:",
					response.status,
					response.statusText,
				);
			}
		} catch (err) {
			console.error("Failed to poll progress:", err);
		}
		return null;
	}

	async function runLibraryScan() {
		if (!selectedLibraryToScan) {
			libraryScanError = "Please select a library to scan";
			return;
		}

		const library = libraryConfigs.find(
			(l) => l.library_id === selectedLibraryToScan,
		);
		if (!library?.primary_scanner) {
			libraryScanError =
				"Selected library does not have a scanner configured";
			return;
		}

		if (
			!confirm(
				`Scan all comics in library "${library.library_name}"?\n\nThis may take a while for large libraries.`,
			)
		) {
			return;
		}

		try {
			isLibraryScanning = true;
			libraryScanError = null;
			libraryScanResult = null;
			scanProgress = {
				processed: 0,
				scanned: 0,
				total: 0,
				failed: 0,
				skipped: 0,
				error: null,
			};

			// Start the scan request - this now returns immediately
			const response = await fetch("/v2/scanners/scan/library", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					library_id: selectedLibraryToScan,
					overwrite: libraryScanOptions.overwrite,
					rescan_existing: libraryScanOptions.rescanExisting,
					confidence_threshold:
						libraryScanOptions.confidenceThreshold,
				}),
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					errorData.detail || "Library scan failed to start",
				);
			}

			const startResult = await response.json();
			if (startResult.status !== "started") {
				throw new Error("Failed to start library scan");
			}

			// Wait a bit for backend to initialize, then start polling
			await new Promise((resolve) => setTimeout(resolve, 500));

			// Start polling for progress
			progressInterval = setInterval(async () => {
				const progress = await pollScanProgress(selectedLibraryToScan);
				if (!progress) {
					return;
				}

				if (!progress.in_progress && progressInterval) {
					clearInterval(progressInterval);
					progressInterval = null;

					if (progress.error) {
						libraryScanError = progress.error;
						libraryScanResult = null;
					} else {
						libraryScanResult = {
							total_comics: scanProgress.total,
							scanned: scanProgress.scanned,
							failed: scanProgress.failed,
							skipped: scanProgress.skipped,
							processed: scanProgress.processed,
						};
					}

					isLibraryScanning = false;

					// Clear progress on backend
					await fetch(
						`/v2/scanners/scan/library/${selectedLibraryToScan}/progress`,
						{
							method: "DELETE",
						},
					);
				}
			}, 500); // Poll every 500ms
		} catch (err) {
			console.error("Library scan failed:", err);
			libraryScanError = err.message;
			if (progressInterval) {
				clearInterval(progressInterval);
				progressInterval = null;
			}
			isLibraryScanning = false;
		}
	}

	function getConfidenceBadgeClass(level) {
		const classes = {
			EXACT: "bg-green-900 text-green-200 border border-green-700",
			HIGH: "bg-blue-900 text-blue-200 border border-blue-700",
			MEDIUM: "bg-yellow-900 text-yellow-200 border border-yellow-700",
			LOW: "bg-orange-900 text-orange-200 border border-orange-700",
			NONE: "bg-red-900 text-red-200 border border-red-700",
		};
		return (
			classes[level] || "bg-gray-800 text-gray-200 border border-gray-600"
		);
	}

	function openConfigModal(library) {
		console.log("[openConfigModal] Opening modal for library:", library);
		configLibrary = library;
		configForm = {
			primary_scanner: library.primary_scanner || "",
			fallback_scanners: library.fallback_scanners || [],
			confidence_threshold: library.confidence_threshold || 0.4,
			fallback_threshold: library.fallback_threshold || 0.7,
			scanner_configs: library.scanner_configs || {},
		};
		console.log("[openConfigModal] Initial configForm:", configForm);
		configError = null;
		showConfigModal = true;
	}

	function closeConfigModal() {
		showConfigModal = false;
		configLibrary = null;
		configError = null;
	}

	async function saveConfiguration() {
		if (!configLibrary) return;

		if (!configForm.primary_scanner) {
			configError = "Please select a primary scanner";
			return;
		}

		try {
			isSavingConfig = true;
			configError = null;

			// Ensure threshold values are numbers
			const payload = {
				primary_scanner: configForm.primary_scanner,
				fallback_scanners: configForm.fallback_scanners,
				confidence_threshold: parseFloat(
					configForm.confidence_threshold,
				),
				fallback_threshold: parseFloat(configForm.fallback_threshold),
				scanner_configs: configForm.scanner_configs,
			};

			console.log("[saveConfiguration] Current configForm:", configForm);
			console.log("[saveConfiguration] Sending payload:", payload);

			const response = await fetch(
				`/v2/scanners/libraries/${configLibrary.library_id}/configure`,
				{
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload),
				},
			);

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					errorData.detail || "Failed to save configuration",
				);
			}

			const savedConfig = await response.json();
			console.log("[saveConfiguration] Server returned:", savedConfig);

			// Reload library configurations
			console.log("[saveConfiguration] Reloading library data...");
			await loadScannerData();

			// Close modal
			closeConfigModal();
		} catch (err) {
			console.error("[saveConfiguration] Error:", err);
			configError = err.message;
		} finally {
			isSavingConfig = false;
		}
	}
</script>

<Navbar />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-dark-text flex items-center gap-3">
			<Scan class="w-8 h-8" />
			Metadata Scanners
		</h1>
		<p class="mt-2 text-dark-text-secondary">
			Configure and test metadata scanners for your libraries
		</p>
	</div>

	{#if isLoading}
		<div class="flex justify-center items-center py-12">
			<div
				class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-orange"
			></div>
		</div>
	{:else if error}
		<Card>
			<div class="text-center py-8">
				<AlertCircle class="w-12 h-12 text-status-error mx-auto mb-4" />
				<p class="text-status-error">{error}</p>
				<button
					on:click={loadScannerData}
					class="mt-4 px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover transition-all duration-200 shadow-sm hover:shadow-md"
				>
					Retry
				</button>
			</div>
		</Card>
	{:else}
		<!-- Available Scanners -->
		<Card class="mb-6">
			<h2
				class="text-xl font-semibold mb-4 flex items-center gap-2 text-dark-text"
			>
				<Settings class="w-5 h-5" />
				Available Scanners
			</h2>
			<div class="grid gap-4 md:grid-cols-2">
				{#each availableScanners as scanner}
					<div
						class="border border-gray-700 rounded-lg p-4 bg-dark-bg-tertiary hover:border-gray-600 transition-colors"
					>
						<div class="flex items-start justify-between">
							<div>
								<h3 class="font-medium text-lg text-dark-text">
									{scanner.name}
								</h3>
								<span class="text-sm text-dark-text-secondary"
									>Level: {scanner.scan_level}</span
								>
							</div>
							<span
								class="px-2 py-1 bg-blue-900 text-blue-200 text-xs rounded-full border border-blue-700"
							>
								Active
							</span>
						</div>
						<p class="mt-2 text-sm text-dark-text-secondary">
							{scanner.description || "No description"}
						</p>
						{#if scanner.config_keys && scanner.config_keys.length > 0}
							<div class="mt-2">
								<p class="text-xs text-dark-text-muted">
									Config options:
								</p>
								<div class="flex flex-wrap gap-1 mt-1">
									{#each scanner.config_keys as key}
										<span
											class="text-xs bg-dark-bg-secondary border border-gray-700 px-2 py-0.5 rounded text-dark-text-secondary"
											>{key}</span
										>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</Card>

		<!-- Library Configurations -->
		<Card class="mb-6">
			<h2 class="text-xl font-semibold mb-4 text-dark-text">
				Library Scanner Configuration
			</h2>
			{#if libraryConfigs.length === 0}
				<div class="text-center py-8 text-dark-text-secondary">
					<p>No libraries found.</p>
					<p class="text-sm mt-2">
						Create a library first to configure scanners.
					</p>
				</div>
			{:else}
				<div class="space-y-4">
					{#each libraryConfigs as config}
						<div
							class="border border-gray-700 rounded-lg p-4 bg-dark-bg-tertiary hover:border-gray-600 transition-colors"
						>
							<div class="flex items-center justify-between mb-3">
								<div>
									<h3 class="font-medium text-dark-text">
										{config.library_name}
									</h3>
									<p
										class="text-xs text-dark-text-secondary mt-0.5"
									>
										{config.library_path}
									</p>
								</div>
								<button
									on:click={() => openConfigModal(config)}
									class="px-3 py-1.5 text-sm bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-1"
								>
									<Settings class="w-4 h-4" />
									Configure
								</button>
							</div>
							<div class="grid grid-cols-2 gap-4 text-sm">
								<div>
									<span class="text-dark-text-secondary"
										>Primary Scanner:</span
									>
									<span
										class="ml-2 font-medium text-dark-text"
									>
										{#if config.primary_scanner}
											{config.primary_scanner}
										{:else}
											<span class="text-status-warning"
												>Not configured</span
											>
										{/if}
									</span>
								</div>
								<div>
									<span class="text-dark-text-secondary"
										>Confidence Threshold:</span
									>
									<span
										class="ml-2 font-medium text-dark-text"
										>{(
											config.confidence_threshold * 100
										).toFixed(0)}%</span
									>
								</div>
								{#if config.fallback_scanners && config.fallback_scanners.length > 0}
									<div class="col-span-2">
										<span class="text-dark-text-secondary"
											>Fallback Scanners:</span
										>
										<span
											class="ml-2 font-medium text-dark-text"
											>{config.fallback_scanners.join(
												", ",
											)}</span
										>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</Card>

		<!-- Library-Wide Scanning -->
		<Card class="mb-6">
			<h2
				class="text-xl font-semibold mb-4 flex items-center gap-2 text-dark-text"
			>
				<Scan class="w-5 h-5" />
				Scan Entire Library
			</h2>
			<p class="text-sm text-dark-text-secondary mb-4">
				Scan all comics in a library for metadata. This may take a while
				for large libraries.
			</p>
			<div class="space-y-4">
				<div>
					<label
						class="block text-sm font-medium text-dark-text mb-3"
					>
						Select Library
					</label>
					<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
						{#each libraryConfigs as config}
							<button
								on:click={() =>
									(selectedLibraryToScan = config.library_id)}
								class="library-card {selectedLibraryToScan ===
								config.library_id
									? 'library-card-selected'
									: ''}"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1 min-w-0">
										<h3
											class="font-medium text-dark-text truncate"
										>
											{config.library_name}
										</h3>
										<p
											class="text-xs text-dark-text-secondary mt-1 truncate"
										>
											{config.library_path}
										</p>
									</div>
									{#if selectedLibraryToScan === config.library_id}
										<CheckCircle
											class="w-5 h-5 text-accent-orange flex-shrink-0 ml-2"
										/>
									{/if}
								</div>
								<div class="mt-2 pt-2 border-t border-gray-700">
									{#if config.primary_scanner}
										<span class="text-xs text-accent-blue"
											>Scanner: {config.primary_scanner}</span
										>
									{:else}
										<span
											class="text-xs text-status-warning"
											>No scanner configured</span
										>
									{/if}
								</div>
							</button>
						{/each}
					</div>
				</div>

				<div
					class="border border-gray-700 rounded-lg p-4 bg-dark-bg-secondary"
				>
					<h3 class="text-sm font-medium text-dark-text mb-3">
						Scan Options
					</h3>
					<div class="space-y-2">
						<label
							class="flex items-center gap-2 text-sm text-dark-text cursor-pointer"
						>
							<input
								type="checkbox"
								bind:checked={libraryScanOptions.overwrite}
								class="rounded border-gray-700 bg-dark-bg-tertiary text-accent-orange focus:ring-accent-orange focus:ring-offset-dark-bg"
							/>
							<span>Overwrite existing metadata</span>
						</label>
						<label
							class="flex items-center gap-2 text-sm text-dark-text cursor-pointer"
						>
							<input
								type="checkbox"
								bind:checked={libraryScanOptions.rescanExisting}
								class="rounded border-gray-700 bg-dark-bg-tertiary text-accent-orange focus:ring-accent-orange focus:ring-offset-dark-bg"
							/>
							<span>Rescan already scanned comics</span>
						</label>
						<div>
							<label class="block text-sm text-dark-text mb-1">
								Custom confidence threshold (optional, 0-1)
							</label>
							<input
								type="number"
								min="0"
								max="1"
								step="0.1"
								bind:value={
									libraryScanOptions.confidenceThreshold
								}
								placeholder="Use library default"
								class="w-full border border-gray-700 bg-dark-bg-tertiary text-dark-text rounded-lg px-3 py-2 focus:border-accent-orange focus:ring-2 focus:ring-accent-orange focus:ring-offset-2 focus:ring-offset-dark-bg transition-all"
							/>
						</div>
					</div>
				</div>

				<button
					on:click={runLibraryScan}
					disabled={isLibraryScanning || !selectedLibraryToScan}
					class="px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center gap-2 transition-all duration-200 shadow-sm hover:shadow-md"
				>
					{#if isLibraryScanning}
						<div
							class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
						></div>
						Scanning Library...
					{:else}
						<Scan class="w-4 h-4" />
						Scan Library
					{/if}
				</button>

				{#if isLibraryScanning}
					<div class="scan-progress-container">
						<div class="flex justify-between items-center mb-2">
							<span class="text-sm font-medium text-dark-text">
								{#if scanProgress.total > 0}
									Scanning library... ({scanProgress.processed}
									/ {scanProgress.total} comics)
								{:else}
									Preparing scan...
								{/if}
							</span>
							{#if scanProgress.total > 0}
								<span class="text-sm text-dark-text-secondary">
									{Math.round(
										(scanProgress.processed /
											scanProgress.total) *
											100,
									)}%
								</span>
							{/if}
						</div>
						<div class="progress-bar-wrapper">
							<div
								class="progress-bar-fill"
								style="width: {scanProgress.total > 0
									? (scanProgress.processed /
											scanProgress.total) *
										100
									: 0}%"
							></div>
						</div>
						<div
							class="mt-2 text-xs text-dark-text-secondary flex flex-wrap gap-3"
						>
							<span>Matched: {scanProgress.scanned}</span>
							<span>Failed: {scanProgress.failed}</span>
							<span>Skipped: {scanProgress.skipped}</span>
						</div>
					</div>
				{/if}

				{#if libraryScanError}
					<div
						class="bg-red-950 border border-red-800 rounded-lg p-4 flex items-start gap-3"
					>
						<XCircle
							class="w-5 h-5 text-status-error flex-shrink-0 mt-0.5"
						/>
						<div>
							<p class="font-medium text-red-200">
								Library Scan Failed
							</p>
							<p class="text-sm text-red-300 mt-1">
								{libraryScanError}
							</p>
						</div>
					</div>
				{/if}

				{#if libraryScanResult}
					<div
						class="bg-green-950 border border-green-800 rounded-lg p-4"
					>
						<div class="flex items-start gap-3">
							<CheckCircle
								class="w-5 h-5 text-status-success flex-shrink-0 mt-0.5"
							/>
							<div class="flex-1">
								<p class="font-medium text-green-200 mb-3">
									Library Scan Complete!
								</p>
								<div
									class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm"
								>
									<div>
										<span
											class="text-dark-text-secondary block"
											>Total Comics in Library</span
										>
										<span
											class="text-lg font-bold text-green-200"
											>{libraryScanResult.total_comics}</span
										>
									</div>
									<div>
										<span
											class="text-dark-text-secondary block"
											>Successfully Scanned</span
										>
										<span
											class="text-lg font-bold text-green-200"
											>{libraryScanResult.scanned}</span
										>
									</div>
									<div>
										<span
											class="text-dark-text-secondary block"
											>Failed to Scan</span
										>
										<span
											class="text-lg font-bold text-yellow-200"
											>{libraryScanResult.failed}</span
										>
									</div>
									<div>
										<span
											class="text-dark-text-secondary block"
											>Skipped</span
										>
										<span
											class="text-lg font-bold text-gray-300"
											>{libraryScanResult.skipped}</span
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</Card>

		<!-- Test Scanner -->
		<Card class="mb-6">
			<h2
				class="text-xl font-semibold mb-4 flex items-center gap-2 text-dark-text"
			>
				<PlayCircle class="w-5 h-5" />
				Test Scanner
			</h2>
			<div class="space-y-4">
				<div>
					<label
						for="test-library-select"
						class="block text-sm font-medium text-dark-text mb-2"
					>
						Library
					</label>
					<select
						id="test-library-select"
						bind:value={testLibraryId}
						class="w-full border border-gray-700 bg-dark-bg-tertiary text-dark-text rounded-lg px-3 py-2 focus:border-accent-orange focus:ring-2 focus:ring-accent-orange focus:ring-offset-2 focus:ring-offset-dark-bg transition-all"
					>
						{#if libraryConfigs.length === 0}
							<option value={null}>No libraries available</option>
						{:else}
							{#each libraryConfigs as config}
								<option value={config.library_id}>
									{config.library_name}
									{#if config.primary_scanner}
										(Scanner: {config.primary_scanner})
									{:else}
										(No scanner configured)
									{/if}
								</option>
							{/each}
						{/if}
					</select>
					<p class="text-xs text-dark-text-secondary mt-1">
						Select which library's scanner configuration to use
					</p>
				</div>

				<div>
					<label
						for="test-filename-input"
						class="block text-sm font-medium text-dark-text mb-2"
					>
						Filename to Scan
					</label>
					<input
						id="test-filename-input"
						type="text"
						bind:value={testQuery}
						placeholder="[Artist] Comic Title [English].cbz"
						class="w-full border border-gray-700 bg-dark-bg-tertiary text-dark-text rounded-lg px-3 py-2 focus:border-accent-orange focus:ring-2 focus:ring-accent-orange focus:ring-offset-2 focus:ring-offset-dark-bg transition-all"
					/>
				</div>

				<button
					on:click={runTestScan}
					disabled={isScanning || !testQuery.trim()}
					class="px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center gap-2 transition-all duration-200 shadow-sm hover:shadow-md"
				>
					{#if isScanning}
						<div
							class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
						></div>
						Scanning...
					{:else}
						<Scan class="w-4 h-4" />
						Run Scan
					{/if}
				</button>

				{#if scanError}
					<div
						class="bg-red-950 border border-red-800 rounded-lg p-4 flex items-start gap-3"
					>
						<XCircle
							class="w-5 h-5 text-status-error flex-shrink-0 mt-0.5"
						/>
						<div>
							<p class="font-medium text-red-200">Scan Failed</p>
							<p class="text-sm text-red-300 mt-1">{scanError}</p>
						</div>
					</div>
				{/if}

				{#if testResult}
					<div
						class="bg-green-950 border border-green-800 rounded-lg p-4"
					>
						<div class="flex items-start gap-3">
							<CheckCircle
								class="w-5 h-5 text-status-success flex-shrink-0 mt-0.5"
							/>
							<div class="flex-1">
								<div
									class="flex items-center justify-between mb-2"
								>
									<p class="font-medium text-green-200">
										Match Found!
									</p>
									<span
										class="px-2 py-1 rounded-full text-xs font-medium {getConfidenceBadgeClass(
											testResult.confidence_level,
										)}"
									>
										{testResult.confidence_level} ({(
											testResult.confidence * 100
										).toFixed(0)}%)
									</span>
								</div>
								<div class="space-y-2 text-sm">
									<div>
										<span class="text-dark-text-secondary"
											>Source:</span
										>
										<a
											href={testResult.source_url}
											target="_blank"
											class="ml-2 text-accent-blue hover:text-blue-400 hover:underline"
										>
											{testResult.source_url}
										</a>
									</div>
									<div>
										<span class="text-dark-text-secondary"
											>Title:</span
										>
										<span class="ml-2 text-dark-text"
											>{testResult.metadata.title ||
												"N/A"}</span
										>
									</div>
									{#if testResult.metadata.artists && testResult.metadata.artists.length > 0}
										<div>
											<span
												class="text-dark-text-secondary"
												>Artists:</span
											>
											<span class="ml-2 text-dark-text"
												>{testResult.metadata.artists.join(
													", ",
												)}</span
											>
										</div>
									{/if}
									{#if testResult.tags && testResult.tags.length > 0}
										<div>
											<span
												class="text-dark-text-secondary"
												>Tags:</span
											>
											<div
												class="flex flex-wrap gap-1 mt-1"
											>
												{#each testResult.tags.slice(0, 10) as tag}
													<span
														class="text-xs bg-dark-bg-secondary border border-gray-700 px-2 py-0.5 rounded text-dark-text-secondary"
													>
														{tag.split(":")[1] ||
															tag}
													</span>
												{/each}
												{#if testResult.tags.length > 10}
													<span
														class="text-xs text-dark-text-muted"
													>
														+{testResult.tags
															.length - 10} more
													</span>
												{/if}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</Card>

		<!-- Bulk Scan -->
		<Card>
			<h2 class="text-xl font-semibold mb-4 text-dark-text">Bulk Scan</h2>
			<div class="space-y-4">
				<div>
					<label
						for="bulk-filenames-textarea"
						class="block text-sm font-medium text-dark-text mb-2"
					>
						Filenames (one per line)
					</label>
					<textarea
						id="bulk-filenames-textarea"
						bind:value={bulkQueries}
						placeholder="[Artist1] Title1.cbz&#10;[Artist2] Title2.cbz&#10;[Artist3] Title3.cbz"
						rows="5"
						class="w-full border border-gray-700 bg-dark-bg-tertiary text-dark-text rounded-lg px-3 py-2 font-mono text-sm focus:border-accent-orange focus:ring-2 focus:ring-accent-orange focus:ring-offset-2 focus:ring-offset-dark-bg transition-all"
					></textarea>
				</div>

				<button
					on:click={runBulkScan}
					disabled={isBulkScanning || !bulkQueries.trim()}
					class="px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover disabled:bg-gray-600 transition-all duration-200 shadow-sm hover:shadow-md"
				>
					{#if isBulkScanning}
						<div class="flex items-center gap-2">
							<div
								class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
							></div>
							Scanning...
						</div>
					{:else}
						Scan All
					{/if}
				</button>

				{#if bulkResults}
					<div
						class="border border-gray-700 rounded-lg p-4 bg-dark-bg-tertiary"
					>
						<div class="grid grid-cols-3 gap-4 mb-4">
							<div class="text-center">
								<p class="text-2xl font-bold text-dark-text">
									{bulkResults.total}
								</p>
								<p class="text-sm text-dark-text-secondary">
									Total
								</p>
							</div>
							<div class="text-center">
								<p
									class="text-2xl font-bold text-status-success"
								>
									{bulkResults.matched}
								</p>
								<p class="text-sm text-dark-text-secondary">
									Matched
								</p>
							</div>
							<div class="text-center">
								<p class="text-2xl font-bold text-status-error">
									{bulkResults.rejected}
								</p>
								<p class="text-sm text-dark-text-secondary">
									Rejected
								</p>
							</div>
						</div>

						<div class="space-y-2 max-h-96 overflow-y-auto">
							{#each bulkResults.results as result}
								<div
									class="flex items-center gap-2 text-sm bg-dark-bg-secondary border border-gray-700 p-2 rounded"
								>
									{#if result.status === "matched"}
										<CheckCircle
											class="w-4 h-4 text-status-success flex-shrink-0"
										/>
										<span
											class="flex-1 truncate text-dark-text"
											>{result.query}</span
										>
										<span
											class="px-2 py-0.5 rounded text-xs {getConfidenceBadgeClass(
												result.confidence_level,
											)}"
										>
											{(result.confidence * 100).toFixed(
												0,
											)}%
										</span>
									{:else}
										<XCircle
											class="w-4 h-4 text-status-error flex-shrink-0"
										/>
										<span
											class="flex-1 truncate text-dark-text-secondary"
											>{result.query}</span
										>
										<span
											class="text-xs text-dark-text-muted"
											>{result.reason ||
												result.error ||
												"Failed"}</span
										>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</Card>
	{/if}
</div>

<!-- Configuration Modal -->
{#if showConfigModal && configLibrary}
	<div
		class="fixed inset-0 flex items-center justify-center z-50 p-4"
		style="background: var(--color-overlay); backdrop-filter: blur(4px);"
	>
		<div
			class="bg-dark-bg-secondary rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border-2 border-gray-700"
		>
			<!-- Modal Header -->
			<div
				class="border-b border-gray-700 px-6 py-4 flex items-center justify-between sticky top-0 bg-dark-bg-secondary"
			>
				<h3 class="text-xl font-semibold text-dark-text">
					Configure Scanner for {configLibrary.library_name}
				</h3>
				<button
					on:click={closeConfigModal}
					class="text-dark-text-secondary hover:text-dark-text transition-colors"
				>
					<XCircle class="w-6 h-6" />
				</button>
			</div>

			<!-- Modal Body -->
			<div class="px-6 py-4 space-y-6">
				<!-- Primary Scanner -->
				<div>
					<label
						for="config-primary-scanner"
						class="block text-sm font-medium text-dark-text mb-2"
					>
						Primary Scanner <span class="text-status-error">*</span>
					</label>
					<select
						id="config-primary-scanner"
						bind:value={configForm.primary_scanner}
						class="w-full border border-gray-700 bg-dark-bg-tertiary text-dark-text rounded-lg px-3 py-2 focus:ring-2 focus:ring-accent-orange focus:border-accent-orange transition-all"
					>
						<option value="">Select a scanner...</option>
						{#each availableScanners as scanner}
							<option value={scanner.name}
								>{scanner.name} - {scanner.description}</option
							>
						{/each}
					</select>
					<p class="text-xs text-dark-text-secondary mt-1">
						The primary scanner to use for this library
					</p>
				</div>

				<!-- Confidence Threshold -->
				<div>
					<label
						for="config-confidence-threshold"
						class="block text-sm font-medium text-dark-text mb-2"
					>
						Confidence Threshold: {(
							configForm.confidence_threshold * 100
						).toFixed(0)}%
					</label>
					<input
						id="config-confidence-threshold"
						type="range"
						value={configForm.confidence_threshold}
						on:input={(e) =>
							(configForm.confidence_threshold = parseFloat(
								e.target.value,
							))}
						min="0"
						max="1"
						step="0.05"
						class="w-full accent-accent-orange"
					/>
					<div
						class="flex justify-between text-xs text-dark-text-secondary mt-1"
					>
						<span>0% (Accept all)</span>
						<span>50% (Balanced)</span>
						<span>100% (Perfect only)</span>
					</div>
					<p class="text-xs text-dark-text-secondary mt-2">
						Minimum confidence score required to accept a match.
						Results below this threshold will be rejected.
					</p>
				</div>

				<!-- Fallback Threshold -->
				<div>
					<label
						for="config-fallback-threshold"
						class="block text-sm font-medium text-dark-text mb-2"
					>
						Fallback Threshold: {(
							configForm.fallback_threshold * 100
						).toFixed(0)}%
					</label>
					<input
						id="config-fallback-threshold"
						type="range"
						value={configForm.fallback_threshold}
						on:input={(e) =>
							(configForm.fallback_threshold = parseFloat(
								e.target.value,
							))}
						min="0"
						max="1"
						step="0.05"
						class="w-full accent-accent-orange"
					/>
					<div
						class="flex justify-between text-xs text-dark-text-secondary mt-1"
					>
						<span>0%</span>
						<span>70% (Recommended)</span>
						<span>100%</span>
					</div>
					<p class="text-xs text-dark-text-secondary mt-2">
						If primary scanner confidence is below this threshold,
						fallback scanners will be used (if configured).
					</p>
				</div>

				<!-- Fallback Scanners -->
				<div>
					<span class="block text-sm font-medium text-dark-text mb-2">
						Fallback Scanners (Optional)
					</span>
					<div class="space-y-2">
						{#each availableScanners as scanner}
							{#if scanner.name !== configForm.primary_scanner}
								<label class="flex items-center">
									<input
										type="checkbox"
										checked={configForm.fallback_scanners.includes(
											scanner.name,
										)}
										on:change={(e) => {
											if (e.target.checked) {
												configForm.fallback_scanners = [
													...configForm.fallback_scanners,
													scanner.name,
												];
											} else {
												configForm.fallback_scanners =
													configForm.fallback_scanners.filter(
														(s) =>
															s !== scanner.name,
													);
											}
										}}
										class="rounded border-gray-700 bg-dark-bg-tertiary text-accent-orange focus:ring-accent-orange focus:ring-offset-dark-bg-secondary"
									/>
									<span class="ml-2 text-sm text-dark-text"
										>{scanner.name} - {scanner.description}</span
									>
								</label>
							{/if}
						{/each}
					</div>
					<p class="text-xs text-dark-text-secondary mt-2">
						Additional scanners to try if the primary scanner
						returns low confidence results.
					</p>
				</div>

				<!-- Scanner Specific Config -->
				{#if configForm.primary_scanner}
					{@const scanner = availableScanners.find(
						(s) => s.name === configForm.primary_scanner,
					)}
					{#if scanner && scanner.config_schema && scanner.config_schema.length > 0}
						<div class="border-t border-gray-700 pt-4">
							<h4
								class="text-sm font-medium text-dark-text mb-3 flex items-center gap-2"
							>
								<Settings class="w-4 h-4" />
								{scanner.name} Configuration
							</h4>

							<!-- Basic Options (non-advanced) -->
							<div class="space-y-4 mb-4">
								{#each scanner.config_schema.filter((opt) => !opt.advanced) as option}
									<ConfigInput
										{option}
										value={configForm.scanner_configs?.[
											configForm.primary_scanner
										]?.[option.key]}
										onChange={(newValue) => {
											if (!configForm.scanner_configs)
												configForm.scanner_configs = {};
											if (
												!configForm.scanner_configs[
													configForm.primary_scanner
												]
											)
												configForm.scanner_configs[
													configForm.primary_scanner
												] = {};
											configForm.scanner_configs[
												configForm.primary_scanner
											][option.key] = newValue;
										}}
									/>
								{/each}
							</div>

							<!-- Advanced Options (collapsible) -->
							{#if scanner.config_schema.filter((opt) => opt.advanced).length > 0}
								{@const advancedOptions =
									scanner.config_schema.filter(
										(opt) => opt.advanced,
									)}
								<details class="border-t border-gray-700 pt-4">
									<summary
										class="cursor-pointer text-sm font-medium text-dark-text-secondary mb-3 hover:text-dark-text transition-colors"
									>
										Advanced Options ({advancedOptions.length})
									</summary>
									<div class="space-y-4 mt-4">
										{#each advancedOptions as option}
											<ConfigInput
												{option}
												value={configForm
													.scanner_configs?.[
													configForm.primary_scanner
												]?.[option.key]}
												onChange={(newValue) => {
													if (
														!configForm.scanner_configs
													)
														configForm.scanner_configs =
															{};
													if (
														!configForm
															.scanner_configs[
															configForm
																.primary_scanner
														]
													)
														configForm.scanner_configs[
															configForm.primary_scanner
														] = {};
													configForm.scanner_configs[
														configForm.primary_scanner
													][option.key] = newValue;
												}}
											/>
										{/each}
									</div>
								</details>
							{/if}
						</div>
					{/if}
				{/if}

				<!-- Error Message -->
				{#if configError}
					<div
						class="bg-red-950 border border-red-800 rounded-lg p-4 flex items-start gap-3"
					>
						<XCircle
							class="w-5 h-5 text-status-error flex-shrink-0 mt-0.5"
						/>
						<div>
							<p class="font-medium text-red-200">
								Configuration Error
							</p>
							<p class="text-sm text-red-300 mt-1">
								{configError}
							</p>
						</div>
					</div>
				{/if}
			</div>

			<!-- Modal Footer -->
			<div
				class="border-t border-gray-700 px-6 py-4 flex justify-end gap-3 sticky bottom-0 bg-dark-bg-secondary"
			>
				<button
					on:click={closeConfigModal}
					disabled={isSavingConfig}
					class="px-4 py-2 border border-gray-700 bg-dark-bg-tertiary text-dark-text rounded-lg hover:bg-gray-600 hover:border-gray-600 transition-all disabled:opacity-50"
				>
					Cancel
				</button>
				<button
					on:click={saveConfiguration}
					disabled={isSavingConfig || !configForm.primary_scanner}
					class="px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm hover:shadow-md"
				>
					{#if isSavingConfig}
						<div
							class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
						></div>
						Saving...
					{:else}
						<CheckCircle class="w-4 h-4" />
						Save Configuration
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.library-card {
		text-align: left;
		padding: 1rem;
		border: 2px solid var(--color-gray-700, #374151);
		background: var(--color-dark-bg-tertiary, #1f2937);
		border-radius: 8px;
		transition: all 0.2s;
		cursor: pointer;
	}

	.library-card:hover {
		border-color: var(--color-gray-600, #4b5563);
		background: var(--color-gray-800, #1f2937);
	}

	.library-card-selected {
		border-color: var(--color-accent-orange, #ff6740);
		background: rgba(255, 103, 64, 0.1);
	}

	.library-card-selected:hover {
		border-color: var(--color-accent-orange, #ff6740);
		background: rgba(255, 103, 64, 0.15);
	}

	.scan-progress-container {
		padding: 1rem;
		background: rgba(0, 0, 0, 0.2);
		border: 1px solid var(--color-gray-700, #374151);
		border-radius: 8px;
	}

	.progress-bar-wrapper {
		width: 100%;
		height: 8px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-bar-fill {
		height: 100%;
		background: linear-gradient(90deg, #ff6740 0%, #ff4520 100%);
		border-radius: 4px;
		transition: width 0.3s ease;
		box-shadow: 0 0 10px rgba(255, 103, 64, 0.5);
	}
</style>
