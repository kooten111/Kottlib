import { api } from './client';

/**
 * Get all reading lists for a library
 */
export async function getReadingLists(libraryId) {
	return api.get(`/library/${libraryId}/reading_lists`);
}

/**
 * Get reading list info
 */
export async function getReadingListInfo(libraryId, listId) {
	return api.get(`/library/${libraryId}/reading_list/${listId}/info`);
}

/**
 * Get comics in a reading list
 */
export async function getReadingListContent(libraryId, listId) {
	return api.get(`/library/${libraryId}/reading_list/${listId}/content`);
}

/**
 * Create a new reading list
 */
export async function createReadingList(libraryId, name, description = '', isPublic = false) {
	return api.post(`/library/${libraryId}/reading_list?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}&is_public=${isPublic}`);
}

/**
 * Delete a reading list
 */
export async function deleteReadingList(libraryId, listId) {
	return api.delete(`/library/${libraryId}/reading_list/${listId}`);
}

/**
 * Update a reading list (name, description, is_public)
 */
export async function updateReadingList(libraryId, listId, { name, description, is_public } = {}) {
	return api.patch(`/library/${libraryId}/reading_list/${listId}`, {
		...(name !== undefined && { name }),
		...(description !== undefined && { description }),
		...(is_public !== undefined && { is_public })
	});
}

/**
 * Add a comic to a reading list
 */
export async function addComicToReadingList(libraryId, listId, comicId) {
	return api.post(`/library/${libraryId}/reading_list/${listId}/comic/${comicId}`);
}

/**
 * Remove a comic from a reading list
 */
export async function removeComicFromReadingList(libraryId, listId, comicId) {
	return api.delete(`/library/${libraryId}/reading_list/${listId}/comic/${comicId}`);
}
