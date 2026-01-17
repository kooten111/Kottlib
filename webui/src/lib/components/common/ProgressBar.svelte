<script>
	export let value = 0; // 0-100
	export let max = 100;
	export let color = 'accent-orange'; // Tailwind color class

	$: percentage = Math.min(Math.max((value / max) * 100, 0), 100);
</script>

<div class="w-full bg-dark-bg-tertiary rounded-full h-2 overflow-hidden">
	<div
		class="h-full bg-{color} transition-all duration-300 rounded-full"
		style="width: {percentage}%"
		role="progressbar"
		aria-valuenow={value}
		aria-valuemin="0"
		aria-valuemax={max}
	></div>
</div>
