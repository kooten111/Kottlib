import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { getLibrary, updateLibrary } from '$lib/api/libraries';

const getDefaultSettings = () => ({
	fitMode: 'fit-height', // fit-width, fit-height, original
	readingMode: 'single', // single, double, continuous
	readingDirection: 'ltr', // ltr, rtl (manga mode)
	preloadPages: 3, // Increased from 2 for better swipe preview experience
	backgroundColor: '#1a1a1a',
	autoHideControls: true,
	autoHideDelay: 3000
});

// Get saved reader settings from localStorage (synchronous)
const getSavedSettings = () => {
	if (!browser) {
		return getDefaultSettings();
	}

	const saved = localStorage.getItem('readerSettings');
	return saved ? JSON.parse(saved) : getDefaultSettings();
};

// Get library-specific reader defaults from API
async function getLibraryReaderDefaults(libraryId) {
	if (!browser || !libraryId) {
		return null;
	}

	try {
		const library = await getLibrary(libraryId);
		if (library?.settings?.reader_defaults) {
			return library.settings.reader_defaults;
		}
	} catch (error) {
		console.error('Failed to fetch library reader defaults:', error);
	}
	return null;
}

// Save library-specific reader defaults via API
async function saveLibraryReaderDefaults(libraryId, settings) {
	if (!browser || !libraryId) {
		return;
	}

	try {
		// Get current library settings
		const library = await getLibrary(libraryId);
		const currentSettings = library?.settings || {};
		
		// Update reader_defaults
		const updatedSettings = {
			...currentSettings,
			reader_defaults: settings
		};

		// Save via API
		await updateLibrary(libraryId, { settings: updatedSettings });
	} catch (error) {
		console.error('Failed to save library reader defaults:', error);
	}
}

// Get settings with library fallback chain (async)
async function getSettingsWithLibraryFallback(libraryId = null) {
	if (!browser) {
		return getDefaultSettings();
	}

	// First, check for library-specific defaults
	if (libraryId) {
		const libraryDefaults = await getLibraryReaderDefaults(libraryId);
		if (libraryDefaults) {
			// Merge with hard-coded defaults to ensure all fields are present
			return { ...getDefaultSettings(), ...libraryDefaults };
		}
	}

	// Fall back to global localStorage settings
	return getSavedSettings();
}

// Create reader settings store
function createReaderStore() {
	const { subscribe, set, update } = writable(getSavedSettings());
	let currentLibraryId = null;
	const libraryIdStore = writable(null);

	return {
		subscribe,
		libraryId: {
			subscribe: libraryIdStore.subscribe
		},
		loadForLibrary: async (libraryId) => {
			currentLibraryId = libraryId;
			libraryIdStore.set(libraryId);
			const settings = await getSettingsWithLibraryFallback(libraryId);
			set(settings);
		},
		setLibraryId: (libraryId) => {
			currentLibraryId = libraryId;
			libraryIdStore.set(libraryId);
		},
		update: (updater) => {
			update((current) => {
				const updated = updater(current);
				if (browser) {
					// Always save to localStorage for backward compatibility
					localStorage.setItem('readerSettings', JSON.stringify(updated));
					
					// Also save to library defaults if libraryId is set
					if (currentLibraryId) {
						saveLibraryReaderDefaults(currentLibraryId, updated).catch(err => {
							console.error('Failed to save library defaults:', err);
						});
					}
				}
				return updated;
			});
		},
		set: (value) => {
			if (browser) {
				localStorage.setItem('readerSettings', JSON.stringify(value));
				
				// Also save to library defaults if libraryId is set
				if (currentLibraryId) {
					saveLibraryReaderDefaults(currentLibraryId, value).catch(err => {
						console.error('Failed to save library defaults:', err);
					});
				}
			}
			set(value);
		},
		reset: () => {
			const defaults = getDefaultSettings();
			if (browser) {
				localStorage.setItem('readerSettings', JSON.stringify(defaults));
				
				// Also save to library defaults if libraryId is set
				if (currentLibraryId) {
					saveLibraryReaderDefaults(currentLibraryId, defaults).catch(err => {
						console.error('Failed to save library defaults:', err);
					});
				}
			}
			set(defaults);
		}
	};
}

export const readerSettings = createReaderStore();
