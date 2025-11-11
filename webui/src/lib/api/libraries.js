import { api } from './client';

/**
 * Get all libraries
 */
export async function getLibraries() {
	return api.get('/libraries');
}

/**
 * Get library info by ID
 */
export async function getLibrary(libraryId) {
	return api.get(`/library/${libraryId}/info`);
}

/**
 * Get folder contents
 */
export async function getFolderContents(libraryId, folderId = 0) {
	// Convert __ROOT__ to folder ID 0 (root folder convention)
	const actualFolderId = folderId === '__ROOT__' ? 0 : folderId;
	return api.get(`/library/${libraryId}/folder/${actualFolderId}`);
}

/**
 * Get continue reading list
 */
export async function getContinueReading(libraryId, limit = 10) {
	return api.get(`/library/${libraryId}/reading?limit=${limit}`);
}

/**
 * Get folder tree for a library
 */
export async function getFolderTree(libraryId, maxDepth = 10) {
	return api.get(`/library/${libraryId}/tree?max_depth=${maxDepth}`);
}

/**
 * Get all series in a library
 */
export async function getSeries(libraryId, sort = 'name') {
	return api.get(`/library/${libraryId}/series?sort=${sort}`);
}

/**
 * Get detailed information about a specific series
 */
export async function getSeriesDetail(libraryId, seriesName) {
	const encodedName = encodeURIComponent(seriesName);
	return api.get(`/library/${libraryId}/series/${encodedName}`);
}

/**
 * Get hierarchical tree of all libraries with series and comics
 */
export async function getLibrariesSeriesTree() {
	return api.get('/libraries/series-tree');
}
