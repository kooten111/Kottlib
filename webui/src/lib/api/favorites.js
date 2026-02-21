import { api } from './client';

/**
 * Get all favorites for the current user (all libraries)
 */
export async function getFavorites() {
	return api.get('/v2/favs');
}

/**
 * Add comic to favorites
 */
export async function addFavorite(comicId) {
	return api.post(`/v2/fav/${comicId}`);
}

/**
 * Remove comic from favorites
 */
export async function removeFavorite(comicId) {
	return api.delete(`/v2/fav/${comicId}`);
}
