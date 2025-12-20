<script>
	import { Github } from 'lucide-svelte';
</script>

<footer class="bg-dark-bg-secondary border-t border-gray-700 mt-auto">
	<div class="container mx-auto px-4 py-6 max-w-content">
		<div class="flex flex-col md:flex-row justify-between items-center">
			<div class="text-dark-text-secondary text-sm mb-4 md:mb-0">
				<p>Kottlib - Modern Comic Library Server</p>
				<p class="mt-1">Compatible with YACReader mobile apps</p>
			</div>

			<div class="flex items-center space-x-6">
				<a
					href="https://github.com/YACReader/yacreader"
					target="_blank"
					rel="noopener noreferrer"
					class="text-dark-text-secondary hover:text-dark-text transition-colors flex items-center space-x-2"
				>
					<Github class="w-5 h-5" />
					<span class="text-sm">YACReader</span>
				</a>

				<a
					href="/admin"
					class="text-dark-text-secondary hover:text-dark-text transition-colors text-sm"
				>
					Admin Panel
				</a>

				<a
					href="/docs"
					class="text-dark-text-secondary hover:text-dark-text transition-colors text-sm"
				>
					Documentation
				</a>
			</div>
		</div>
	</div>
</footer>
