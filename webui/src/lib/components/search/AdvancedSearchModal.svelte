<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import {
		X,
		Search,
		Save,
		Clock,
		Star,
		Tag,
		RotateCcw
	} from 'lucide-svelte';
	import { getSearchValues } from '$lib/api/search';
	import {
		searchHistory,
		savedSearches
	} from '$lib/stores/advancedSearch';

	export let libraryId = null;
	export let initialQuery = '';
	export let onClose = () => {};

	const dispatch = createEventDispatcher();

	// ── Field definitions grouped by category ──────────────────────────────
	const FIELD_GROUPS = [
		{
			label: 'Content',
			fields: [
				{ key: 'title',       label: 'Title',       type: 'chips', placeholder: 'e.g. Dark Knight' },
				{ key: 'series',      label: 'Series',      type: 'chips', placeholder: 'e.g. Batman' },
				{ key: 'description', label: 'Description', type: 'chips', placeholder: 'Keyword in description' },
				{ key: 'story_arc',   label: 'Story Arc',   type: 'chips', placeholder: 'e.g. Civil War' },
				{ key: 'characters',  label: 'Characters',  type: 'chips', placeholder: 'e.g. Spider-Man' },
				{ key: 'teams',       label: 'Teams',       type: 'chips', placeholder: 'e.g. Avengers' },
				{ key: 'locations',   label: 'Locations',   type: 'chips', placeholder: 'e.g. Gotham' },
			]
		},
		{
			label: 'Creators',
			fields: [
				{ key: 'writer',       label: 'Writer',        type: 'chips', placeholder: 'e.g. Stan Lee' },
				{ key: 'artist',       label: 'Artist',        type: 'chips', placeholder: 'e.g. Jack Kirby' },
				{ key: 'penciller',    label: 'Penciller',     type: 'chips', placeholder: '' },
				{ key: 'inker',        label: 'Inker',         type: 'chips', placeholder: '' },
				{ key: 'colorist',     label: 'Colorist',      type: 'chips', placeholder: '' },
				{ key: 'letterer',     label: 'Letterer',      type: 'chips', placeholder: '' },
				{ key: 'cover_artist', label: 'Cover Artist',  type: 'chips', placeholder: '' },
				{ key: 'editor',       label: 'Editor',        type: 'chips', placeholder: '' },
			]
		},
		{
			label: 'Classification',
			fields: [
				{ key: 'publisher',    label: 'Publisher',    type: 'chips', placeholder: 'e.g. Marvel' },
				{ key: 'imprint',      label: 'Imprint',      type: 'chips', placeholder: 'e.g. Vertigo' },
				{ key: 'genre',        label: 'Genre',        type: 'chips', placeholder: 'e.g. superhero' },
				{ key: 'tags',         label: 'Tags',         type: 'chips', placeholder: 'e.g. action' },
				{ key: 'age_rating',   label: 'Age Rating',   type: 'select',
				  options: ['', 'Unknown', 'Adults Only 18+', 'Early Childhood', 'Everyone', 'Everyone 10+', 'G', 'Kids to Adults', 'M', 'MA15+', 'Mature 17+', 'PG', 'R18+', 'Rating Pending', 'Teen', 'X18+'] },
				{ key: 'format_type',  label: 'Format',       type: 'select',
				  options: ['', 'Single Issue', 'TPB', 'HC', 'Omnibus', 'Annual', 'Special', 'One-Shot', 'GN', 'Digital'] },
				{ key: 'language_iso', label: 'Language',     type: 'chips', placeholder: 'e.g. en, ja, fr' },
			]
		},
		{
			label: 'Source',
			fields: [
				{ key: 'scanner_source', label: 'Scanner Source', type: 'chips', placeholder: 'e.g. nhentai, anilist' },
				{ key: 'series_group',   label: 'Series Group',   type: 'chips', placeholder: '' },
			]
		},
	];

	const FIELD_DEFS = Object.fromEntries(
		FIELD_GROUPS.flatMap((group) => group.fields.map((field) => [field.key, field]))
	);

	const SUGGESTABLE_FIELDS = new Set([
		'title',
		'series',
		'story_arc',
		'writer',
		'artist',
		'penciller',
		'inker',
		'colorist',
		'letterer',
		'cover_artist',
		'editor',
		'publisher',
		'imprint',
		'genre',
		'tags',
		'characters',
		'teams',
		'locations',
		'language_iso',
		'scanner_source',
		'series_group'
	]);

	// ── State ───────────────────────────────────────────────────────────────
	let selectedTab = 'builder'; // 'builder' | 'history' | 'saved'

	// chips: { [fieldKey]: string[] }
	let chips = {};
	// select-type values: { [fieldKey]: string }
	let selects = {};
	// general text (no field:value prefix)
	let generalText = '';

	// year / rating range
	let yearMin = '';
	let yearMax = '';
	let ratingMin = '';
	let ratingMax = '';

	// per-field text inputs (before they become chips)
	let inputValues = {};
	// which field's dropdown is open
	let openField = null;
	let activeBrowseField = 'tags';
	let fieldSuggestions = {};
	let browseValues = {};
	let loadingSuggestions = {};
	let loadingBrowseValues = {};

	let showSaveDialog = false;
	let saveName = '';

	// ── Init from initialQuery ───────────────────────────────────────────────
	let builtQuery = '';
	$: {
		const parts = [];
		if (generalText.trim()) parts.push(generalText.trim());
		for (const [field, vals] of Object.entries(chips)) {
			for (const v of vals) {
				if (!v) continue;
				const quoted = v.includes(' ') ? `"${v}"` : v;
				parts.push(`${field}:${quoted}`);
			}
		}
		for (const [field, val] of Object.entries(selects)) {
			if (val) parts.push(`${field}:${val}`);
		}
		if (yearMin) parts.push(`year:>=${yearMin}`);
		if (yearMax) parts.push(`year:<=${yearMax}`);
		if (ratingMin) parts.push(`rating:>=${ratingMin}`);
		if (ratingMax) parts.push(`rating:<=${ratingMax}`);
		builtQuery = parts.join(' ');
	}

	function parseInitial(q) {
		if (!q) return;
		const fieldPattern = /(-?)(\w+):(?:"([^"]+)"|'([^']+)'|(\S+))/g;
		let match;
		let covered = new Set();
		while ((match = fieldPattern.exec(q)) !== null) {
			const [full, excl, field, v1, v2, v3] = match;
			const val = v1 || v2 || v3;
			for (let i = match.index; i < match.index + full.length; i++) covered.add(i);
			if (excl) continue; // skip negations for now
			// check if it's a known select field
			const allFields = FIELD_GROUPS.flatMap(g => g.fields);
			const def = allFields.find(f => f.key === field);
			if (def?.type === 'select') {
				selects[field] = val;
			} else {
				if (!chips[field]) chips[field] = [];
				if (!chips[field].includes(val)) chips[field].push(val);
			}
		}
		let rest = '';
		for (let i = 0; i < q.length; i++) {
			if (!covered.has(i)) rest += q[i];
		}
		generalText = rest.trim();
		chips = chips;
		selects = selects;
	}

	onMount(async () => {
		parseInitial(initialQuery);
		if (isSuggestableField(activeBrowseField)) {
			await loadBrowseValues(activeBrowseField);
		}
	});

	// ── Chip management ──────────────────────────────────────────────────────
	function addChip(fieldKey) {
		const raw = (inputValues[fieldKey] || '').trim();
		if (!raw) return;
		addChipValue(fieldKey, raw);
	}

	function addChipValue(fieldKey, rawValue) {
		const raw = (rawValue || '').trim();
		if (!raw) return;
		if (!chips[fieldKey]) chips[fieldKey] = [];
		if (!chips[fieldKey].includes(raw)) {
			chips[fieldKey] = [...chips[fieldKey], raw];
		}
		inputValues[fieldKey] = '';
		inputValues = inputValues;
		chips = chips;
		fieldSuggestions = { ...fieldSuggestions, [fieldKey]: [] };
		openField = null;
	}

	function removeChip(fieldKey, val) {
		chips[fieldKey] = chips[fieldKey].filter(v => v !== val);
		chips = chips;
	}

	function toggleChipValue(fieldKey, rawValue) {
		const values = chips[fieldKey] || [];
		if (values.includes(rawValue)) {
			removeChip(fieldKey, rawValue);
			return;
		}
		addChipValue(fieldKey, rawValue);
	}

	function isSuggestableField(fieldKey) {
		return SUGGESTABLE_FIELDS.has(fieldKey);
	}

	function getFieldLabel(fieldKey) {
		return FIELD_DEFS[fieldKey]?.label || fieldKey;
	}

	function getFieldSuggestions(fieldKey) {
		return fieldSuggestions[fieldKey] || [];
	}

	function getBrowseValues(fieldKey) {
		return browseValues[fieldKey] || [];
	}

	function isLoadingSuggestionsForField(fieldKey) {
		return Boolean(loadingSuggestions[fieldKey]);
	}

	function isLoadingBrowseField(fieldKey) {
		return Boolean(loadingBrowseValues[fieldKey]);
	}

	async function loadBrowseValues(fieldKey) {
		if (!isSuggestableField(fieldKey)) return;
		try {
			loadingBrowseValues = { ...loadingBrowseValues, [fieldKey]: true };
			const response = await getSearchValues({ field: fieldKey, libraryId, limit: 40 });
			browseValues = { ...browseValues, [fieldKey]: response.values || [] };
		} catch (error) {
			console.error(`Failed to load browseable values for ${fieldKey}:`, error);
			browseValues = { ...browseValues, [fieldKey]: [] };
		} finally {
			loadingBrowseValues = { ...loadingBrowseValues, [fieldKey]: false };
		}
	}

	async function loadFieldSuggestions(fieldKey, query) {
		if (!isSuggestableField(fieldKey)) return;
		const normalized = (query || '').trim();
		if (!normalized) {
			fieldSuggestions = {
				...fieldSuggestions,
				[fieldKey]: getBrowseValues(fieldKey)
					.filter((item) => !((chips[fieldKey] || []).includes(item.name)))
					.slice(0, 8)
			};
			return;
		}

		try {
			loadingSuggestions = { ...loadingSuggestions, [fieldKey]: true };
			const response = await getSearchValues({ field: fieldKey, libraryId, query: normalized, limit: 10 });
			fieldSuggestions = {
				...fieldSuggestions,
				[fieldKey]: (response.values || []).filter(
					(item) => !((chips[fieldKey] || []).includes(item.name))
				)
			};
		} catch (error) {
			console.error(`Failed to load suggestions for ${fieldKey}:`, error);
			fieldSuggestions = { ...fieldSuggestions, [fieldKey]: [] };
		} finally {
			loadingSuggestions = { ...loadingSuggestions, [fieldKey]: false };
		}
	}

	function handleInputChange(fieldKey, value) {
		inputValues[fieldKey] = value;
		inputValues = inputValues;

		if (isSuggestableField(fieldKey)) {
			loadFieldSuggestions(fieldKey, value);
		}
	}

	function addSuggestedValue(fieldKey, value) {
		addChipValue(fieldKey, value);
	}

	function toggleSuggestedValue(fieldKey, value) {
		toggleChipValue(fieldKey, value);
	}

	function handleChipKeydown(e, fieldKey) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addChip(fieldKey);
		} else if (e.key === 'Backspace' && !inputValues[fieldKey] && chips[fieldKey]?.length) {
			chips[fieldKey] = chips[fieldKey].slice(0, -1);
			chips = chips;
		} else if (e.key === 'Escape') {
			openField = null;
		}
	}

	function clearAll() {
		chips = {};
		selects = {};
		generalText = '';
		yearMin = ''; yearMax = '';
		ratingMin = ''; ratingMax = '';
		inputValues = {};
		fieldSuggestions = {};
	}

	function hasAnyFilter() {
		if (generalText.trim()) return true;
		if (Object.values(chips).some(a => a.length > 0)) return true;
		if (Object.values(selects).some(v => v)) return true;
		if (yearMin || yearMax || ratingMin || ratingMax) return true;
		return false;
	}

	// ── Search / Save ────────────────────────────────────────────────────────
	function handleSearch() {
		const q = builtQuery.trim();
		if (!q) return;
		searchHistory.add(q);
		dispatch('search', { query: q });
		onClose();
	}

	function loadFromHistory(item) {
		clearAll();
		parseInitial(item.query);
		selectedTab = 'builder';
	}

	function loadSavedSearch(saved) {
		clearAll();
		parseInitial(saved.query);
		selectedTab = 'builder';
	}

	function saveCurrentSearch() {
		if (!saveName.trim()) return;
		savedSearches.save(saveName, builtQuery, {});
		showSaveDialog = false;
		saveName = '';
	}

	function clearHistory() {
		if (confirm('Clear all search history?')) searchHistory.clear();
	}

	function removeSaved(id) {
		if (confirm('Remove this saved search?')) savedSearches.remove(id);
	}
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	class="modal-overlay"
	on:click={onClose}
	on:keydown={(e) => e.key === 'Escape' && onClose()}
	role="presentation"
>
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-content"
		on:click|stopPropagation
		on:keydown={(e) => e.key === 'Escape' && onClose()}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
	>
		<!-- Header -->
		<div class="modal-header">
			<div class="header-title">
				<Search size={20} />
				<h2>Advanced Search</h2>
			</div>
			<div class="header-actions">
				{#if hasAnyFilter()}
					<button class="btn-ghost" on:click={clearAll} title="Clear all filters">
						<RotateCcw size={14} />
						<span>Reset</span>
					</button>
				{/if}
				<button class="close-btn" on:click={onClose} aria-label="Close">
					<X size={18} />
				</button>
			</div>
		</div>

		<!-- Tabs -->
		<div class="tabs">
			<button class="tab" class:active={selectedTab === 'builder'} on:click={() => (selectedTab = 'builder')}>
				<Search size={14} />
				<span>Filters</span>
			</button>
			<button class="tab" class:active={selectedTab === 'history'} on:click={() => (selectedTab = 'history')}>
				<Clock size={14} />
				<span>History</span>
				{#if $searchHistory.length > 0}
					<span class="badge">{$searchHistory.length}</span>
				{/if}
			</button>
			<button class="tab" class:active={selectedTab === 'saved'} on:click={() => (selectedTab = 'saved')}>
				<Star size={14} />
				<span>Saved</span>
				{#if $savedSearches.length > 0}
					<span class="badge">{$savedSearches.length}</span>
				{/if}
			</button>
		</div>

		<!-- Body -->
		<div class="modal-body">
			{#if selectedTab === 'builder'}
				<div class="builder-wrap">

					<!-- General keyword -->
					<div class="section-block">
						<label class="section-label" for="general-input">General Keywords</label>
						<input
							id="general-input"
							type="text"
							class="text-input"
							bind:value={generalText}
							placeholder="Search across all fields…"
						/>
					</div>

					<!-- Field Groups -->
					{#each FIELD_GROUPS as group}
						<div class="section-block">
							<div class="group-header">
								<span class="group-label">{group.label}</span>
							</div>
							<div class="fields-grid">
								{#each group.fields as field}
									<div class="field-row">
										<span class="field-label">{field.label}</span>
										{#if field.type === 'select'}
											<select
												class="field-select"
												bind:value={selects[field.key]}
												on:change={() => { selects = selects; }}
											>
												{#each field.options as opt}
													<option value={opt}>{opt || '— any —'}</option>
												{/each}
											</select>
										{:else}
											<!-- Chip input -->
											<div class="chip-box" on:click={() => { openField = field.key; }} role="button" tabindex="0" on:keydown={(e) => { if (e.key === 'Enter') openField = field.key; }}>
												{#if chips[field.key]}
													{#each chips[field.key] as chip}
														<span class="chip">
															{chip}
															<button
																class="chip-remove"
																type="button"
																on:click|stopPropagation={() => removeChip(field.key, chip)}
																aria-label="Remove {chip}"
															>×</button>
														</span>
													{/each}
												{/if}
												<input
													class="chip-input"
													type="text"
													placeholder={chips[field.key]?.length ? '' : field.placeholder}
													value={inputValues[field.key] || ''}
													on:input={(e) => handleInputChange(field.key, e.currentTarget.value)}
													on:keydown={(e) => handleChipKeydown(e, field.key)}
													on:focus={() => {
														openField = field.key;
														activeBrowseField = field.key;
														if (isSuggestableField(field.key)) {
															if (!browseValues[field.key]) loadBrowseValues(field.key);
															loadFieldSuggestions(field.key, inputValues[field.key] || '');
														}
													}}
													on:blur={() => { setTimeout(() => { openField = null; }, 150); }}
												/>
											</div>
											{#if isSuggestableField(field.key) && openField === field.key && (isLoadingSuggestionsForField(field.key) || getFieldSuggestions(field.key).length > 0)}
												<div class="tag-suggestions">
													{#if isLoadingSuggestionsForField(field.key)}
														<div class="tag-suggestion-empty">Loading {field.label.toLowerCase()}…</div>
													{:else}
														{#each getFieldSuggestions(field.key) as suggestion}
															<button
																type="button"
																class="tag-suggestion"
																on:mousedown|preventDefault={() => addSuggestedValue(field.key, suggestion.name)}
															>
																<span>{suggestion.name}</span>
																<span class="tag-suggestion-count">{suggestion.count}</span>
															</button>
														{/each}
													{/if}
												</div>
											{/if}
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/each}

					<div class="section-block">
						<div class="group-header">
							<span class="group-label browse-tags-title">
								<Tag size={14} />
								Browse {getFieldLabel(activeBrowseField)}
							</span>
						</div>
						{#if !isSuggestableField(activeBrowseField)}
							<div class="browse-tags-empty">Focus a searchable chip field to browse existing values.</div>
						{:else if isLoadingBrowseField(activeBrowseField)}
							<div class="browse-tags-empty">Loading available {getFieldLabel(activeBrowseField).toLowerCase()}…</div>
						{:else if getBrowseValues(activeBrowseField).length > 0}
							<div class="browse-tags-grid">
								{#each getBrowseValues(activeBrowseField) as item}
									<button
										type="button"
										class="browse-tag"
										class:selected={(chips[activeBrowseField] || []).includes(item.name)}
										on:click={() => toggleSuggestedValue(activeBrowseField, item.name)}
									>
										<span>{item.name}</span>
										<span class="browse-tag-count">{item.count}</span>
									</button>
								{/each}
							</div>
						{:else}
							<div class="browse-tags-empty">No {getFieldLabel(activeBrowseField).toLowerCase()} values found in indexed comics yet.</div>
						{/if}
					</div>

					<!-- Numeric Ranges -->
					<div class="section-block">
						<div class="group-header">
							<span class="group-label">Ranges</span>
						</div>
						<div class="ranges-grid">
							<div class="range-row">
								<span class="field-label">Year</span>
								<div class="range-inputs">
									<input type="number" class="range-input" bind:value={yearMin} placeholder="From" min="1900" max="2100" />
									<span class="range-sep">–</span>
									<input type="number" class="range-input" bind:value={yearMax} placeholder="To" min="1900" max="2100" />
								</div>
							</div>
							<div class="range-row">
								<span class="field-label">Rating</span>
								<div class="range-inputs">
									<input type="number" class="range-input" bind:value={ratingMin} placeholder="Min" min="0" max="5" step="0.5" />
									<span class="range-sep">–</span>
									<input type="number" class="range-input" bind:value={ratingMax} placeholder="Max" min="0" max="5" step="0.5" />
								</div>
							</div>
						</div>
					</div>

					<!-- Query preview -->
					{#if builtQuery.trim()}
						<div class="query-preview">
							<span class="preview-label">Query preview</span>
							<code class="preview-code">{builtQuery}</code>
						</div>
					{/if}

				</div>

			{:else if selectedTab === 'history'}
				<div class="list-section">
					{#if $searchHistory.length > 0}
						<div class="list-header">
							<button class="btn-ghost-sm" on:click={clearHistory}>
								<RotateCcw size={12} />
								Clear all
							</button>
						</div>
						<div class="entry-list">
							{#each $searchHistory as item}
								<div class="entry-row">
									<button class="entry-btn" on:click={() => loadFromHistory(item)}>
										<Clock size={14} class="entry-icon" />
										<span class="entry-query">{item.query}</span>
										<span class="entry-time">{new Date(item.timestamp).toLocaleDateString()}</span>
									</button>
									<button class="entry-del" on:click={() => searchHistory.remove(item.query)} aria-label="Remove">
										<X size={14} />
									</button>
								</div>
							{/each}
						</div>
					{:else}
						<div class="empty-state">
							<Clock size={40} />
							<p>No search history yet</p>
						</div>
					{/if}
				</div>

			{:else if selectedTab === 'saved'}
				<div class="list-section">
					{#if $savedSearches.length > 0}
						<div class="entry-list">
							{#each $savedSearches as saved}
								<div class="entry-row">
									<button class="entry-btn" on:click={() => loadSavedSearch(saved)}>
										<Star size={14} class="entry-icon accent" />
										<span class="entry-name">{saved.name}</span>
										<span class="entry-query dimmed">{saved.query}</span>
									</button>
									<button class="entry-del" on:click={() => removeSaved(saved.id)} aria-label="Remove">
										<X size={14} />
									</button>
								</div>
							{/each}
						</div>
					{:else}
						<div class="empty-state">
							<Star size={40} />
							<p>No saved searches yet</p>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="modal-footer">
			<div class="footer-left">
				{#if selectedTab === 'builder' && builtQuery.trim()}
					<button class="btn-secondary" on:click={() => (showSaveDialog = true)}>
						<Save size={14} />
						Save
					</button>
				{/if}
			</div>
			<div class="footer-right">
				<button class="btn-secondary" on:click={onClose}>Cancel</button>
				<button class="btn-primary" on:click={handleSearch} disabled={!builtQuery.trim()}>
					<Search size={14} />
					Search
				</button>
			</div>
		</div>
	</div>
</div>

<!-- Save Dialog -->
{#if showSaveDialog}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div class="modal-overlay" on:click={() => (showSaveDialog = false)} on:keydown={(e) => e.key === 'Escape' && (showSaveDialog = false)} role="presentation">
		<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
		<div class="save-dialog" on:click|stopPropagation on:keydown={(e) => e.key === 'Escape' && (showSaveDialog = false)} role="dialog" tabindex="-1">
			<h3>Save Search</h3>
			<input
				type="text"
				class="text-input"
				bind:value={saveName}
				placeholder="Name this search…"
				on:keydown={(e) => e.key === 'Enter' && saveCurrentSearch()}
			/>
			<div class="save-actions">
				<button class="btn-secondary" on:click={() => (showSaveDialog = false)}>Cancel</button>
				<button class="btn-primary" on:click={saveCurrentSearch} disabled={!saveName.trim()}>
					<Save size={14} />
					Save
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ── Overlay / Modal shell ─────────────────────────────────────────────── */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: var(--color-overlay, rgba(0,0,0,0.7));
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 1rem;
	}

	.modal-content {
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-border-strong);
		border-radius: 14px;
		width: min(860px, 100%);
		max-height: 92vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 24px 64px rgba(0,0,0,0.6);
		overflow: hidden;
	}

	/* ── Header ───────────────────────────────────────────────────────────── */
	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.125rem 1.25rem;
		border-bottom: 1px solid var(--color-border-strong);
		flex-shrink: 0;
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		color: var(--color-accent);
	}

	.header-title h2 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--color-text);
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.375rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		transition: background 0.15s, color 0.15s;
	}

	.close-btn:hover {
		background: var(--color-tertiary-bg);
		color: var(--color-text);
	}

	.btn-ghost {
		background: none;
		border: 1px solid var(--color-border);
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.3rem 0.65rem;
		border-radius: 6px;
		display: flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.8rem;
		transition: all 0.15s;
	}

	.btn-ghost:hover {
		border-color: var(--color-border-strong);
		color: var(--color-text);
	}

	/* ── Tabs ─────────────────────────────────────────────────────────────── */
	.tabs {
		display: flex;
		gap: 0.25rem;
		padding: 0.75rem 1.25rem 0;
		border-bottom: 1px solid var(--color-border-strong);
		flex-shrink: 0;
	}

	.tab {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.5rem 0.875rem;
		border-radius: 6px 6px 0 0;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.875rem;
		font-weight: 500;
		transition: all 0.15s;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
	}

	.tab:hover { color: var(--color-text); }

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
		background: color-mix(in srgb, var(--color-accent) 8%, transparent);
	}

	.badge {
		background: var(--color-accent);
		color: #fff;
		font-size: 0.7rem;
		padding: 0.1rem 0.4rem;
		border-radius: 8px;
		font-weight: 700;
		line-height: 1.4;
	}

	/* ── Body ─────────────────────────────────────────────────────────────── */
	.modal-body {
		flex: 1;
		overflow-y: auto;
		padding: 1.25rem;
	}

	.modal-body::-webkit-scrollbar { width: 6px; }
	.modal-body::-webkit-scrollbar-track { background: transparent; }
	.modal-body::-webkit-scrollbar-thumb {
		background: var(--color-border-strong);
		border-radius: 3px;
	}

	/* ── Builder ──────────────────────────────────────────────────────────── */
	.builder-wrap {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.section-block {
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}

	.section-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--color-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	.group-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding-bottom: 0.375rem;
		border-bottom: 1px solid var(--color-border);
	}

	.group-label {
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--color-text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.07em;
	}

	.browse-tags-title {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}

	.browse-tags-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.browse-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.45rem 0.7rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 999px;
		color: var(--color-text);
		font-size: 0.8rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.browse-tag:hover {
		border-color: var(--color-accent);
		background: color-mix(in srgb, var(--color-accent) 10%, var(--color-tertiary-bg));
	}

	.browse-tag.selected {
		border-color: color-mix(in srgb, var(--color-accent) 60%, transparent);
		background: color-mix(in srgb, var(--color-accent) 14%, var(--color-tertiary-bg));
		color: var(--color-accent);
	}

	.browse-tag-count {
		font-size: 0.72rem;
		color: var(--color-text-secondary);
	}

	.browse-tags-empty {
		padding: 0.75rem;
		background: var(--color-tertiary-bg);
		border: 1px dashed var(--color-border);
		border-radius: 8px;
		color: var(--color-text-secondary);
		font-size: 0.82rem;
	}

	.fields-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 0.5rem 1rem;
	}

	.field-row {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		position: relative;
	}

	.field-label {
		font-size: 0.78rem;
		font-weight: 500;
		color: var(--color-text-secondary);
	}

	/* ── Text Input ───────────────────────────────────────────────────────── */
	.text-input {
		width: 100%;
		padding: 0.5rem 0.75rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 7px;
		color: var(--color-text);
		font-size: 0.875rem;
		transition: border-color 0.15s, box-shadow 0.15s;
		box-sizing: border-box;
	}

	.text-input:focus {
		outline: none;
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent) 18%, transparent);
	}

	.text-input::placeholder { color: var(--color-text-secondary); opacity: 0.7; }

	/* ── Select ───────────────────────────────────────────────────────────── */
	.field-select {
		width: 100%;
		padding: 0.5rem 0.75rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 7px;
		color: var(--color-text);
		font-size: 0.875rem;
		cursor: pointer;
		transition: border-color 0.15s;
		appearance: none;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.6rem center;
		padding-right: 2rem;
	}

	.field-select:focus {
		outline: none;
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent) 18%, transparent);
	}

	/* ── Chip Box ─────────────────────────────────────────────────────────── */
	.chip-box {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem;
		min-height: 2rem;
		padding: 0.3rem 0.5rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 7px;
		cursor: text;
		transition: border-color 0.15s, box-shadow 0.15s;
	}

	.chip-box:focus-within {
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent) 18%, transparent);
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.2rem;
		background: color-mix(in srgb, var(--color-accent) 22%, transparent);
		color: var(--color-accent);
		border: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent);
		padding: 0.15rem 0.4rem 0.15rem 0.55rem;
		border-radius: 5px;
		font-size: 0.78rem;
		font-weight: 500;
		white-space: nowrap;
		max-width: 180px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.chip-remove {
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: 0;
		font-size: 0.95rem;
		line-height: 1;
		opacity: 0.7;
		transition: opacity 0.1s;
		flex-shrink: 0;
	}

	.chip-remove:hover { opacity: 1; }

	.chip-input {
		background: none;
		border: none;
		outline: none;
		color: var(--color-text);
		font-size: 0.8rem;
		min-width: 80px;
		flex: 1;
		padding: 0.1rem 0.2rem;
	}

	.chip-input::placeholder { color: var(--color-text-secondary); opacity: 0.6; }

	.tag-suggestions {
		position: absolute;
		top: calc(100% + 0.25rem);
		left: 0;
		right: 0;
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-border-strong);
		border-radius: 8px;
		box-shadow: 0 12px 24px rgba(0, 0, 0, 0.35);
		z-index: 20;
		overflow: hidden;
		max-height: 220px;
		overflow-y: auto;
	}

	.tag-suggestion,
	.tag-suggestion-empty {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 0.55rem 0.75rem;
		background: transparent;
		border: none;
		color: var(--color-text);
		font-size: 0.82rem;
		text-align: left;
	}

	.tag-suggestion {
		cursor: pointer;
		transition: background 0.15s;
	}

	.tag-suggestion:hover {
		background: color-mix(in srgb, var(--color-accent) 10%, transparent);
	}

	.tag-suggestion-empty {
		color: var(--color-text-secondary);
	}

	.tag-suggestion-count {
		color: var(--color-text-secondary);
		font-size: 0.72rem;
		margin-left: 0.75rem;
	}

	/* ── Ranges ───────────────────────────────────────────────────────────── */
	.ranges-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 0.5rem 1rem;
	}

	.range-row {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.range-inputs {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.range-input {
		flex: 1;
		padding: 0.45rem 0.6rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 7px;
		color: var(--color-text);
		font-size: 0.875rem;
		transition: border-color 0.15s;
	}

	.range-input:focus {
		outline: none;
		border-color: var(--color-accent);
	}

	.range-sep {
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	/* ── Query Preview ────────────────────────────────────────────────────── */
	.query-preview {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
		padding: 0.75rem;
		background: color-mix(in srgb, var(--color-accent) 6%, var(--color-tertiary-bg));
		border: 1px solid color-mix(in srgb, var(--color-accent) 25%, transparent);
		border-radius: 8px;
	}

	.preview-label {
		font-size: 0.72rem;
		font-weight: 600;
		color: var(--color-accent);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	.preview-code {
		font-family: 'Courier New', ui-monospace, monospace;
		font-size: 0.825rem;
		color: var(--color-text);
		word-break: break-all;
	}

	/* ── History / Saved Lists ────────────────────────────────────────────── */
	.list-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.list-header {
		display: flex;
		justify-content: flex-end;
	}

	.btn-ghost-sm {
		background: none;
		border: 1px solid var(--color-border);
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.25rem 0.6rem;
		border-radius: 5px;
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.75rem;
		transition: all 0.15s;
	}

	.btn-ghost-sm:hover { border-color: var(--color-border-strong); color: var(--color-text); }

	.entry-list {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.entry-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 0.625rem 0.75rem;
		transition: background 0.15s, border-color 0.15s;
	}

	.entry-row:hover {
		background: color-mix(in srgb, var(--color-accent) 8%, var(--color-tertiary-bg));
		border-color: var(--color-border-strong);
	}

	.entry-btn {
		flex: 1;
		background: none;
		border: none;
		color: var(--color-text);
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.6rem;
		text-align: left;
		padding: 0;
		overflow: hidden;
	}

	:global(.entry-icon) { color: var(--color-text-secondary); flex-shrink: 0; }
	:global(.entry-icon.accent) { color: var(--color-accent); }

	.entry-query {
		flex: 1;
		font-family: 'Courier New', ui-monospace, monospace;
		font-size: 0.825rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.entry-query.dimmed { color: var(--color-text-secondary); }

	.entry-name {
		font-weight: 600;
		font-size: 0.875rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 140px;
	}

	.entry-time {
		font-size: 0.72rem;
		color: var(--color-text-secondary);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.entry-del {
		background: none;
		border: none;
		color: var(--color-text-secondary);
		cursor: pointer;
		padding: 0.25rem;
		border-radius: 4px;
		display: flex;
		align-items: center;
		transition: background 0.15s, color 0.15s;
		flex-shrink: 0;
	}

	.entry-del:hover {
		background: color-mix(in srgb, #f87171 15%, transparent);
		color: #f87171;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 3rem 1rem;
		color: var(--color-text-secondary);
		text-align: center;
	}

	.empty-state p { margin: 0; font-size: 0.9rem; }

	/* ── Footer ───────────────────────────────────────────────────────────── */
	.modal-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-top: 1px solid var(--color-border-strong);
		flex-shrink: 0;
		gap: 0.75rem;
	}

	.footer-left, .footer-right {
		display: flex;
		gap: 0.5rem;
	}

	.btn-secondary, .btn-primary {
		padding: 0.55rem 1.1rem;
		border-radius: 7px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		transition: all 0.15s;
		border: none;
	}

	.btn-secondary {
		background: var(--color-tertiary-bg);
		border: 1px solid var(--color-border-strong);
		color: var(--color-text);
	}

	.btn-secondary:hover { background: var(--color-border); }

	.btn-primary {
		background: var(--color-accent);
		color: #fff;
	}

	.btn-primary:hover:not(:disabled) {
		background: color-mix(in srgb, var(--color-accent) 80%, #fff);
	}

	.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }

	/* ── Save Dialog ──────────────────────────────────────────────────────── */
	.save-dialog {
		background: var(--color-secondary-bg);
		border: 1px solid var(--color-border-strong);
		border-radius: 12px;
		padding: 1.5rem;
		width: min(400px, 100%);
		display: flex;
		flex-direction: column;
		gap: 1rem;
		box-shadow: 0 12px 48px rgba(0,0,0,0.5);
	}

	.save-dialog h3 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--color-text);
	}

	.save-actions {
		display: flex;
		gap: 0.5rem;
		justify-content: flex-end;
	}

	/* ── Responsive ───────────────────────────────────────────────────────── */
	@media (max-width: 600px) {
		.fields-grid { grid-template-columns: 1fr; }
		.ranges-grid { grid-template-columns: 1fr; }
		.modal-footer { flex-direction: column; align-items: stretch; }
		.footer-left, .footer-right { width: 100%; justify-content: stretch; }
		.btn-secondary, .btn-primary { flex: 1; justify-content: center; }
	}
</style>
