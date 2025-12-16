import { writable } from 'svelte';

/**
 * UI state store for managing global UI state like sidebar visibility
 */
function createUIStore() {
	const { subscribe, set, update } = writable({
		isSidebarOpen: false,
	});

	return {
		subscribe,
		openSidebar: () => update(state => ({ ...state, isSidebarOpen: true })),
		closeSidebar: () => update(state => ({ ...state, isSidebarOpen: false })),
		toggleSidebar: () => update(state => ({ ...state, isSidebarOpen: !state.isSidebarOpen })),
	};
}

export const uiStore = createUIStore();
