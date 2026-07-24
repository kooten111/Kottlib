import { appApi } from './client';

/**
 * Get full comic information
 */
export async function getComic(libraryId, comicId) {
	const comic = await appApi.get(`/libraries/${libraryId}/comics/${comicId}`);

	// Convert 0-based page index to 1-based for frontend
	if (typeof comic.current_page === 'number' && comic.current_page > 0) {
		comic.current_page += 1;
	}

	return comic;
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
	// Convert 1-based page to 0-based index for API
	const pageIndex = Math.max(0, page - 1);
	return appApi.getBlob(`/libraries/${libraryId}/comics/${comicId}/pages/${pageIndex}/remote`);
}

/**
 * Build a cacheable comic page URL for <img> / Image() preload.
 * When PUBLIC_BACKEND_URL is set, requests go directly to the backend
 * (same pattern as covers) so large page JPEGs skip the SvelteKit proxy.
 */
export function getComicPageUrl(libraryId, comicId, page) {
	const pageIndex = Math.max(0, page - 1);
	const base =
		(typeof import.meta !== 'undefined' &&
			import.meta.env &&
			import.meta.env.PUBLIC_BACKEND_URL) ||
		'';
	const normalized = String(base).replace(/\/$/, '');
	return `${normalized}/api/libraries/${libraryId}/comics/${comicId}/pages/${pageIndex}/remote`;
}

/**
 * Warm the browser HTTP cache for a page URL (does not create blob URLs).
 */
export function preloadComicPageUrl(url) {
	return new Promise((resolve, reject) => {
		if (typeof Image === 'undefined') {
			resolve(url);
			return;
		}
		const img = new Image();
		img.onload = () => resolve(url);
		img.onerror = () => reject(new Error(`Failed to preload page: ${url}`));
		img.src = url;
	});
}

/**
 * Update comic reading progress
 * Note: YACReader API expects plain text format "currentPage:N", not JSON
 */
export async function updateReadingProgress(libraryId, comicId, currentPage) {
	// Convert 1-based page to 0-based index for API
	const pageIndex = Math.max(0, currentPage - 1);
	return appApi.post(`/libraries/${libraryId}/comics/${comicId}/progress`, {
		current_page: pageIndex
	});
}

/**
 * Get previous comic in series
 */
export async function getPreviousComic(libraryId, comicId) {
	return appApi.get(`/libraries/${libraryId}/comics/${comicId}/previous`);
}

/**
 * Get next comic in series
 */
export async function getNextComic(libraryId, comicId) {
	return appApi.get(`/libraries/${libraryId}/comics/${comicId}/next`);
}

/**
 * Get comic cover URL.
 * Prefer WebP (WebUI); JPEG remains available for the YACReader app/API.
 * When PUBLIC_BACKEND_URL is set, covers bypass the SvelteKit proxy.
 */
export function getCoverUrl(libraryId, coverHash, format = 'webp') {
	const base =
		(typeof import.meta !== 'undefined' &&
			import.meta.env &&
			import.meta.env.PUBLIC_BACKEND_URL) ||
		'';
	const normalized = String(base).replace(/\/$/, '');
	return `${normalized}/api/libraries/${libraryId}/covers/${coverHash}.${format}`;
}
