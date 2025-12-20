<script>
	import { onMount } from "svelte";
	import Navbar from "$lib/components/layout/Navbar.svelte";
	import ThemeSelector from "$lib/components/settings/ThemeSelector.svelte";
	import { getConfig, updateConfig } from "$lib/api/config";
	import {
		Settings,
		Palette,
		Server,
		Database,
		HardDrive,
		ToggleLeft,
		Save,
		RotateCw,
		AlertCircle,
		CheckCircle,
		Globe,
		Wrench,
	} from "lucide-svelte";

	let activeTab = "appearance";
	let config = null;
	let originalConfig = null;
	let isLoading = true;
	let isSaving = false;
	let error = null;
	let successMessage = null;
	let hasChanges = false;

	// Maintenance tab state
	let isReindexing = false;
	let reindexMessage = null;
	let reindexError = null;
	let searchIndexStatus = null;

	const tabs = [
		{ id: "appearance", label: "Appearance", icon: Palette },
		{ id: "server", label: "Server", icon: Server },
		{ id: "storage", label: "Storage", icon: HardDrive },
		{ id: "features", label: "Features", icon: ToggleLeft },
		{ id: "maintenance", label: "Maintenance", icon: Wrench },
	];

	const logLevels = ["debug", "info", "warning", "error"];

	onMount(async () => {
		await loadConfig();
	});

	async function loadConfig() {
		try {
			isLoading = true;
			error = null;
			const data = await getConfig();
			config = data;
			originalConfig = JSON.parse(JSON.stringify(data));
			hasChanges = false;
			isLoading = false;
		} catch (err) {
			console.error("Failed to load config:", err);
			error = err.message;
			isLoading = false;
		}
	}

	function checkForChanges() {
		hasChanges = JSON.stringify(config) !== JSON.stringify(originalConfig);
	}

	async function saveConfig() {
		try {
			isSaving = true;
			error = null;
			successMessage = null;

			const updatePayload = {
				server: config.server,
				database: config.database,
				storage: config.storage,
				features: config.features,
			};

			const result = await updateConfig(updatePayload);
			successMessage = result.message;

			if (result.restart_required) {
				successMessage +=
					" Note: Server restart required for some changes to take effect.";
			}

			// Reload to get the saved state
			await loadConfig();

			isSaving = false;
		} catch (err) {
			console.error("Failed to save config:", err);
			error = err.message;
			isSaving = false;
		}
	}

	function resetChanges() {
		config = JSON.parse(JSON.stringify(originalConfig));
		hasChanges = false;
		successMessage = null;
		error = null;
	}

	function addCorsOrigin() {
		config.server.cors_origins = [...config.server.cors_origins, ""];
		checkForChanges();
	}

	function removeCorsOrigin(index) {
		config.server.cors_origins = config.server.cors_origins.filter(
			(_, i) => i !== index,
		);
		checkForChanges();
	}

	function updateCorsOrigin(index, value) {
		config.server.cors_origins[index] = value;
		checkForChanges();
	}

	// Maintenance functions
	async function loadSearchIndexStatus() {
		try {
			const response = await fetch("/v2/admin/search-index/status");
			if (!response.ok)
				throw new Error("Failed to load search index status");
			searchIndexStatus = await response.json();
		} catch (err) {
			console.error("Failed to load search index status:", err);
			searchIndexStatus = { error: err.message };
		}
	}

	async function runMigration() {
		try {
			isReindexing = true;
			reindexError = null;
			reindexMessage = null;

			const response = await fetch("/v2/admin/migrate/search-indexes", {
				method: "POST",
			});

			if (!response.ok) throw new Error("Failed to run migration");

			const result = await response.json();
			reindexMessage = result.message;

			// Reload status
			await loadSearchIndexStatus();

			isReindexing = false;
		} catch (err) {
			console.error("Migration failed:", err);
			reindexError = err.message;
			isReindexing = false;
		}
	}

	async function reindexSearch() {
		try {
			isReindexing = true;
			reindexError = null;
			reindexMessage = null;

			const response = await fetch("/v2/admin/reindex-search", {
				method: "POST",
			});

			if (!response.ok) throw new Error("Failed to start reindex");

			const result = await response.json();
			reindexMessage = result.message;

			// Reload status after a delay
			setTimeout(() => loadSearchIndexStatus(), 2000);

			isReindexing = false;
		} catch (err) {
			console.error("Reindex failed:", err);
			reindexError = err.message;
			isReindexing = false;
		}
	}

	// Load search index status when maintenance tab is opened
	$: if (activeTab === "maintenance" && searchIndexStatus === null) {
		loadSearchIndexStatus();
	}
</script>

<svelte:head>
	<title>Server Settings - Kottlib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		<!-- Page Header -->
		<div class="page-header">
			<div class="header-title-section">
				<div class="icon-wrapper">
					<Settings class="w-8 h-8 text-accent-orange" />
				</div>
				<div>
					<h1 class="page-title">Server Settings</h1>
					<p class="page-subtitle">
						Configure your Kottlib server and preferences
					</p>
				</div>
			</div>

			{#if hasChanges}
				<div class="action-buttons">
					<button
						class="btn-secondary"
						on:click={resetChanges}
						disabled={isSaving}
					>
						<RotateCw class="w-4 h-4" />
						Reset
					</button>
					<button
						class="btn-primary"
						on:click={saveConfig}
						disabled={isSaving}
					>
						{#if isSaving}
							<div class="spinner-small" />
							Saving...
						{:else}
							<Save class="w-4 h-4" />
							Save Changes
						{/if}
					</button>
				</div>
			{/if}
		</div>

		{#if error}
			<div class="alert alert-error">
				<AlertCircle class="w-5 h-5" />
				<span>{error}</span>
			</div>
		{/if}

		{#if successMessage}
			<div class="alert alert-success">
				<CheckCircle class="w-5 h-5" />
				<span>{successMessage}</span>
			</div>
		{/if}

		{#if isLoading}
			<div class="loading-container">
				<div class="spinner" />
				<p class="text-gray-400 mt-4">Loading settings...</p>
			</div>
		{:else if config}
			<!-- Tabs -->
			<div class="tabs">
				{#each tabs as tab}
					<button
						class="tab"
						class:active={activeTab === tab.id}
						on:click={() => (activeTab = tab.id)}
					>
						<svelte:component this={tab.icon} class="w-5 h-5" />
						{tab.label}
					</button>
				{/each}
			</div>

			<!-- Tab Content -->
			<div class="tab-content">
				<!-- Appearance Tab -->
				{#if activeTab === "appearance"}
					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">Theme</h2>
							<p class="section-description">
								Choose your preferred color theme
							</p>
						</div>
						<div class="section-body">
							<ThemeSelector />
						</div>
					</div>
				{/if}

				<!-- Server Tab -->
				{#if activeTab === "server"}
					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">Server Configuration</h2>
							<p class="section-description">
								Configure server host, port, and logging
								settings. Changes to host/port require a server
								restart.
							</p>
						</div>
						<div class="section-body">
							<div class="form-grid">
								<div class="form-group">
									<label for="host">Host</label>
									<input
										id="host"
										type="text"
										bind:value={config.server.host}
										on:input={checkForChanges}
										placeholder="0.0.0.0"
									/>
									<p class="form-hint">
										Server host address (0.0.0.0 = all
										interfaces, 127.0.0.1 = local only)
									</p>
								</div>

								<div class="form-group">
									<label for="port">Port</label>
									<input
										id="port"
										type="number"
										min="1"
										max="65535"
										bind:value={config.server.port}
										on:input={checkForChanges}
										placeholder="8081"
									/>
									<p class="form-hint">
										Server port number (1-65535)
									</p>
								</div>

								<div class="form-group">
									<label for="log_level">Log Level</label>
									<select
										id="log_level"
										bind:value={config.server.log_level}
										on:change={checkForChanges}
									>
										{#each logLevels as level}
											<option value={level}
												>{level
													.charAt(0)
													.toUpperCase() +
													level.slice(1)}</option
											>
										{/each}
									</select>
									<p class="form-hint">
										Logging verbosity (debug = most verbose,
										error = least)
									</p>
								</div>

								<div class="form-group full-width">
									<div class="form-group-header">
										<label>CORS Origins</label>
										<button
											class="btn-sm"
											on:click={addCorsOrigin}
										>
											<span class="text-lg">+</span> Add Origin
										</button>
									</div>
									<div class="cors-list">
										{#each config.server.cors_origins as origin, index}
											<div class="cors-item">
												<Globe
													class="w-4 h-4 text-gray-400"
												/>
												<input
													type="text"
													value={origin}
													on:input={(e) =>
														updateCorsOrigin(
															index,
															e.target.value,
														)}
													placeholder="https://example.com or *"
												/>
												<button
													class="btn-icon-danger"
													on:click={() =>
														removeCorsOrigin(index)}
												>
													×
												</button>
											</div>
										{/each}
									</div>
									<p class="form-hint">
										Allowed origins for Cross-Origin
										Resource Sharing. Use * to allow all
										origins (not recommended for
										production).
									</p>
								</div>

								<div class="form-group full-width">
									<label class="checkbox-label">
										<input
											type="checkbox"
											bind:checked={config.server.reload}
											on:change={checkForChanges}
										/>
										<span
											>Enable auto-reload (development
											only)</span
										>
									</label>
									<p class="form-hint">
										Automatically reload server on code
										changes (development mode)
									</p>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Storage Tab -->
				{#if activeTab === "storage"}
					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">Storage Paths</h2>
							<p class="section-description">
								Configure storage directories for covers and
								cache. Leave empty for auto-detection.
							</p>
						</div>
						<div class="section-body">
							<div class="form-grid">
								<div class="form-group full-width">
									<label for="covers_dir"
										>Covers Directory</label
									>
									<input
										id="covers_dir"
										type="text"
										bind:value={config.storage.covers_dir}
										on:input={checkForChanges}
										placeholder="Auto-detect (same as database)"
									/>
									<p class="form-hint">
										Directory for cover images. Each library
										has its own subdirectory. Leave empty
										for auto-detection.
									</p>
								</div>

								<div class="form-group full-width">
									<label for="cache_dir"
										>Cache Directory</label
									>
									<input
										id="cache_dir"
										type="text"
										bind:value={config.storage.cache_dir}
										on:input={checkForChanges}
										placeholder="Not configured"
									/>
									<p class="form-hint">
										Optional directory for temporary page
										cache. Leave empty to disable caching.
									</p>
								</div>
							</div>
						</div>
					</div>

					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">Database</h2>
							<p class="section-description">
								Database configuration. Changes require server
								restart.
							</p>
						</div>
						<div class="section-body">
							<div class="form-grid">
								<div class="form-group full-width">
									<label for="db_path">Database Path</label>
									<input
										id="db_path"
										type="text"
										bind:value={config.database.path}
										on:input={checkForChanges}
										placeholder="Auto-detect platform default"
									/>
									<p class="form-hint">
										Path to SQLite database file. Leave
										empty for platform-specific default
										location.
									</p>
								</div>

								<div class="form-group full-width">
									<label class="checkbox-label">
										<input
											type="checkbox"
											bind:checked={config.database.echo}
											on:change={checkForChanges}
										/>
										<span>Enable SQL query logging</span>
									</label>
									<p class="form-hint">
										Log all SQL queries (for debugging, may
										impact performance)
									</p>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Features Tab -->
				{#if activeTab === "features"}
					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">Feature Flags</h2>
							<p class="section-description">
								Enable or disable server features
							</p>
						</div>
						<div class="section-body">
							<div class="features-grid">
								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Legacy API
										</h3>
										<p class="feature-description">
											YACReader-compatible legacy API
											(plain text format)
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features.legacy_api
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>

								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Modern API
										</h3>
										<p class="feature-description">
											Modern JSON REST API for web UI and
											apps
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features.modern_api
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>

								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Reading Progress
										</h3>
										<p class="feature-description">
											Track user reading progress and
											bookmarks
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features.reading_progress
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>

								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Series Detection
										</h3>
										<p class="feature-description">
											Automatically detect and group comic
											series
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features.series_detection
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>

								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Collections
										</h3>
										<p class="feature-description">
											Enable user collections and reading
											lists
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features.collections
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>

								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Auto Thumbnails
										</h3>
										<p class="feature-description">
											Automatically generate thumbnails
											during scan
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features.auto_thumbnails
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>

								<div class="feature-item">
									<div class="feature-info">
										<h3 class="feature-title">
											Ignore Series Metadata
										</h3>
										<p class="feature-description">
											Ignore series metadata from comic
											files (use folder structure only)
										</p>
									</div>
									<label class="toggle">
										<input
											type="checkbox"
											bind:checked={
												config.features
													.ignore_series_metadata
											}
											on:change={checkForChanges}
										/>
										<span class="toggle-slider"></span>
									</label>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Maintenance Tab -->
				{#if activeTab === "maintenance"}
					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">Search Index</h2>
							<p class="section-description">
								Manage the full-text search index for advanced
								metadata search
							</p>
						</div>
						<div class="section-body">
							{#if searchIndexStatus}
								<div class="status-card">
									{#if searchIndexStatus.error}
										<div class="status-item error">
											<AlertCircle class="w-5 h-5" />
											<span
												>Error: {searchIndexStatus.error}</span
											>
										</div>
									{:else if searchIndexStatus.fts_enabled}
										<div
											class="status-item {searchIndexStatus.index_complete
												? 'success'
												: 'warning'}"
										>
											{#if searchIndexStatus.index_complete}
												<CheckCircle class="w-5 h-5" />
											{:else}
												<AlertCircle class="w-5 h-5" />
											{/if}
											<div class="status-text">
												<strong
													>{searchIndexStatus.message}</strong
												>
												<p
													class="text-sm text-gray-400 mt-1"
												>
													{searchIndexStatus.comics_indexed}
													of {searchIndexStatus.total_comics}
													comics indexed
												</p>
											</div>
										</div>
									{:else}
										<div class="status-item warning">
											<AlertCircle class="w-5 h-5" />
											<div class="status-text">
												<strong
													>{searchIndexStatus.message}</strong
												>
												<p
													class="text-sm text-gray-400 mt-1"
												>
													Run the migration to enable
													advanced search features
												</p>
											</div>
										</div>
									{/if}
								</div>
							{/if}

							{#if reindexMessage}
								<div class="alert alert-success">
									<CheckCircle class="w-5 h-5" />
									<span>{reindexMessage}</span>
								</div>
							{/if}

							{#if reindexError}
								<div class="alert alert-error">
									<AlertCircle class="w-5 h-5" />
									<span>{reindexError}</span>
								</div>
							{/if}

							<div class="maintenance-actions">
								{#if !searchIndexStatus?.fts_enabled}
									<button
										class="btn btn-primary"
										on:click={runMigration}
										disabled={isReindexing}
									>
										<Database class="w-4 h-4" />
										{isReindexing
											? "Running..."
											: "Initialize Search Index"}
									</button>
									<p class="form-hint">
										This will create the full-text search
										index and populate it with your comics.
										This is a one-time operation required
										for advanced search features.
									</p>
								{:else}
									<button
										class="btn btn-secondary"
										on:click={reindexSearch}
										disabled={isReindexing}
									>
										<RotateCw
											class="w-4 h-4 {isReindexing
												? 'animate-spin'
												: ''}"
										/>
										{isReindexing
											? "Reindexing..."
											: "Rebuild Search Index"}
									</button>
									<p class="form-hint">
										Rebuild the search index from scratch.
										This may take several minutes for large
										libraries. Use this if search results
										seem incomplete or incorrect.
									</p>

									<button
										class="btn btn-secondary"
										on:click={loadSearchIndexStatus}
									>
										<RotateCw class="w-4 h-4" />
										Refresh Status
									</button>
								{/if}
							</div>
						</div>
					</div>

					<div class="settings-section">
						<div class="section-header-simple">
							<h2 class="section-title">About Search Index</h2>
							<p class="section-description">
								How the advanced search works
							</p>
						</div>
						<div class="section-body">
							<div class="info-box">
								<h3
									class="text-lg font-semibold text-white mb-2"
								>
									What does this do?
								</h3>
								<ul class="space-y-2 text-gray-300">
									<li>
										• Creates a full-text search index for
										fast metadata queries
									</li>
									<li>
										• Indexes all comic metadata fields
										(title, writer, artist, genre, etc.)
									</li>
									<li>
										• Indexes dynamic scanner-specific
										metadata (parodies, circles, etc.)
									</li>
									<li>
										• Enables field-specific searches like
										"writer:Stan Lee"
									</li>
									<li>
										• Automatically stays in sync as you add
										or update comics
									</li>
								</ul>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Config File Info -->
			<div class="config-info">
				<p class="text-sm text-gray-400">
					Configuration file: <code class="code-inline"
						>{config.config_path}</code
					>
				</p>
			</div>
		{/if}
	</main>
</div>

<style>
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 2rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.header-title-section {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.icon-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 56px;
		height: 56px;
		background: var(--color-secondary-bg);
		border-radius: 12px;
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.page-subtitle {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0.25rem 0 0 0;
	}

	.action-buttons {
		display: flex;
		gap: 0.75rem;
	}

	.btn-primary,
	.btn-secondary,
	.btn-sm,
	.btn-icon-danger {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 1.25rem;
		border-radius: 6px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
		border: none;
		font-size: 0.875rem;
	}

	.btn-primary {
		background: var(--color-accent);
		color: white;
	}

	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: var(--color-secondary-bg);
		color: var(--color-text);
		border: 1px solid var(--color-border);
	}

	.btn-secondary:hover:not(:disabled) {
		border-color: var(--color-accent);
	}

	.btn-sm {
		padding: 0.4rem 0.75rem;
		font-size: 0.8rem;
		background: var(--color-secondary-bg);
		color: var(--color-text);
		border: 1px solid var(--color-border);
	}

	.btn-sm:hover {
		border-color: var(--color-accent);
	}

	.btn-icon-danger {
		padding: 0.25rem 0.5rem;
		background: transparent;
		color: #ef4444;
		border: 1px solid transparent;
		font-size: 1.25rem;
		line-height: 1;
	}

	.btn-icon-danger:hover {
		background: rgba(239, 68, 68, 0.1);
		border-color: #ef4444;
	}

	.alert {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
	}

	.alert-error {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid #ef4444;
		color: #fca5a5;
	}

	.alert-success {
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid #22c55e;
		color: #86efac;
	}

	.tabs {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
		border-bottom: 2px solid var(--color-border);
		overflow-x: auto;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.875rem 1.5rem;
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--color-text-secondary);
		cursor: pointer;
		transition: all 0.2s;
		white-space: nowrap;
		margin-bottom: -2px;
	}

	.tab:hover {
		color: var(--color-text);
	}

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
	}

	.tab-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.settings-section {
		padding: 2rem;
		background: var(--color-secondary-bg);
		border-radius: 12px;
		border: 1px solid var(--color-border);
	}

	.section-header-simple {
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--color-border);
	}

	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.5rem 0;
	}

	.section-description {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0;
		line-height: 1.5;
	}

	.section-body {
		/* Content goes here */
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: 1.5rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.form-group.full-width {
		grid-column: 1 / -1;
	}

	.form-group-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.form-group label {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text);
	}

	.form-group input[type="text"],
	.form-group input[type="number"],
	.form-group select {
		padding: 0.625rem 0.875rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		color: var(--color-text);
		font-size: 0.875rem;
		transition: border-color 0.2s;
	}

	.form-group input[type="text"]:focus,
	.form-group input[type="number"]:focus,
	.form-group select:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.form-hint {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin: 0;
		line-height: 1.4;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		cursor: pointer;
		font-size: 0.875rem;
		color: var(--color-text);
	}

	.checkbox-label input[type="checkbox"] {
		width: 18px;
		height: 18px;
		cursor: pointer;
	}

	.cors-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.cors-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: 6px;
	}

	.cors-item input {
		flex: 1;
		padding: 0.5rem;
		background: transparent;
		border: none;
		color: var(--color-text);
		font-size: 0.875rem;
	}

	.cors-item input:focus {
		outline: none;
	}

	.features-grid {
		display: grid;
		gap: 1rem;
	}

	.feature-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.25rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		transition: border-color 0.2s;
	}

	.feature-item:hover {
		border-color: var(--color-accent);
	}

	.feature-info {
		flex: 1;
	}

	.feature-title {
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.25rem 0;
	}

	.feature-description {
		font-size: 0.8125rem;
		color: var(--color-text-secondary);
		margin: 0;
	}

	/* Toggle Switch */
	.toggle {
		position: relative;
		display: inline-block;
		width: 48px;
		height: 24px;
		flex-shrink: 0;
	}

	.toggle input {
		opacity: 0;
		width: 0;
		height: 0;
	}

	.toggle-slider {
		position: absolute;
		cursor: pointer;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: var(--color-border);
		transition: 0.3s;
		border-radius: 24px;
	}

	.toggle-slider:before {
		position: absolute;
		content: "";
		height: 18px;
		width: 18px;
		left: 3px;
		bottom: 3px;
		background-color: white;
		transition: 0.3s;
		border-radius: 50%;
	}

	.toggle input:checked + .toggle-slider {
		background-color: var(--color-accent);
	}

	.toggle input:checked + .toggle-slider:before {
		transform: translateX(24px);
	}

	.config-info {
		margin-top: 2rem;
		padding: 1rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
		border: 1px solid var(--color-border);
	}

	.code-inline {
		padding: 0.125rem 0.375rem;
		background: var(--color-bg);
		border-radius: 4px;
		font-family: "Courier New", monospace;
		font-size: 0.8125rem;
		color: var(--color-accent);
	}

	.loading-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
	}

	.spinner {
		width: 64px;
		height: 64px;
		border: 4px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	.spinner-small {
		width: 16px;
		height: 16px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Maintenance tab styles */
	.status-card {
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 1.5rem;
	}

	.status-item {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.5rem;
		border-radius: 6px;
	}

	.status-item.success {
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid rgba(34, 197, 94, 0.3);
		color: #86efac;
	}

	.status-item.warning {
		background: rgba(251, 146, 60, 0.1);
		border: 1px solid rgba(251, 146, 60, 0.3);
		color: #fdba74;
	}

	.status-item.error {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.3);
		color: #fca5a5;
	}

	.status-text {
		flex: 1;
	}

	.maintenance-actions {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.alert {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		border-radius: 6px;
		margin-bottom: 1rem;
	}

	.alert-success {
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid rgba(34, 197, 94, 0.3);
		color: #86efac;
	}

	.alert-error {
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.3);
		color: #fca5a5;
	}

	.info-box {
		background: rgba(59, 130, 246, 0.1);
		border: 1px solid rgba(59, 130, 246, 0.3);
		border-radius: 8px;
		padding: 1.5rem;
	}

	@media (max-width: 768px) {
		.page-title {
			font-size: 1.5rem;
		}

		.icon-wrapper {
			width: 48px;
			height: 48px;
		}

		.settings-section {
			padding: 1.5rem;
		}

		.form-grid {
			grid-template-columns: 1fr;
		}

		.action-buttons {
			width: 100%;
		}

		.btn-primary,
		.btn-secondary {
			flex: 1;
			justify-content: center;
		}
	}
</style>
