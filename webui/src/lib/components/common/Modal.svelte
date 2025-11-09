<script>
	import { X } from 'lucide-svelte';

	export let open = false;
	export let title = '';
	export let onClose = () => {};

	function handleClose() {
		open = false;
		onClose();
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') {
			handleClose();
		}
	}
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		on:keydown={handleKeydown}
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		<!-- Backdrop -->
		<div
			class="absolute inset-0 bg-black bg-opacity-75 transition-opacity"
			on:click={handleClose}
			role="button"
			tabindex="0"
			aria-label="Close modal"
		/>

		<!-- Modal Content -->
		<div class="relative bg-dark-bg-secondary rounded-card shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b border-gray-700">
				<h2 id="modal-title" class="text-xl font-semibold text-dark-text">
					{title}
				</h2>
				<button
					on:click={handleClose}
					class="p-2 hover:bg-dark-bg-tertiary rounded-button transition-colors"
					aria-label="Close"
				>
					<X class="w-5 h-5" />
				</button>
			</div>

			<!-- Body -->
			<div class="p-4">
				<slot />
			</div>

			<!-- Footer (optional) -->
			{#if $$slots.footer}
				<div class="p-4 border-t border-gray-700">
					<slot name="footer" />
				</div>
			{/if}
		</div>
	</div>
{/if}
