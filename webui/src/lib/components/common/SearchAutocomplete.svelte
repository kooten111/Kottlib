<script>
	import { onMount, onDestroy } from "svelte";
	import {
		Search,
		SlidersHorizontal,
		Library,
		BookOpen,
	} from "lucide-svelte";
	import { getLibraries } from "$lib/api/libraries";
	import { searchComics } from "$lib/api/search";
	import { getCoverUrl } from "$lib/api/comics";
	import { showAdvancedSearch } from "$lib/stores/advancedSearch";
	import AdvancedSearchModal from "$lib/components/search/AdvancedSearchModal.svelte";

	export let placeholder = "Search comics... (Ctrl+K)";
	export let onSelect = null;

	// Expose focus method
	export function focus() {
		inputElement?.focus();
	}

	// Expose search method
	export function triggerSearch() {
		if (searchQuery.trim()) {
			if (isOpen && selectedIndex >= 0) {
				selectResult(results[selectedIndex]);
			} else {
				navigateToSearch();
			}
		}
	}

	let searchQuery = "";
	let isOpen = false;
	let results = [];
	let isSearching = false;
	let searchTimeout;
	let selectedIndex = -1;
	let inputElement;
	let dropdownElement;

	// Debounced search
	$: if (searchQuery.trim().length >= 2) {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(performSearch, 300);
	} else {
		results = [];
		isOpen = false;
	}

	async function performSearch() {
		if (!searchQuery.trim() || searchQuery.trim().length < 2) {
			results = [];
			isOpen = false;
			return;
		}

		try {
			isSearching = true;
			const libraries = await getLibraries();

			// Search across all libraries
			const searchPromises = libraries.map(async (lib) => {
				try {
					const comics = await searchComics(lib.id, searchQuery);
					return comics.map((item) => ({
						...item,
						libraryId: lib.id,
						libraryName: lib.name,
					}));
				} catch {
					return [];
				}
			});

			const searchResults = await Promise.all(searchPromises);
			results = searchResults.flat().slice(0, 8); // Limit to 8 results
			isOpen = true; // Always open if search completes
			selectedIndex = -1;
		} catch (error) {
			console.error("Search failed:", error);
			results = [];
			isOpen = true; // Open to show error/empty state
		} finally {
			isSearching = false;
		}
	}

	function handleKeydown(e) {
		if (!isOpen) {
			if (e.key === "Enter" && searchQuery.trim()) {
				navigateToSearch();
			}
			return;
		}

		switch (e.key) {
			case "ArrowDown":
				e.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
				scrollToSelected();
				break;
			case "ArrowUp":
				e.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, -1);
				scrollToSelected();
				break;
			case "Enter":
				e.preventDefault();
				if (selectedIndex >= 0) {
					selectResult(results[selectedIndex]);
				} else {
					navigateToSearch();
				}
				break;
			case "Escape":
				isOpen = false;
				selectedIndex = -1;
				break;
		}
	}

	function scrollToSelected() {
		if (!dropdownElement || selectedIndex < 0) return;
		const selectedElement = dropdownElement.children[selectedIndex];
		if (selectedElement) {
			selectedElement.scrollIntoView({ block: "nearest" });
		}
	}

	function selectResult(result) {
		if (onSelect) {
			onSelect(result);
		} else {
			if (result.type === "series") {
				window.location.href = `/library/${result.libraryId}/browse/${encodeURIComponent(result.name)}`;
			} else {
				// Navigate to the parent folder's browse view
				const segments = result.path
					? result.path.replace(/^\//, "").split("/").slice(0, -1)
					: [];
				const folderPath = segments
					.map((s) => encodeURIComponent(s))
					.join("/");
				window.location.href = `/library/${result.libraryId}/browse/${folderPath}`;
			}
		}
		isOpen = false;
		searchQuery = "";
		selectedIndex = -1;
	}

	function navigateToSearch() {
		window.location.href = `/search?q=${encodeURIComponent(searchQuery)}`;
		isOpen = false;
		selectedIndex = -1;
	}

	function openAdvancedSearch() {
		isOpen = false;
		selectedIndex = -1;
		showAdvancedSearch.set(true);
	}

	function handleAdvancedSearch(event) {
		const { query } = event.detail;
		window.location.href = `/search?q=${encodeURIComponent(query)}`;
	}

	function handleClickOutside(e) {
		if (
			inputElement &&
			!inputElement.contains(e.target) &&
			dropdownElement &&
			!dropdownElement.contains(e.target)
		) {
			isOpen = false;
			selectedIndex = -1;
		}
	}

	function handleFocus() {
		if (searchQuery.trim().length >= 2) {
			isOpen = true;
		}
	}

	// Keyboard shortcut (Ctrl/Cmd + K)
	function handleGlobalKeydown(e) {
		if ((e.ctrlKey || e.metaKey) && e.key === "k") {
			e.preventDefault();
			inputElement?.focus();
		}
	}

	onMount(() => {
		if (typeof document !== "undefined") {
			document.addEventListener("click", handleClickOutside);
			document.addEventListener("keydown", handleGlobalKeydown);
		}
	});

	onDestroy(() => {
		if (typeof document !== "undefined") {
			document.removeEventListener("click", handleClickOutside);
			document.removeEventListener("keydown", handleGlobalKeydown);
		}
		clearTimeout(searchTimeout);
	});

	function getResultTitle(result) {
		if (result.type === "series") {
			return result.name;
		}
		return (
			result.title ||
			result.file_name?.replace(/\.(cbz|cbr|cb7|cbt)$/i, "") ||
			"Untitled"
		);
	}

	function getResultCover(result) {
		const hash = result.hash || result.coverHash || result.first_comic_hash;
		return hash ? getCoverUrl(result.libraryId, hash) : null;
	}
</script>

<div class="search-container">
	<div class="search-input-wrapper">
		<input
			bind:this={inputElement}
			type="text"
			bind:value={searchQuery}
			on:keydown={handleKeydown}
			on:focus={handleFocus}
			{placeholder}
			class="search-input"
			autocomplete="off"
			spellcheck="false"
		/>
		{#if isSearching}
			<div class="search-spinner"></div>
		{/if}
	</div>

	{#if isOpen}
		<div bind:this={dropdownElement} class="search-dropdown">
			{#if results.length > 0}
				{#each results as result, index}
					<button
						class="search-result"
						class:selected={index === selectedIndex}
						on:click={() => selectResult(result)}
						type="button"
					>
						<div
							class="result-cover"
							class:result-cover-icon={result.type === "series"}
						>
							{#if getResultCover(result)}
								<img
									src={getResultCover(result)}
									alt={getResultTitle(result)}
									loading="lazy"
									decoding="async"
								/>
							{:else if result.type === "series"}
								<div class="result-icon-placeholder">
									<BookOpen size={32} class="opacity-50" />
								</div>
							{:else}
								<div class="result-cover-placeholder">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
									>
										<path
											d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"
										/>
										<path
											d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
										/>
									</svg>
								</div>
							{/if}
						</div>
						<div class="result-info">
							<div class="result-title">
								{getResultTitle(result)}
							</div>
							<div class="result-meta">
								{#if result.type === "series"}
									<span class="result-tag">Series</span>
								{:else if result.series}
									<span class="result-series"
										>{result.series}</span
									>
									<span class="result-separator">•</span>
								{/if}
								<span class="result-library"
									>{result.libraryName}</span
								>
							</div>
						</div>
					</button>
				{/each}

				{#if results.length === 8}
					<button
						class="search-see-all"
						on:click={navigateToSearch}
						type="button"
					>
						See all results →
					</button>
				{/if}
			{:else if !isSearching && searchQuery.trim().length >= 2}
				<div class="no-results">
					<Search class="w-8 h-8 opacity-50 mb-2" />
					<p>No comics found matching "{searchQuery}"</p>
				</div>
			{/if}

			<button
				class="search-advanced"
				on:click={openAdvancedSearch}
				type="button"
			>
				<SlidersHorizontal class="w-4 h-4" />
				Advanced Search
			</button>
		</div>
	{/if}
</div>

{#if $showAdvancedSearch}
	<AdvancedSearchModal
		libraryId={null}
		initialQuery={searchQuery}
		onClose={() => showAdvancedSearch.set(false)}
		on:search={handleAdvancedSearch}
	/>
{/if}

<style>
	.search-container {
		position: relative;
		width: 100%;
	}

	.search-input-wrapper {
		position: relative;
	}

	.search-input {
		width: 100%;
		padding: 0.625rem 2.5rem 0.625rem 1rem;
		background: var(--color-secondary-bg);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 0.875rem;
		transition: all 0.2s;
	}

	.search-input:focus {
		outline: none;
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px rgba(255, 103, 64, 0.1);
	}

	.search-input::placeholder {
		color: var(--color-text-secondary);
	}

	.search-spinner {
		position: absolute;
		right: 2.25rem;
		top: 50%;
		transform: translateY(-50%);
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: translateY(-50%) rotate(360deg);
		}
	}

	.search-dropdown {
		position: absolute;
		top: calc(100% + 0.5rem);
		left: 0;
		right: 0;
		background: #242424;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
		max-height: 400px;
		overflow-y: auto;
		z-index: 100;
	}

	.search-result {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.75rem;
		background: transparent;
		border: none;
		border-bottom: 1px solid rgba(255, 255, 255, 0.05);
		cursor: pointer;
		transition: background 0.15s;
		text-align: left;
	}

	.search-result:last-of-type {
		border-bottom: none;
	}

	.search-result:hover,
	.search-result.selected {
		background: rgba(255, 103, 64, 0.1);
	}

	.result-cover {
		width: 48px;
		height: 72px;
		flex-shrink: 0;
		border-radius: 4px;
		overflow: hidden;
		background: #1a1a1a;
	}

	.result-cover img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.result-cover-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--color-text-secondary);
	}

	.result-info {
		flex: 1;
		min-width: 0;
	}

	.result-title {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		margin-bottom: 0.25rem;
	}

	.result-meta {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.result-series {
		font-weight: 500;
		color: var(--color-accent);
	}

	.result-separator {
		color: var(--color-text-secondary);
	}

	.result-library {
		opacity: 0.8;
	}

	.result-tag {
		font-size: 0.7rem;
		font-weight: 600;
		background: var(--color-accent);
		color: #fff;
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.result-icon-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(255, 103, 64, 0.1);
		color: var(--color-accent);
	}

	.search-see-all {
		width: 100%;
		padding: 0.75rem;
		background: transparent;
		border: none;
		color: var(--color-accent);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
		text-align: center;
	}

	.search-see-all:hover {
		background: rgba(255, 103, 64, 0.1);
	}

	.search-advanced {
		width: 100%;
		padding: 0.75rem;
		background: transparent;
		border: none;
		border-top: 1px solid rgba(255, 255, 255, 0.1);
		color: var(--color-accent);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.search-advanced:hover {
		background: rgba(255, 103, 64, 0.1);
	}

	/* Scrollbar styling */
	.search-dropdown::-webkit-scrollbar {
		width: 8px;
	}

	.search-dropdown::-webkit-scrollbar-track {
		background: transparent;
	}

	.search-dropdown::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.2);
		border-radius: 4px;
	}

	.search-dropdown::-webkit-scrollbar-thumb:hover {
		background: rgba(255, 255, 255, 0.3);
	}

	.no-results {
		padding: 2rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		color: var(--color-text-secondary);
		text-align: center;
		font-size: 0.875rem;
	}
</style>
