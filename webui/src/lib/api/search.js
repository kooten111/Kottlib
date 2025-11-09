import { api } from './client';

/**
 * Search comics in a library
 */
export async function searchComics(libraryId, query, options = {}) {
	const params = new URLSearchParams({
		q: query,
		...options
	});

	return api.get(`/library/${libraryId}/search?${params}`);
}
