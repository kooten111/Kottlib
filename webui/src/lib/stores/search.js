import { writable } from 'svelte/store';

export const searchStore = writable({
	query: '',
	isSearching: false
});

export function setSearchQuery(query) {
	searchStore.update(state => ({
		...state,
		query
	}));
}

export function setSearching(isSearching) {
	searchStore.update(state => ({
		...state,
		isSearching
	}));
}
