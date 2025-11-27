<script>
	import { page } from "$app/stores";
	import { themeStore } from "$stores/theme";
	import { searchStore } from "$stores/search";
	import { currentFilterStore, treeExpandedNodes } from "$stores/library";
	import {
		Moon,
		Sun,
		Home,
		BookOpen,
		Heart,
		List,
		Search as SearchIcon,
		X,
	} from "lucide-svelte";

	let searchInput;

	// Debug: Track search store changes
	$: console.log("[Navbar] Search store query changed:", $searchStore.query);

	function clearSearch() {
		console.log("[Navbar] Clearing search");
		searchStore.set({
			query: "",
			isSearching: false,
		});
		if (searchInput) {
			searchInput.value = "";
		}
	}

	function clearFilters() {
		console.log("[Navbar] Clearing filters");
		currentFilterStore.set(null);
		clearSearch();
	}

	function handleHomeClick() {
		clearFilters();
		// Collapse all tree nodes except the root
		const collapsedState = new Set(["libraries-root"]);
		treeExpandedNodes.set(collapsedState);

		// Persist the collapsed state to localStorage immediately
		if (typeof window !== "undefined") {
			localStorage.setItem(
				"series-tree-expanded",
				JSON.stringify([...collapsedState]),
			);
		}
	}

	function handleSearchKeydown(e) {
		if (e.key === "Escape") {
			clearSearch();
			searchInput?.blur();
		}
	}
</script>

<nav class="bg-dark-bg-secondary border-b border-gray-700 sticky top-0 z-50">
	<div class="container mx-auto px-4 max-w-content">
		<div class="flex items-center justify-between h-16">
			<!-- Logo and Brand -->
			<div class="flex items-center space-x-8">
				<a
					href="/"
					class="flex items-center space-x-2 hover:opacity-80 transition-opacity"
					on:click={handleHomeClick}
				>
					<BookOpen class="w-8 h-8 text-accent-orange" />
					<span class="text-xl font-bold text-dark-text">YACLib</span>
				</a>

				<!-- Main Navigation -->
				<div class="hidden md:flex items-center space-x-6">
					<a
						href="/"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname === "/"}
						on:click={handleHomeClick}
					>
						<Home class="w-4 h-4" />
						<span>Home</span>
					</a>

					<a
						href="/continue-reading"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname ===
							"/continue-reading"}
					>
						<List class="w-4 h-4" />
						<span>Continue</span>
					</a>

					<a
						href="/favorites"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname ===
							"/favorites"}
					>
						<Heart class="w-4 h-4" />
						<span>Favorites</span>
					</a>
				</div>
			</div>

			<!-- Search Bar -->
			<div class="flex-1 max-w-md mx-8 hidden lg:flex">
				<div class="search-input-wrapper">
					<input
						bind:this={searchInput}
						type="text"
						class="search-input"
						placeholder="Search comics and series..."
						bind:value={$searchStore.query}
						on:keydown={handleSearchKeydown}
					/>
					{#if $searchStore.query}
						<button
							class="search-clear"
							on:click={clearSearch}
							aria-label="Clear search"
						>
							<X class="w-4 h-4" />
						</button>
					{:else}
						<SearchIcon class="search-icon" />
					{/if}
				</div>
			</div>

			<!-- Right Side Actions -->
			<div class="flex items-center space-x-4">
				<!-- Theme Toggle -->
				<button
					on:click={() => themeStore.toggle()}
					class="p-2 rounded-button hover:bg-dark-bg-tertiary transition-colors focus-ring"
					aria-label="Toggle theme"
				>
					{#if $themeStore.mode === "dark"}
						<Sun class="w-5 h-5 text-dark-text-secondary" />
					{:else}
						<Moon class="w-5 h-5 text-dark-text-secondary" />
					{/if}
				</button>

				<!-- Admin Link -->
				<a
					href="/admin"
					class="hidden md:inline-block btn-secondary text-sm"
				>
					Admin
				</a>
			</div>
		</div>
	</div>
</nav>

<style>
	.search-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		width: 100%;
	}

	.search-icon {
		position: absolute;
		right: 0.75rem;
		width: 18px;
		height: 18px;
		color: var(--color-text-secondary);
		pointer-events: none;
		z-index: 1;
	}

	.search-input {
		width: 100%;
		padding: 0.625rem 2.5rem 0.625rem 1rem;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 8px;
		color: var(--color-text);
		font-size: 0.875rem;
		transition: all 0.2s;
	}

	.search-input:focus {
		outline: none;
		border-color: var(--color-accent);
		background: rgba(255, 255, 255, 0.08);
	}

	.search-input::placeholder {
		color: var(--color-text-secondary);
	}

	.search-clear {
		position: absolute;
		right: 0.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		padding: 0;
		background: rgba(255, 255, 255, 0.1);
		border: none;
		border-radius: 50%;
		color: var(--color-text);
		cursor: pointer;
		transition: all 0.2s;
	}

	.search-clear:hover {
		background: rgba(255, 255, 255, 0.2);
		transform: scale(1.1);
	}
</style>
