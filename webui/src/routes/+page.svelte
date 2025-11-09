<script>
	import Navbar from '$components/layout/Navbar.svelte';
</script>

<div class="flex flex-col min-h-screen">
	<Navbar />

	<main class="flex-1 container mx-auto px-4 py-8 max-w-content">
		<div class="text-center py-16">
			<h1 class="text-4xl font-bold mb-4 text-dark-text">
				Welcome to YACLib Enhanced
			</h1>
			<p class="text-xl text-dark-text-secondary mb-8">
				Modern Comic Library Server
			</p>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
				<div class="card">
					<h2 class="text-2xl font-semibold mb-3">Browse Libraries</h2>
					<p class="text-dark-text-secondary">
						Access your comic collection from anywhere
					</p>
					<a href="/browse" class="btn-primary mt-4 inline-block">
						Start Reading
					</a>
				</div>

				<div class="card">
					<h2 class="text-2xl font-semibold mb-3">Continue Reading</h2>
					<p class="text-dark-text-secondary">
						Pick up where you left off
					</p>
					<a href="/continue-reading" class="btn-primary mt-4 inline-block">
						View Progress
					</a>
				</div>

				<div class="card">
					<h2 class="text-2xl font-semibold mb-3">Search</h2>
					<p class="text-dark-text-secondary">
						Find your favorite comics quickly
					</p>
					<a href="/search" class="btn-primary mt-4 inline-block">
						Search Now
					</a>
				</div>
			</div>
		</div>
	</main>
</div>
