import { api } from './client';

/**
 * Get all reading lists for a library
 */
export async function getReadingLists(libraryId) {
	return api.get(`/libraries/${libraryId}/reading-lists`);
}

/**
 * Get reading list info
 */
export async function getReadingListInfo(libraryId, listId) {
	return api.get(`/libraries/${libraryId}/reading-lists/${listId}`);
}

/**
 * Get comics in a reading list
 */
export async function getReadingListContent(libraryId, listId) {
	return api.get(`/libraries/${libraryId}/reading-lists/${listId}/items`);
}

/**
 * Create a new reading list
 */
export async function createReadingList(libraryId, name, description = '', isPublic = false) {
	return api.post(`/libraries/${libraryId}/reading-lists?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}&is_public=${isPublic}`);
}

/**
 * Delete a reading list
 */
export async function deleteReadingList(libraryId, listId) {
	return api.delete(`/libraries/${libraryId}/reading-lists/${listId}`);
}

/**
 * Update a reading list (name, description, is_public)
 */
export async function updateReadingList(libraryId, listId, { name, description, is_public } = {}) {
	return api.patch(`/libraries/${libraryId}/reading-lists/${listId}`, {
		...(name !== undefined && { name }),
		...(description !== undefined && { description }),
		...(is_public !== undefined && { is_public })
	});
}

/**
 * Add a comic to a reading list
 */
export async function addComicToReadingList(libraryId, listId, comicId) {
	return api.post(`/libraries/${libraryId}/reading-lists/${listId}/items/${comicId}`);
}

/**
 * Remove a comic from a reading list
 */
export async function removeComicFromReadingList(libraryId, listId, comicId) {
	return api.delete(`/libraries/${libraryId}/reading-lists/${listId}/items/${comicId}`);
}
