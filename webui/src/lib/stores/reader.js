import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Get saved reader settings
const getSavedSettings = () => {
	if (!browser) {
		return getDefaultSettings();
	}

	const saved = localStorage.getItem('readerSettings');
	return saved ? JSON.parse(saved) : getDefaultSettings();
};

const getDefaultSettings = () => ({
	fitMode: 'fit-width', // fit-width, fit-height, original
	readingMode: 'single', // single, double, continuous
	readingDirection: 'ltr', // ltr, rtl (manga mode)
	preloadPages: 3, // Increased from 2 for better swipe preview experience
	backgroundColor: '#1a1a1a',
	autoHideControls: true,
	autoHideDelay: 3000
});

// Create reader settings store
function createReaderStore() {
	const { subscribe, set, update } = writable(getSavedSettings());

	return {
		subscribe,
		update: (updater) => {
			update((current) => {
				const updated = updater(current);
				if (browser) {
					localStorage.setItem('readerSettings', JSON.stringify(updated));
				}
				return updated;
			});
		},
		set: (value) => {
			if (browser) {
				localStorage.setItem('readerSettings', JSON.stringify(value));
			}
			set(value);
		},
		reset: () => {
			const defaults = getDefaultSettings();
			if (browser) {
				localStorage.setItem('readerSettings', JSON.stringify(defaults));
			}
			set(defaults);
		}
	};
}

export const readerSettings = createReaderStore();
