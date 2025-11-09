import { api } from './client';

/**
 * Get full comic information
 */
export async function getComic(libraryId, comicId) {
	return api.get(`/library/${libraryId}/comic/${comicId}/fullinfo`);
}

/**
 * Get comic page image
 */
export async function getComicPage(libraryId, comicId, page) {
	return api.getBlob(`/library/${libraryId}/comic/${comicId}/page/${page}/remote`);
}

/**
 * Update comic reading progress
 */
export async function updateReadingProgress(libraryId, comicId, currentPage) {
	return api.post(`/library/${libraryId}/comic/${comicId}/update`, {
		currentPage
	});
}

/**
 * Get previous comic in series
 */
export async function getPreviousComic(libraryId, comicId) {
	return api.get(`/library/${libraryId}/comic/${comicId}/previousComic`);
}

/**
 * Get next comic in series
 */
export async function getNextComic(libraryId, comicId) {
	return api.get(`/library/${libraryId}/comic/${comicId}/nextComic`);
}

/**
 * Get comic cover
 */
export function getCoverUrl(libraryId, coverHash, format = 'jpg') {
	return `/v2/library/${libraryId}/cover/${coverHash}.${format}`;
}
