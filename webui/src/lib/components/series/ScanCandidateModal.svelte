<script>
	import { createEventDispatcher } from 'svelte';
	import { X, ExternalLink, Check, Loader2 } from 'lucide-svelte';

	export let open = false;
	export let candidates = [];
	export let isApplying = false;
	export let selectedIndex = -1;

	const dispatch = createEventDispatcher();

	function closeModal() {
		dispatch('close');
	}

	function selectCandidate(candidate, index) {
		dispatch('select', { candidate, index });
	}
</script>

{#if open && candidates.length > 0}
	<div
		class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
		on:click|self={closeModal}
		on:keydown={(e) => e.key === 'Escape' && closeModal()}
		role="dialog"
		aria-modal="true"
		aria-labelledby="candidate-modal-title"
		tabindex="-1"
	>
		<div
			class="bg-dark-bg-secondary rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden border"
			style="border-color: var(--color-border);"
		>
			<div
				class="flex items-center justify-between p-5 border-b bg-gradient-to-r from-accent-orange/10 to-accent-orange/5"
				style="border-color: var(--color-border);"
			>
				<div>
					<h2 id="candidate-modal-title" class="text-xl font-bold text-dark-text">
						Select Match
					</h2>
					<p class="text-sm text-accent-orange/80 mt-1">
						No automatic match found. Choose from {candidates.length}
						candidate{candidates.length > 1 ? 's' : ''} below:
					</p>
				</div>
				<button
					on:click={closeModal}
					class="p-2 hover:bg-dark-bg-tertiary rounded-lg transition-colors text-dark-text-secondary hover:text-dark-text"
					aria-label="Close modal"
				>
					<X class="w-5 h-5" />
				</button>
			</div>

			<div class="overflow-y-auto max-h-[calc(85vh-120px)] p-4 space-y-3">
				{#each candidates as candidate, index}
					<button
						on:click={() => selectCandidate(candidate, index)}
						disabled={isApplying}
						class="w-full text-left p-4 rounded-xl border transition-all duration-200
                               {selectedIndex === index
							? 'border-status-success bg-status-success/20'
							: 'bg-dark-bg-tertiary hover:border-accent-orange/50 hover:bg-accent-orange/10'}
                               disabled:opacity-50 disabled:cursor-not-allowed"
						style="border-color: {selectedIndex === index ? '' : 'var(--color-border)'}"
					>
						<div class="flex items-start gap-4">
							<div class="flex-shrink-0">
								<div
									class="w-14 h-14 rounded-xl flex flex-col items-center justify-center
                                           {candidate.confidence >= 0.7
										? 'bg-status-success/20 text-status-success'
										: candidate.confidence >= 0.5
											? 'bg-status-warning/20 text-status-warning'
											: 'bg-status-error/20 text-status-error'}"
								>
									<span class="text-lg font-bold">
										{Math.round(candidate.confidence * 100)}
									</span>
									<span class="text-xs opacity-70">%</span>
								</div>
							</div>

							<div class="flex-1 min-w-0">
								<h3 class="text-dark-text font-semibold text-lg truncate">
									{candidate.title || candidate.metadata?.title || 'Unknown Title'}
								</h3>

								{#if candidate.metadata}
									<div class="mt-2 flex flex-wrap gap-2 text-sm">
										{#if candidate.metadata.year}
											<span class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary">
												{candidate.metadata.year}
											</span>
										{/if}
										{#if candidate.metadata.status}
											<span
												class="px-2 py-0.5 rounded
                                                   {candidate.metadata.status === 'FINISHED'
													? 'bg-status-success/20 text-status-success'
													: candidate.metadata.status === 'RELEASING'
														? 'bg-accent-blue/20 text-accent-blue'
														: 'bg-dark-bg text-dark-text-muted'}"
											>
												{candidate.metadata.status}
											</span>
										{/if}
										{#if candidate.metadata.format}
											<span class="px-2 py-0.5 rounded bg-accent-blue/20 text-accent-blue">
												{candidate.metadata.format}
											</span>
										{/if}
										{#if candidate.metadata.count}
											<span class="px-2 py-0.5 rounded bg-dark-bg text-dark-text-secondary">
												{candidate.metadata.count} chapters
											</span>
										{/if}
									</div>

									{#if candidate.metadata.writer || candidate.metadata.artist}
										<p class="mt-2 text-sm text-dark-text-secondary truncate">
											{#if candidate.metadata.writer}
												<span>By {candidate.metadata.writer}</span>
											{/if}
											{#if candidate.metadata.writer && candidate.metadata.artist && candidate.metadata.writer !== candidate.metadata.artist}
												<span>• Art by {candidate.metadata.artist}</span>
											{:else if candidate.metadata.artist && !candidate.metadata.writer}
												<span>Art by {candidate.metadata.artist}</span>
											{/if}
										</p>
									{/if}

									{#if candidate.metadata.description}
										<p class="mt-2 text-sm text-dark-text-muted line-clamp-2">
											{candidate.metadata.description
												.replace(/<[^>]*>/g, '')
												.substring(0, 150)}...
										</p>
									{/if}
								{/if}
							</div>

							<div class="flex-shrink-0 flex items-center">
								{#if selectedIndex === index && isApplying}
									<Loader2 class="w-5 h-5 animate-spin text-status-success" />
								{:else}
									<div class="p-2 rounded-lg bg-dark-bg group-hover:bg-accent-orange/20 transition-colors">
										<Check class="w-5 h-5 text-dark-text-muted" />
									</div>
								{/if}
							</div>
						</div>

						{#if candidate.source_url}
							<a
								href={candidate.source_url}
								target="_blank"
								rel="noopener noreferrer"
								on:click|stopPropagation
								class="mt-3 inline-flex items-center gap-1 text-xs text-accent-blue hover:text-accent-orange-hover transition-colors"
							>
								<ExternalLink class="w-3 h-3" />
								View on AniList
							</a>
						{/if}
					</button>
				{/each}
			</div>

			<div class="p-4 border-t bg-dark-bg-tertiary" style="border-color: var(--color-border);">
				<div class="flex justify-between items-center">
					<p class="text-xs text-dark-text-muted">Click on a result to apply its metadata</p>
					<button
						on:click={closeModal}
						class="px-4 py-2 rounded-lg bg-dark-bg text-dark-text-secondary hover:bg-dark-bg-secondary transition-colors text-sm font-medium"
					>
						Cancel
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
