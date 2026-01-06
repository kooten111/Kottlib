<script>
	import { page } from "$app/stores";
	import { themeStore } from "$stores/theme";
	import { currentFilterStore, treeExpandedNodes } from "$stores/library";
	import { uiStore } from "$stores/ui";
	import SearchAutocomplete from "$lib/components/common/SearchAutocomplete.svelte";
	import { Moon, Sun, BookOpen, Menu } from "lucide-svelte";

	function clearFilters() {
		currentFilterStore.set(null);
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
</script>

<nav class="bg-dark-bg-secondary border-b border-gray-700 sticky top-0 z-50">
	<div class="container mx-auto px-4 max-w-content">
		<div class="flex items-center justify-between h-16">
			<!-- Hamburger Menu Button (Mobile only) -->
			<button
				class="lg:hidden p-2 rounded-button hover:bg-dark-bg-tertiary transition-colors focus-ring mr-2"
				on:click={() => uiStore.toggleSidebar()}
				aria-label="Toggle sidebar menu"
			>
				<Menu class="w-6 h-6 text-dark-text" />
			</button>

			<!-- Logo and Brand -->
			<div class="flex items-center space-x-8">
				<a
					href="/"
					class="flex items-center space-x-2 hover:opacity-80 transition-opacity"
					on:click={handleHomeClick}
				>
					<BookOpen class="w-8 h-8 text-accent-orange" />
					<span class="text-xl font-bold text-dark-text">Kottlib</span
					>
				</a>

				<!-- Main Navigation removed as it's now in the sidebar -->
			</div>

			<!-- Search Bar -->
			<div class="flex-1 max-w-md mx-8 hidden lg:flex">
				<SearchAutocomplete
					placeholder="Search comics and libraries..."
				/>
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
