<script>
	import { page } from '$app/stores';
	import { themeStore } from '$stores/theme';
	import { Moon, Sun, Home, BookOpen, Heart, List, Search } from 'lucide-svelte';
	import SearchAutocomplete from '$components/common/SearchAutocomplete.svelte';

	let searchComponent;

	function handleSearchIconClick() {
		searchComponent?.triggerSearch();
	}
</script>

<nav class="bg-dark-bg-secondary border-b border-gray-700 sticky top-0 z-50">
	<div class="container mx-auto px-4 max-w-content">
		<div class="flex items-center justify-between h-16">
			<!-- Logo and Brand -->
			<div class="flex items-center space-x-8">
				<a href="/" class="flex items-center space-x-2 hover:opacity-80 transition-opacity">
					<BookOpen class="w-8 h-8 text-accent-orange" />
					<span class="text-xl font-bold text-dark-text">YACLib</span>
				</a>

				<!-- Main Navigation -->
				<div class="hidden md:flex items-center space-x-6">
					<a
						href="/"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname === '/'}
					>
						<Home class="w-4 h-4" />
						<span>Home</span>
					</a>

					<a
						href="/browse"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname.startsWith('/browse')}
					>
						<BookOpen class="w-4 h-4" />
						<span>Browse</span>
					</a>

					<a
						href="/continue-reading"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname === '/continue-reading'}
					>
						<List class="w-4 h-4" />
						<span>Continue</span>
					</a>

					<a
						href="/favorites"
						class="flex items-center space-x-2 text-dark-text-secondary hover:text-dark-text transition-colors"
						class:text-accent-orange={$page.url.pathname === '/favorites'}
					>
						<Heart class="w-4 h-4" />
						<span>Favorites</span>
					</a>
				</div>
			</div>

			<!-- Search Bar -->
			<div class="flex-1 max-w-md mx-8 hidden lg:flex items-center gap-3">
				<SearchAutocomplete bind:this={searchComponent} placeholder="Search comics... (Ctrl+K)" />
				<button on:click={handleSearchIconClick} class="hover:text-dark-text transition-colors" aria-label="Focus search">
					<Search class="w-6 h-6 text-dark-text-secondary flex-shrink-0" />
				</button>
			</div>

			<!-- Right Side Actions -->
			<div class="flex items-center space-x-4">
				<!-- Theme Toggle -->
				<button
					on:click={() => themeStore.toggle()}
					class="p-2 rounded-button hover:bg-dark-bg-tertiary transition-colors focus-ring"
					aria-label="Toggle theme"
				>
					{#if $themeStore === 'dark'}
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

		<!-- Mobile Search (visible on small screens) -->
		<div class="lg:hidden pb-3">
			<SearchAutocomplete placeholder="Search comics..." />
		</div>
	</div>
</nav>
