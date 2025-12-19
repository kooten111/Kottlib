import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Default preferences
const defaultPreferences = {
	gridCoverSize: 1.0, // Multiplier for grid view cover size (0.5 to 2.0)
	viewMode: 'grid', // 'grid' or 'list'
	sortBy: 'name', // Global sort option: 'name', 'recent-read', 'progress', 'recent', 'shuffle'
	librarySortBy: {} // Per-library sort preferences: { libraryId: sortMode }
};

// Get initial preferences from localStorage
const getInitialPreferences = () => {
	if (!browser) return defaultPreferences;

	const stored = localStorage.getItem('libraryPreferences');
	if (stored) {
		try {
			return { ...defaultPreferences, ...JSON.parse(stored) };
		} catch (e) {
			console.error('Failed to parse preferences:', e);
			return defaultPreferences;
		}
	}

	return defaultPreferences;
};

// Create preferences store
function createPreferencesStore() {
	const { subscribe, set, update } = writable(getInitialPreferences());

	return {
		subscribe,
		set: (value) => {
			if (browser) {
				localStorage.setItem('libraryPreferences', JSON.stringify(value));
			}
			set(value);
		},
		update: (fn) => {
			update((current) => {
				const newPrefs = fn(current);
				if (browser) {
					localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
				}
				return newPrefs;
			});
		},
		setGridCoverSize: (size) => {
			update((current) => {
				const newPrefs = { ...current, gridCoverSize: size };
				if (browser) {
					localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
				}
				return newPrefs;
			});
		},
		setViewMode: (mode) => {
			update((current) => {
				const newPrefs = { ...current, viewMode: mode };
				if (browser) {
					localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
				}
				return newPrefs;
			});
		},
		toggleViewMode: () => {
			update((current) => {
				const newMode = current.viewMode === 'grid' ? 'list' : 'grid';
				const newPrefs = { ...current, viewMode: newMode };
				if (browser) {
					localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
				}
				return newPrefs;
			});
		},
		setSortBy: (sortValue, libraryId = null) => {
			update((current) => {
				let newPrefs;
				if (libraryId !== null) {
					// Set sort for specific library
					newPrefs = {
						...current,
						librarySortBy: {
							...(current.librarySortBy || {}),
							[libraryId]: sortValue
						}
					};
				} else {
					// Set global sort
					newPrefs = { ...current, sortBy: sortValue };
				}
				if (browser) {
					localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
				}
				return newPrefs;
			});
		},
		getSortBy: (libraryId = null) => {
			let currentPrefs;
			const unsubscribe = subscribe((prefs) => {
				currentPrefs = prefs;
			});
			unsubscribe();

			if (libraryId !== null && currentPrefs.librarySortBy && currentPrefs.librarySortBy[libraryId]) {
				return currentPrefs.librarySortBy[libraryId];
			}
			return currentPrefs.sortBy || 'name';
		}
	};
}

export const preferencesStore = createPreferencesStore();
