import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// Get initial theme from localStorage or default to 'dark'
const getInitialTheme = () => {
	if (!browser) return 'dark';

	const stored = localStorage.getItem('theme');
	if (stored) return stored;

	// Check system preference
	if (window.matchMedia('(prefers-color-scheme: light)').matches) {
		return 'light';
	}

	return 'dark';
};

// Create theme store
function createThemeStore() {
	const { subscribe, set, update } = writable(getInitialTheme());

	return {
		subscribe,
		set: (value) => {
			if (browser) {
				localStorage.setItem('theme', value);
			}
			set(value);
		},
		toggle: () => {
			update((current) => {
				const newTheme = current === 'dark' ? 'light' : 'dark';
				if (browser) {
					localStorage.setItem('theme', newTheme);
				}
				return newTheme;
			});
		}
	};
}

export const themeStore = createThemeStore();
