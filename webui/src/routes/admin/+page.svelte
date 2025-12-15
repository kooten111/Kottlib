<script>
	import { onMount } from 'svelte';
	import Navbar from '$lib/components/layout/Navbar.svelte';
	import Card from '$lib/components/common/Card.svelte';
	import { getLibraries } from '$lib/api/libraries';
	import { Settings, Database, Users, Activity, HardDrive, BookOpen, Heart, List as ListIcon, Scan } from 'lucide-svelte';

	let libraries = [];
	let stats = {
		totalComics: 0,
		totalLibraries: 0
	};
	let isLoading = true;
	let error = null;

	onMount(async () => {
		await loadDashboardData();
	});

	async function loadDashboardData() {
		try {
			isLoading = true;
			error = null;

			// Load libraries
			libraries = await getLibraries();
			stats.totalLibraries = libraries.length;

			// Calculate total comics
			stats.totalComics = libraries.reduce((sum, lib) => sum + (lib.comic_count || 0), 0);

			isLoading = false;
		} catch (err) {
			console.error('Failed to load dashboard data:', err);
			error = err.message;
			isLoading = false;
		}
	}

</script>

<svelte:head>
	<title>Admin Dashboard - YACLib</title>
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
					<h1 class="page-title">Admin Dashboard</h1>
					<p class="page-subtitle">Manage your YACLib server</p>
				</div>
			</div>
		</div>

		{#if isLoading}
			<div class="loading-container">
				<div class="spinner" />
				<p class="text-gray-400 mt-4">Loading dashboard...</p>
			</div>
		{:else if error}
			<div class="error-container">
				<p class="text-red-400">Failed to load dashboard: {error}</p>
				<button class="btn-primary mt-4" on:click={loadDashboardData}>Try Again</button>
			</div>
		{:else}
			<!-- Stats Cards -->
			<div class="stats-grid">
				<!-- Total Comics -->
				<div class="stat-card">
					<div class="stat-icon">
						<BookOpen class="w-6 h-6 text-accent-orange" />
					</div>
					<div class="stat-content">
						<p class="stat-label">Total Comics</p>
						<p class="stat-value">{stats.totalComics.toLocaleString()}</p>
					</div>
				</div>

				<!-- Total Libraries -->
				<div class="stat-card">
					<div class="stat-icon">
						<Database class="w-6 h-6 text-blue-400" />
					</div>
					<div class="stat-content">
						<p class="stat-label">Libraries</p>
						<p class="stat-value">{stats.totalLibraries}</p>
					</div>
				</div>
			</div>

			<!-- Libraries Section -->
			<div class="section-card mb-6">
				<div class="section-header">
					<h2 class="section-title">
						<Database class="w-5 h-5" />
						Libraries
					</h2>
					<a href="/admin/libraries" class="see-all">Manage →</a>
				</div>
				<div class="libraries-list">
					{#if libraries.length > 0}
						{#each libraries as library}
							<div class="library-item">
								<div class="library-info">
									<p class="library-name">{library.name}</p>
									<p class="library-path">{library.path || 'No path'}</p>
								</div>
								<div class="library-stats">
									<span class="stat-badge">{library.comic_count || 0} comics</span>
								</div>
							</div>
						{/each}
					{:else}
						<p class="text-gray-400 text-sm">No libraries configured</p>
					{/if}
				</div>
			</div>

			<!-- Quick Actions -->
			<div class="quick-actions">
				<h2 class="section-title mb-4">Quick Actions</h2>
				<div class="actions-grid">
					<a href="/admin/libraries" class="action-card">
						<Database class="w-8 h-8 text-accent-orange" />
						<span>Manage Libraries</span>
					</a>
					<a href="/admin/scanners" class="action-card">
						<Scan class="w-8 h-8 text-blue-400" />
						<span>Manage Scanners</span>
					</a>
					<a href="/admin/settings" class="action-card">
						<Settings class="w-8 h-8 text-green-400" />
						<span>Server Settings</span>
					</a>
				</div>
			</div>
		{/if}
	</main>
</div>

<style>
	.page-header {
		margin-bottom: 2rem;
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

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	.stat-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1.5rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
		border: 1px solid transparent;
		transition: border-color 0.2s;
	}

	.stat-card:hover {
		border-color: var(--color-accent);
	}

	.stat-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 8px;
	}

	.stat-content {
		flex: 1;
	}

	.stat-label {
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		margin: 0 0 0.25rem 0;
	}

	.stat-value {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
	}

	.content-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	.section-card {
		padding: 1.5rem;
		background: var(--color-secondary-bg);
		border-radius: 8px;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
	}

	.see-all {
		font-size: 0.875rem;
		color: var(--color-accent);
		text-decoration: none;
		transition: opacity 0.2s;
	}

	.see-all:hover {
		opacity: 0.8;
	}

	.libraries-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.library-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem;
		background: rgba(255, 255, 255, 0.02);
		border-radius: 6px;
	}

	.library-info {
		flex: 1;
	}

	.library-name {
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.25rem 0;
	}

	.library-path {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin: 0;
		font-family: monospace;
	}

	.library-stats {
		display: flex;
		gap: 0.5rem;
	}

	.stat-badge {
		padding: 0.25rem 0.5rem;
		background: rgba(255, 255, 255, 0.05);
		border-radius: 4px;
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.activity-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.activity-item {
		display: flex;
		align-items: start;
		gap: 0.75rem;
	}

	.activity-dot {
		width: 8px;
		height: 8px;
		background: var(--color-accent);
		border-radius: 50%;
		margin-top: 0.5rem;
	}

	.activity-content {
		flex: 1;
	}

	.activity-message {
		font-size: 0.875rem;
		color: var(--color-text);
		margin: 0 0 0.25rem 0;
	}

	.activity-time {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin: 0;
	}

	.quick-actions {
		margin-top: 2rem;
	}

	.actions-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.action-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 2rem 1rem;
		background: var(--color-secondary-bg);
		border: 1px solid transparent;
		border-radius: 8px;
		color: var(--color-text);
		text-decoration: none;
		cursor: pointer;
		transition: all 0.2s;
	}

	.action-card:hover {
		border-color: var(--color-accent);
		transform: translateY(-2px);
	}

	.loading-container,
	.error-container {
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

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 768px) {
		.page-title {
			font-size: 1.5rem;
		}

		.icon-wrapper {
			width: 48px;
			height: 48px;
		}

		.stats-grid {
			grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
		}

		.stat-value {
			font-size: 1.5rem;
		}

		.content-grid,
		.actions-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
