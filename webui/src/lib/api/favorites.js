import { api } from './client';

/**
 * Get all favorites for the current user (all libraries)
 */
export async function getFavorites() {
	return api.get('/favorites');
}

/**
 * Add comic to favorites
 */
export async function addFavorite(comicId) {
	return api.post(`/favorites/${comicId}`);
}

/**
 * Remove comic from favorites
 */
export async function removeFavorite(comicId) {
	return api.delete(`/favorites/${comicId}`);
}

/**
 * Check if a comic is in favorites
 */
export async function isFavorite(comicId) {
	try {
		const result = await api.get(`/favorites/${comicId}/check`);
		return result?.isFavorite || false;
	} catch {
		return false;
	}
}
