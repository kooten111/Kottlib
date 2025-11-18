import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Current library state
export const currentLibrary = writable(null);

// Libraries list
export const librariesStore = writable([]);

// Navigation context for filtering continue reading
// Structure: { type: 'all' | 'library' | 'series', libraryId?: number, seriesName?: string }
export const navigationContext = writable({ type: 'all' });

// Create a persisted writable store that saves to localStorage
function createPersistedStore(key, initialValue) {
	// Initialize from localStorage if available
	let storedValue = initialValue;
	if (browser) {
		const stored = localStorage.getItem(key);
		if (stored) {
			try {
				storedValue = JSON.parse(stored);
			} catch (e) {
				console.error(`Failed to parse stored value for ${key}:`, e);
			}
		}
	}

	const store = writable(storedValue);

	// Subscribe to changes and persist to localStorage
	if (browser) {
		store.subscribe(value => {
			if (value === null || value === undefined) {
				localStorage.removeItem(key);
			} else {
				localStorage.setItem(key, JSON.stringify(value));
			}
		});
	}

	return store;
}

// Current filter state (persisted across navigation)
// Structure: { type: 'all' | 'library' | 'folder', libraryId?: number, folderId?: number, folderName?: string, libraryName?: string }
export const currentFilterStore = createPersistedStore('yaclib-current-filter', null);

// Tree expansion state - controls which nodes are expanded in the sidebar tree
// Set of node IDs that are currently expanded
export const treeExpandedNodes = writable(new Set(['libraries-root']));
