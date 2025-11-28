<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import {
		X,
		Search,
		Plus,
		Trash2,
		Save,
		Clock,
		Star,
		BookmarkPlus,
		HelpCircle,
		Filter
	} from 'lucide-svelte';
	import {
		activeFilters,
		searchableFields,
		searchHistory,
		savedSearches,
		buildQueryFromFilters,
		parseQueryToFilters
	} from '$lib/stores/advancedSearch';
	import { getSearchableFields, parseSearchQuery } from '$lib/api/search';

	export let libraryId = null;
	export let initialQuery = '';
	export let onClose = () => {};

	const dispatch = createEventDispatcher();

	let queryText = initialQuery;
	let filters = parseQueryToFilters(initialQuery);
	let parsedQuery = null;
	let showSaveDialog = false;
	let saveName = '';
	let selectedTab = 'builder'; // 'builder', 'history', 'saved'

	// Available fields
	let availableFields = [];
	let fieldOptions = {};

	onMount(async () => {
		// Load searchable fields
		if (libraryId && !$searchableFields) {
			try {
				const fields = await getSearchableFields(libraryId);
				searchableFields.set(fields);
				availableFields = Object.keys(fields.standard_fields || {});
				fieldOptions = fields.standard_fields || {};
			} catch (err) {
				console.error('Failed to load searchable fields:', err);
			}
		} else if ($searchableFields) {
			availableFields = Object.keys($searchableFields.standard_fields || {});
			fieldOptions = $searchableFields.standard_fields || {};
		}

		// Parse initial query if provided
		if (initialQuery) {
			await updateParsedQuery(initialQuery);
		}
	});

	async function updateParsedQuery(query) {
		if (!query || !query.trim()) {
			parsedQuery = null;
			return;
		}

		try {
			parsedQuery = await parseSearchQuery(query);
		} catch (err) {
			console.error('Failed to parse query:', err);
			parsedQuery = null;
		}
	}

	function addFieldFilter() {
		// Add empty field filter
		if (!filters.fields) filters.fields = {};
		// Find first unused field
		const unusedField = availableFields.find(f => !(f in filters.fields));
		if (unusedField) {
			filters.fields[unusedField] = '';
		}
		filters = filters; // Trigger reactivity
	}

	function removeFieldFilter(field) {
		delete filters.fields[field];
		filters = filters;
		updateQueryText();
	}

	function updateQueryText() {
		queryText = buildQueryFromFilters(filters);
		updateParsedQuery(queryText);
	}

	function handleSearch() {
		const query = queryText.trim();
		if (!query) return;

		// Add to history
		searchHistory.add(query);

		// Dispatch search event
		dispatch('search', { query });

		onClose();
	}

	function loadFromHistory(historyItem) {
		queryText = historyItem.query;
		filters = parseQueryToFilters(historyItem.query);
		updateParsedQuery(queryText);
	}

	function loadSavedSearch(search) {
		queryText = search.query;
		filters = search.filters || parseQueryToFilters(search.query);
		updateParsedQuery(queryText);
	}

	function saveCurrentSearch() {
		if (!saveName.trim()) return;

		savedSearches.save(saveName, queryText, filters);
		showSaveDialog = false;
		saveName = '';
	}

	function clearHistory() {
		if (confirm('Clear all search history?')) {
			searchHistory.clear();
		}
	}

	function removeSaved(id) {
		if (confirm('Remove this saved search?')) {
			savedSearches.remove(id);
		}
	}

	// Reactive: Update query text when filters change
	$: if (filters) {
		queryText = buildQueryFromFilters(filters);
		updateParsedQuery(queryText);
	}
</script>

<div class="modal-overlay" on:click={onClose}>
	<div class="modal-content" on:click|stopPropagation>
		<!-- Header -->
		<div class="modal-header">
			<div class="header-title">
				<Search class="w-6 h-6 text-accent-orange" />
				<h2>Advanced Search</h2>
			</div>
			<button class="close-btn" on:click={onClose}>
				<X class="w-5 h-5" />
			</button>
		</div>

		<!-- Tabs -->
		<div class="tabs">
			<button
				class="tab"
				class:active={selectedTab === 'builder'}
				on:click={() => (selectedTab = 'builder')}
			>
				<Filter class="w-4 h-4" />
				<span>Query Builder</span>
			</button>
			<button
				class="tab"
				class:active={selectedTab === 'history'}
				on:click={() => (selectedTab = 'history')}
			>
				<Clock class="w-4 h-4" />
				<span>History</span>
				{#if $searchHistory.length > 0}
					<span class="badge">{$searchHistory.length}</span>
				{/if}
			</button>
			<button
				class="tab"
				class:active={selectedTab === 'saved'}
				on:click={() => (selectedTab = 'saved')}
			>
				<Star class="w-4 h-4" />
				<span>Saved</span>
				{#if $savedSearches.length > 0}
					<span class="badge">{$savedSearches.length}</span>
				{/if}
			</button>
		</div>

		<!-- Content -->
		<div class="modal-body">
			{#if selectedTab === 'builder'}
				<!-- Query Builder -->
				<div class="builder-section">
					<!-- Query Preview -->
					<div class="query-preview">
						<label>Search Query</label>
						<input
							type="text"
							bind:value={queryText}
							on:input={() => updateParsedQuery(queryText)}
							placeholder="Enter search query or use builder below..."
							class="query-input"
						/>
						{#if parsedQuery}
							<div class="query-info">
								{#if parsedQuery.field_queries && Object.keys(parsedQuery.field_queries).length > 0}
									<span class="info-label">Fields:</span>
									{#each Object.entries(parsedQuery.field_queries) as [field, values]}
										<span class="info-chip">{field}: {values.join(', ')}</span>
									{/each}
								{/if}
								{#if parsedQuery.general_terms && parsedQuery.general_terms.length > 0}
									<span class="info-label">General:</span>
									{#each parsedQuery.general_terms as term}
										<span class="info-chip">{term}</span>
									{/each}
								{/if}
							</div>
						{/if}
					</div>

					<!-- Field Filters -->
					<div class="field-filters">
						<div class="section-header">
							<h3>Search By Field</h3>
							<button class="btn-icon" on:click={addFieldFilter} title="Add field filter">
								<Plus class="w-4 h-4" />
							</button>
						</div>

						{#if filters.fields && Object.keys(filters.fields).length > 0}
							<div class="filter-list">
								{#each Object.entries(filters.fields) as [field, value]}
									<div class="filter-item">
										<select
											bind:value={filters.fields[field]}
											on:change={updateQueryText}
											class="field-select"
										>
											{#each availableFields as fieldOption}
												<option value={fieldOption}>{fieldOption}</option>
											{/each}
										</select>
										<input
											type="text"
											bind:value={filters.fields[field]}
											on:input={updateQueryText}
											placeholder={fieldOptions[field]?.example || 'Value...'}
											class="field-input"
										/>
										<button
											class="btn-icon-danger"
											on:click={() => removeFieldFilter(field)}
											title="Remove filter"
										>
											<Trash2 class="w-4 h-4" />
										</button>
									</div>
								{/each}
							</div>
						{:else}
							<p class="empty-message">
								No field filters. Click <Plus class="inline w-4 h-4" /> to add one.
							</p>
						{/if}
					</div>

					<!-- Help Section -->
					<div class="help-section">
						<div class="help-header">
							<HelpCircle class="w-4 h-4" />
							<span>Query Syntax</span>
						</div>
						<div class="help-content">
							<div class="help-item">
								<code>batman</code>
								<span>Search all fields for "batman"</span>
							</div>
							<div class="help-item">
								<code>writer:Stan Lee</code>
								<span>Search specific field</span>
							</div>
							<div class="help-item">
								<code>writer:"Frank Miller"</code>
								<span>Multi-word values (quoted)</span>
							</div>
							<div class="help-item">
								<code>-tag:nsfw</code>
								<span>Exclude results with this tag</span>
							</div>
							<div class="help-item">
								<code>writer:Stan genre:superhero</code>
								<span>Combine multiple fields</span>
							</div>
						</div>
					</div>
				</div>
			{:else if selectedTab === 'history'}
				<!-- Search History -->
				<div class="history-section">
					{#if $searchHistory.length > 0}
						<div class="section-actions">
							<button class="btn-secondary-small" on:click={clearHistory}>
								<Trash2 class="w-4 h-4" />
								Clear History
							</button>
						</div>
						<div class="history-list">
							{#each $searchHistory as item}
								<div class="history-item">
									<button class="history-query" on:click={() => loadFromHistory(item)}>
										<Clock class="w-4 h-4 text-gray-400" />
										<span class="query-text">{item.query}</span>
										<span class="timestamp">
											{new Date(item.timestamp).toLocaleDateString()}
										</span>
									</button>
									<button
										class="btn-icon-danger"
										on:click={() => searchHistory.remove(item.query)}
									>
										<X class="w-4 h-4" />
									</button>
								</div>
							{/each}
						</div>
					{:else}
						<div class="empty-state">
							<Clock class="w-12 h-12 text-gray-600" />
							<p>No search history yet</p>
							<p class="text-sm text-gray-500">Your recent searches will appear here</p>
						</div>
					{/if}
				</div>
			{:else if selectedTab === 'saved'}
				<!-- Saved Searches -->
				<div class="saved-section">
					{#if $savedSearches.length > 0}
						<div class="saved-list">
							{#each $savedSearches as saved}
								<div class="saved-item">
									<button class="saved-query" on:click={() => loadSavedSearch(saved)}>
										<Star class="w-4 h-4 text-accent-orange" />
										<div class="saved-info">
											<span class="saved-name">{saved.name}</span>
											<span class="saved-query-text">{saved.query}</span>
										</div>
									</button>
									<button class="btn-icon-danger" on:click={() => removeSaved(saved.id)}>
										<Trash2 class="w-4 h-4" />
									</button>
								</div>
							{/each}
						</div>
					{:else}
						<div class="empty-state">
							<Star class="w-12 h-12 text-gray-600" />
							<p>No saved searches yet</p>
							<p class="text-sm text-gray-500">
								Save frequently used searches for quick access
							</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Footer Actions -->
		<div class="modal-footer">
			<div class="footer-left">
				{#if selectedTab === 'builder' && queryText.trim()}
					<button class="btn-secondary" on:click={() => (showSaveDialog = true)}>
						<BookmarkPlus class="w-4 h-4" />
						Save Search
					</button>
				{/if}
			</div>
			<div class="footer-right">
				<button class="btn-secondary" on:click={onClose}>Cancel</button>
				<button
					class="btn-primary"
					on:click={handleSearch}
					disabled={!queryText.trim()}
				>
					<Search class="w-4 h-4" />
					Search
				</button>
			</div>
		</div>
	</div>
</div>

<!-- Save Dialog -->
{#if showSaveDialog}
	<div class="modal-overlay" on:click={() => (showSaveDialog = false)}>
		<div class="save-dialog" on:click|stopPropagation>
			<h3>Save Search</h3>
			<input
				type="text"
				bind:value={saveName}
				placeholder="Enter name for this search..."
				class="save-input"
				on:keydown={(e) => e.key === 'Enter' && saveCurrentSearch()}
			/>
			<div class="save-actions">
				<button class="btn-secondary" on:click={() => (showSaveDialog = false)}>
					Cancel
				</button>
				<button class="btn-primary" on:click={saveCurrentSearch} disabled={!saveName.trim()}>
					<Save class="w-4 h-4" />
					Save
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.75);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 1rem;
	}

	.modal-content {
		background: var(--color-bg-secondary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		max-width: 800px;
		width: 100%;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.5rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.header-title h2 {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-text-primary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.close-btn:hover {
		background: rgba(255, 255, 255, 0.1);
		color: var(--color-text-primary);
	}

	.tabs {
		display: flex;
		gap: 0.5rem;
		padding: 1rem 1.5rem 0;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	}

	.tab {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.75rem 1rem;
		border-radius: 6px 6px 0 0;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		font-weight: 500;
		transition: all 0.2s;
		position: relative;
	}

	.tab:hover {
		background: rgba(255, 255, 255, 0.05);
		color: var(--color-text-primary);
	}

	.tab.active {
		background: rgba(255, 121, 63, 0.1);
		color: var(--color-accent-orange);
		border-bottom: 2px solid var(--color-accent-orange);
	}

	.badge {
		background: var(--color-accent-orange);
		color: white;
		font-size: 0.75rem;
		padding: 0.125rem 0.5rem;
		border-radius: 10px;
		font-weight: 600;
	}

	.modal-body {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
	}

	.builder-section {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.query-preview {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.query-preview label {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--color-text-primary);
	}

	.query-input {
		width: 100%;
		padding: 0.75rem;
		background: var(--color-bg-tertiary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: var(--color-text-primary);
		font-size: 1rem;
		font-family: 'Courier New', monospace;
	}

	.query-input:focus {
		outline: none;
		border-color: var(--color-accent-orange);
		box-shadow: 0 0 0 3px rgba(255, 121, 63, 0.1);
	}

	.query-info {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		padding: 0.75rem;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.info-label {
		color: var(--color-text-secondary);
		font-weight: 600;
	}

	.info-chip {
		background: var(--color-accent-orange);
		color: white;
		padding: 0.25rem 0.75rem;
		border-radius: 12px;
		font-size: 0.875rem;
		font-family: 'Courier New', monospace;
	}

	.field-filters {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.section-header h3 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-text-primary);
	}

	.btn-icon {
		background: var(--color-accent-orange);
		border: none;
		color: white;
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.btn-icon:hover {
		background: var(--color-accent-orange-hover);
		transform: scale(1.05);
	}

	.filter-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.filter-item {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}

	.field-select {
		flex: 0 0 150px;
		padding: 0.5rem;
		background: var(--color-bg-tertiary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: var(--color-text-primary);
		font-size: 0.9rem;
	}

	.field-input {
		flex: 1;
		padding: 0.5rem;
		background: var(--color-bg-tertiary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: var(--color-text-primary);
		font-size: 0.9rem;
	}

	.field-input:focus,
	.field-select:focus {
		outline: none;
		border-color: var(--color-accent-orange);
	}

	.btn-icon-danger {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.btn-icon-danger:hover {
		background: rgba(239, 68, 68, 0.1);
		color: #f87171;
	}

	.empty-message {
		text-align: center;
		color: var(--color-text-secondary);
		padding: 1rem;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.help-section {
		background: rgba(59, 130, 246, 0.1);
		border: 1px solid rgba(59, 130, 246, 0.3);
		border-radius: 8px;
		padding: 1rem;
	}

	.help-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #60a5fa;
		font-weight: 600;
		margin-bottom: 0.75rem;
	}

	.help-content {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.help-item {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		font-size: 0.875rem;
	}

	.help-item code {
		background: rgba(0, 0, 0, 0.3);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-family: 'Courier New', monospace;
		color: #60a5fa;
		flex: 0 0 200px;
	}

	.help-item span {
		color: var(--color-text-secondary);
		flex: 1;
	}

	.history-section,
	.saved-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.section-actions {
		display: flex;
		justify-content: flex-end;
	}

	.btn-secondary-small {
		background: rgba(255, 255, 255, 0.1);
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		transition: all 0.2s;
	}

	.btn-secondary-small:hover {
		background: rgba(255, 255, 255, 0.15);
		color: var(--color-text-primary);
	}

	.history-list,
	.saved-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.history-item,
	.saved-item {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		padding: 0.75rem;
		transition: all 0.2s;
	}

	.history-item:hover,
	.saved-item:hover {
		background: rgba(255, 255, 255, 0.08);
		border-color: rgba(255, 255, 255, 0.2);
	}

	.history-query,
	.saved-query {
		flex: 1;
		background: none;
		border: none;
		color: var(--color-text-primary);
		cursor: pointer;
		text-align: left;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0;
	}

	.query-text {
		flex: 1;
		font-family: 'Courier New', monospace;
		font-size: 0.9rem;
	}

	.timestamp {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.saved-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.saved-name {
		font-weight: 600;
		color: var(--color-text-primary);
	}

	.saved-query-text {
		font-size: 0.875rem;
		font-family: 'Courier New', monospace;
		color: var(--color-text-secondary);
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 3rem 1rem;
		gap: 0.75rem;
		text-align: center;
	}

	.empty-state p {
		margin: 0;
		color: var(--color-text-secondary);
	}

	.modal-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.5rem;
		border-top: 1px solid rgba(255, 255, 255, 0.1);
		gap: 1rem;
	}

	.footer-left,
	.footer-right {
		display: flex;
		gap: 0.75rem;
	}

	.btn-secondary,
	.btn-primary {
		padding: 0.75rem 1.5rem;
		border-radius: 6px;
		font-size: 1rem;
		font-weight: 500;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		transition: all 0.2s;
		border: none;
	}

	.btn-secondary {
		background: rgba(255, 255, 255, 0.1);
		color: var(--color-text-primary);
	}

	.btn-secondary:hover {
		background: rgba(255, 255, 255, 0.15);
	}

	.btn-primary {
		background: var(--color-accent-orange);
		color: white;
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--color-accent-orange-hover);
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.save-dialog {
		background: var(--color-bg-secondary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 12px;
		padding: 1.5rem;
		max-width: 400px;
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.save-dialog h3 {
		margin: 0;
		font-size: 1.25rem;
		color: var(--color-text-primary);
	}

	.save-input {
		width: 100%;
		padding: 0.75rem;
		background: var(--color-bg-tertiary);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		color: var(--color-text-primary);
		font-size: 1rem;
	}

	.save-input:focus {
		outline: none;
		border-color: var(--color-accent-orange);
	}

	.save-actions {
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
	}

	.inline {
		display: inline;
		vertical-align: middle;
	}

	@media (max-width: 768px) {
		.modal-content {
			max-height: 95vh;
		}

		.filter-item {
			flex-direction: column;
		}

		.field-select,
		.field-input {
			flex: 1;
			width: 100%;
		}

		.help-item {
			flex-direction: column;
			gap: 0.25rem;
		}

		.help-item code {
			flex: none;
			width: 100%;
		}

		.modal-footer {
			flex-direction: column;
			align-items: stretch;
		}

		.footer-left,
		.footer-right {
			width: 100%;
			justify-content: stretch;
		}

		.btn-secondary,
		.btn-primary {
			flex: 1;
			justify-content: center;
		}
	}
</style>
