import { writable } from 'svelte/store';

// Current library state
export const currentLibrary = writable(null);

// Libraries list
export const librariesStore = writable([]);

// Navigation context for filtering continue reading
// Structure: { type: 'all' | 'library' | 'series', libraryId?: number, seriesName?: string }
export const navigationContext = writable({ type: 'all' });
