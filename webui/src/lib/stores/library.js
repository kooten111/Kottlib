import { writable } from 'svelte/store';

// Current library state
export const currentLibrary = writable(null);

// Libraries list
export const librariesStore = writable([]);
