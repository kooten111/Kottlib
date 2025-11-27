import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { getThemeById, applyTheme, DEFAULT_LIGHT_THEME, DEFAULT_DARK_THEME } from '$lib/themes';

// Get initial theme preferences from localStorage
const getInitialThemePreferences = () => {
	if (!browser) {
		return {
			mode: 'dark',
			lightTheme: DEFAULT_LIGHT_THEME,
			darkTheme: DEFAULT_DARK_THEME
		};
	}

	const stored = localStorage.getItem('themePreferences');
	if (stored) {
		try {
			return JSON.parse(stored);
		} catch (e) {
			console.error('Failed to parse theme preferences:', e);
		}
	}

	// Check system preference for initial mode
	const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

	return {
		mode: prefersDark ? 'dark' : 'light',
		lightTheme: DEFAULT_LIGHT_THEME,
		darkTheme: DEFAULT_DARK_THEME
	};
};

// Create theme store
function createThemeStore() {
	const { subscribe, set, update } = writable(getInitialThemePreferences());

	// Helper to persist and apply theme
	const persistAndApply = (preferences) => {
		if (browser) {
			localStorage.setItem('themePreferences', JSON.stringify(preferences));

			// Apply the current theme based on mode
			const themeId = preferences.mode === 'light'
				? preferences.lightTheme
				: preferences.darkTheme;
			const theme = getThemeById(themeId);
			if (theme) {
				applyTheme(theme);
			}

			// Update dark class on html element
			if (preferences.mode === 'dark') {
				document.documentElement.classList.add('dark');
			} else {
				document.documentElement.classList.remove('dark');
			}
		}
		set(preferences);
	};

	return {
		subscribe,

		// Set the entire preferences object
		set: persistAndApply,

		// Toggle between light and dark mode
		toggle: () => {
			update((current) => {
				const newPreferences = {
					...current,
					mode: current.mode === 'dark' ? 'light' : 'dark'
				};
				persistAndApply(newPreferences);
				return newPreferences;
			});
		},

		// Set the light theme (only affects light mode)
		setLightTheme: (themeId) => {
			update((current) => {
				const newPreferences = {
					...current,
					lightTheme: themeId
				};
				persistAndApply(newPreferences);
				return newPreferences;
			});
		},

		// Set the dark theme (only affects dark mode)
		setDarkTheme: (themeId) => {
			update((current) => {
				const newPreferences = {
					...current,
					darkTheme: themeId
				};
				persistAndApply(newPreferences);
				return newPreferences;
			});
		},

		// Initialize theme application (call this on mount)
		init: () => {
			update((current) => {
				persistAndApply(current);
				return current;
			});
		}
	};
}

export const themeStore = createThemeStore();
