import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Default preferences
const defaultPreferences = {
	gridCoverSize: 1.0, // Multiplier for grid view cover size (0.5 to 2.0)
	viewMode: 'grid' // 'grid' or 'list'
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
		}
	};
}

export const preferencesStore = createPreferencesStore();
