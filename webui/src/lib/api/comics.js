import { api } from './client';

/**
 * Get full comic information
 */
export async function getComic(libraryId, comicId) {
	return api.get(`/library/${libraryId}/comic/${comicId}/fullinfo`);
}

/**
 * Get comic info (alias for getComic)
 */
export async function getComicInfo(libraryId, comicId) {
	return getComic(libraryId, comicId);
}

/**
 * Get comic page image
 */
export async function getComicPage(libraryId, comicId, page) {
	return api.getBlob(`/library/${libraryId}/comic/${comicId}/page/${page}/remote`);
}

/**
 * Update comic reading progress
 * Note: YACReader API expects plain text format "currentPage:N", not JSON
 */
export async function updateReadingProgress(libraryId, comicId, currentPage) {
	const response = await fetch(`/v2/library/${libraryId}/comic/${comicId}/update`, {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'text/plain'
		},
		body: `currentPage:${currentPage}`
	});

	if (!response.ok) {
		throw new Error(`Failed to update progress: ${response.statusText}`);
	}

	return response.json();
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
