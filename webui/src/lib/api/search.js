import { api } from './client';

/**
 * Search comics in a library (basic search)
 */
export async function searchComics(libraryId, query, options = {}) {
	const params = new URLSearchParams({
		q: query,
		...options
	});

	return api.get(`/libraries/${libraryId}/search?${params}`);
}

/**
 * Advanced search with pagination
 */
export async function searchComicsAdvanced(libraryId, query, { limit = 100, offset = 0 } = {}) {
	const params = new URLSearchParams({
		q: query,
		limit: limit.toString(),
		offset: offset.toString()
	});

	return api.get(`/libraries/${libraryId}/search/advanced?${params}`);
}

/**
 * Get searchable fields for a library
 */
export async function getSearchableFields(libraryId) {
	return api.get(`/libraries/${libraryId}/search/fields`);
}

/**
 * Parse a search query (for debugging/preview)
 */
export async function parseSearchQuery(query) {
	const params = new URLSearchParams({ q: query });
	return api.get(`/search/query/parse?${params}`);
}
