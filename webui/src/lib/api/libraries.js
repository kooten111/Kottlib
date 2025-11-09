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
export async function getFolderContents(libraryId, folderId = '__ROOT__') {
	return api.get(`/library/${libraryId}/folder/${folderId}`);
}

/**
 * Get continue reading list
 */
export async function getContinueReading(libraryId, limit = 10) {
	return api.get(`/library/${libraryId}/reading?limit=${limit}`);
}
