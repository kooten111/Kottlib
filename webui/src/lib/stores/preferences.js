import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Default preferences
const defaultPreferences = {
	gridCoverSize: 1.0, // Multiplier for grid view cover size (0.5 to 2.0)
	folderCoverSizes: {}, // Per-folder cover size preferences: { "libraryId:path": size }
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

	// Helper to persist preferences and return them
	function persistAndReturn(newPrefs) {
		if (browser) {
			localStorage.setItem('libraryPreferences', JSON.stringify(newPrefs));
		}
		return newPrefs;
	}

	return {
		subscribe,
		set: (value) => {
			if (browser) {
				localStorage.setItem('libraryPreferences', JSON.stringify(value));
			}
			set(value);
		},
		update: (fn) => {
			update((current) => persistAndReturn(fn(current)));
		},
		setGridCoverSize: (size) => {
			update((current) => persistAndReturn({ ...current, gridCoverSize: size }));
		},
		setFolderCoverSize: (size, libraryId, path = "") => {
			update((current) => {
				const key = `${libraryId}:${path || ''}`;
				return persistAndReturn({
					...current,
					folderCoverSizes: {
						...(current.folderCoverSizes || {}),
						[key]: size
					}
				});
			});
		},
		getFolderCoverSize: (libraryId, path = "") => {
			// Helper to get value, though usually accessed via store subscription in components
			let val = 1.0;
			const unsubscribe = subscribe(p => {
				const key = `${libraryId}:${path || ''}`;
				val = p.folderCoverSizes?.[key] ?? p.gridCoverSize ?? 1.0;
			});
			unsubscribe();
			return val;
		},
		setViewMode: (mode) => {
			update((current) => persistAndReturn({ ...current, viewMode: mode }));
		},
		toggleViewMode: () => {
			update((current) => {
				const newMode = current.viewMode === 'grid' ? 'list' : 'grid';
				return persistAndReturn({ ...current, viewMode: newMode });
			});
		},
		setSortBy: (sortValue, libraryId = null) => {
			update((current) => {
				if (libraryId !== null) {
					// Set sort for specific library
					return persistAndReturn({
						...current,
						librarySortBy: {
							...(current.librarySortBy || {}),
							[libraryId]: sortValue
						}
					});
				} else {
					// Set global sort
					return persistAndReturn({ ...current, sortBy: sortValue });
				}
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
