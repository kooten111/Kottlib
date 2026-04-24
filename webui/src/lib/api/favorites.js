import { appApi } from './client';

/**
 * Get all favorites for the current user (all libraries)
 */
export async function getFavorites() {
	return appApi.get('/favorites');
}

/**
 * Add comic to favorites
 */
export async function addFavorite(comicId) {
	return appApi.post(`/favorites/${comicId}`);
}

/**
 * Remove comic from favorites
 */
export async function removeFavorite(comicId) {
	return appApi.delete(`/favorites/${comicId}`);
}

/**
 * Check if a comic is in favorites
 */
export async function isFavorite(comicId, options = {}) {
	try {
		const result = await appApi.get(`/favorites/${comicId}/check`, options);
		return result?.isFavorite || false;
	} catch {
		return false;
	}
}
