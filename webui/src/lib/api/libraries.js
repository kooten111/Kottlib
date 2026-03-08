import { appApi } from './client';

/**
 * Get all libraries
 */
export async function getLibraries() {
	return appApi.get('/libraries');
}

/**
 * Create a new library
 */
export async function createLibrary(data) {
	return appApi.post('/libraries', data);
}

/**
 * Update a library
 */
export async function updateLibrary(libraryId, data) {
	return appApi.put(`/libraries/${libraryId}`, data);
}

/**
 * Delete a library
 */
export async function deleteLibrary(libraryId) {
	return appApi.delete(`/libraries/${libraryId}`);
}

/**
 * Trigger a manual scan for a library
 */
export async function scanLibrary(libraryId) {
	return appApi.post(`/libraries/${libraryId}/scan`);
}

/**
 * Get library info by ID
 */
export async function getLibrary(libraryId) {
	return appApi.get(`/libraries/${libraryId}`);
}

/**
 * Get continue reading list for a specific library
 */
export async function getContinueReading(libraryId, limit = 10) {
	return appApi.get(`/libraries/${libraryId}/reading?limit=${limit}`);
}

/**
 * Get continue reading list from ALL libraries (cross-library, sorted by last_read_at)
 */
export async function getContinueReadingAll(limit = 100) {
	return appApi.get(`/reading?limit=${limit}`);
}

/**
 * Get all series in a library
 */
export async function getSeries(libraryId, sort = 'name', offset = 0, limit = 50) {
	return appApi.get(`/libraries/${libraryId}/series?sort=${sort}&offset=${offset}&limit=${limit}`);
}

/**
 * Get hierarchical tree of all libraries with series and comics
 */
export async function getLibrariesSeriesTree() {
	return appApi.get('/libraries/tree');
}

/**
 * Browse library folder
 */
export async function browseLibrary(libraryId, path = '', sort = 'name', offset = 0, limit = 50, seed = null) {
	let pathParam = path ? `&path=${encodeURIComponent(path)}` : '';
	if (seed) {
		pathParam += `&seed=${seed}`;
	}
	return appApi.get(`/browse/libraries/${libraryId}?sort=${sort}&offset=${offset}&limit=${limit}${pathParam}`);
}

/**
 * Browse content from all libraries
 */
export async function browseAllLibraries(sort = 'name', offset = 0, limit = 50, seed = null) {
	let url = `/browse/libraries?sort=${sort}&offset=${offset}&limit=${limit}`;
	if (seed) {
		url += `&seed=${seed}`;
	}
	return appApi.get(url);
}
