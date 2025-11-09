import { api } from './client';

/**
 * Get all favorites for a library
 */
export async function getFavorites(libraryId) {
	return api.get(`/library/${libraryId}/favs`);
}

/**
 * Add comic to favorites
 */
export async function addFavorite(libraryId, comicId) {
	return api.post(`/library/${libraryId}/comic/${comicId}/fav`);
}

/**
 * Remove comic from favorites
 */
export async function removeFavorite(libraryId, comicId) {
	return api.delete(`/library/${libraryId}/comic/${comicId}/fav`);
}
