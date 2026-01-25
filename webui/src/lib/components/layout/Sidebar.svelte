<script>
	import { tick } from "svelte";
	import { Filter, X } from "lucide-svelte";
	import { browser } from "$app/environment";

	export let open = true;

	// Read sidebar width synchronously to prevent FOUC
	let sidebarWidth = browser
		? parseInt(localStorage.getItem("sidebar-width") || "256", 10)
		: 256;
	let isResizing = false;
	let sidebarElement;

	function startResize(e) {
		isResizing = true;
		document.body.style.cursor = "col-resize";
		document.body.style.userSelect = "none"; // Prevent text selection while resizing

		window.addEventListener("mousemove", handleResize);
		window.addEventListener("mouseup", stopResize);
	}

	function handleResize(e) {
		if (!isResizing) return;

		// Calculate new width
		// Using e.clientX directly assumes sidebar is on the left
		let newWidth = e.clientX;

		// Constraints
		const MINI_WIDTH = 160;
		const MAX_WIDTH = 448;

		if (newWidth < MINI_WIDTH) newWidth = MINI_WIDTH;
		if (newWidth > MAX_WIDTH) newWidth = MAX_WIDTH;

		sidebarWidth = newWidth;
	}

	function stopResize() {
		isResizing = false;
		document.body.style.cursor = "";
		document.body.style.userSelect = "";

		window.removeEventListener("mousemove", handleResize);
		window.removeEventListener("mouseup", stopResize);

		// Save to localStorage
		localStorage.setItem("sidebar-width", sidebarWidth.toString());
	}
</script>

<div class="relative h-full flex">
	<!-- Toggle Button (Mobile) -->
	<button
		on:click={() => (open = !open)}
		class="lg:hidden fixed bottom-4 right-4 z-50 btn-primary rounded-full p-4 shadow-lg"
		aria-label="Toggle filters"
	>
		{#if open}
			<X class="w-6 h-6" />
		{:else}
			<Filter class="w-6 h-6" />
		{/if}
	</button>

	<!-- Sidebar Container -->
	<aside
		class="fixed lg:static inset-y-0 left-0 z-40 bg-dark-bg-secondary border-r border-gray-700 transform transition-transform duration-300 lg:transform-none flex flex-col"
		class:translate-x-0={open}
		class:-translate-x-full={!open}
		style="width: {open ? sidebarWidth + 'px' : '0px'};"
		bind:this={sidebarElement}
	>
		<div class="h-full overflow-y-auto overflow-x-hidden flex-1 relative">
			<slot />
		</div>

		<!-- Resize Handle -->
		<div
			class="resize-handle"
			on:mousedown={startResize}
			role="slider"
			tabindex="0"
			aria-label="Resize sidebar"
			aria-orientation="horizontal"
			aria-valuemin="160"
			aria-valuemax="448"
			aria-valuenow={sidebarWidth}
		></div>
	</aside>

	<!-- Overlay for mobile -->
	{#if open}
		<div
			class="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
			on:click={() => (open = false)}
			on:keydown={(e) => e.key === "Escape" && (open = false)}
			role="button"
			tabindex="0"
			aria-label="Close sidebar"
		></div>
	{/if}
</div>

<style>
	.resize-handle {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		width: 4px;
		cursor: col-resize;
		z-index: 50;
		transition: background-color 0.2s;
	}

	.resize-handle:hover,
	.resize-handle:active {
		background-color: var(--color-accent);
	}

	/* Ensure the resize handle is touch-friendly if needed, though mouse events are used */
</style>
