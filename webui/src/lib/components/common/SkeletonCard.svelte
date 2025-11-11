<!--
  Skeleton loading placeholder for comic cards
  Provides visual feedback during initial page load
-->
<script>
	export let width = 180;
	export let height = 270;
</script>

<div
	class="skeleton-card"
	style="width: {width}px; height: {height}px;"
	aria-label="Loading..."
>
	<div class="skeleton-image" />
	<div class="skeleton-content">
		<div class="skeleton-title" />
		<div class="skeleton-subtitle" />
	</div>
</div>

<style>
	.skeleton-card {
		display: flex;
		flex-direction: column;
		border-radius: 8px;
		overflow: hidden;
		background: rgba(255, 255, 255, 0.05);
	}

	.skeleton-image {
		flex: 1;
		background: linear-gradient(
			90deg,
			rgba(255, 255, 255, 0.05) 25%,
			rgba(255, 255, 255, 0.1) 50%,
			rgba(255, 255, 255, 0.05) 75%
		);
		background-size: 200% 100%;
		animation: shimmer 2s infinite;
	}

	.skeleton-content {
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.skeleton-title {
		height: 16px;
		background: linear-gradient(
			90deg,
			rgba(255, 255, 255, 0.05) 25%,
			rgba(255, 255, 255, 0.1) 50%,
			rgba(255, 255, 255, 0.05) 75%
		);
		background-size: 200% 100%;
		border-radius: 4px;
		animation: shimmer 2s infinite;
		width: 80%;
	}

	.skeleton-subtitle {
		height: 12px;
		background: linear-gradient(
			90deg,
			rgba(255, 255, 255, 0.05) 25%,
			rgba(255, 255, 255, 0.1) 50%,
			rgba(255, 255, 255, 0.05) 75%
		);
		background-size: 200% 100%;
		border-radius: 4px;
		animation: shimmer 2s infinite;
		animation-delay: 0.2s;
		width: 60%;
	}

	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}
</style>
