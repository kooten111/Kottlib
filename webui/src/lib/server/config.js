/**
 * Server-side Configuration for Kottlib WebUI
 *
 * Centralizes configuration values used in server-side code (+page.server.js files).
 * This eliminates the need to repeat configuration in every server file.
 *
 * Usage:
 *   import { API_BASE_URL, buildApiUrl } from '$lib/server/config.js';
 */

/**
 * Base URL for the API server (Kottlib-native endpoints)
 * Configured via API_BASE_URL environment variable, defaults to localhost for development
 */
export const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/api';

/**
 * Build a full API URL from a path
 * @param {string} path - API path (e.g., '/libraries' or '/browse/libraries/1')
 * @returns {string} Full API URL
 */
export function buildApiUrl(path) {
    // Remove leading slash if present to avoid double slashes
    const cleanPath = path.startsWith('/') ? path.slice(1) : path;
    return `${API_BASE_URL}/${cleanPath}`;
}

/**
 * Common API endpoints
 */
export const API_ENDPOINTS = {
    libraries: () => `${API_BASE_URL}/libraries`,
    seriesTree: () => `${API_BASE_URL}/libraries/tree`,
    libraryTree: (libraryId) => `${API_BASE_URL}/libraries/${libraryId}/tree`,
    libraryBrowse: (libraryId, path = '', sort = 'name') => {
        const encodedPath = path ? encodeURIComponent(path) : '';
        return `${API_BASE_URL}/browse/libraries/${libraryId}?path=${encodedPath}&sort=${sort}`;
    },
    browseAllLibraries: (sort = 'name', offset = 0, limit = 50) =>
        `${API_BASE_URL}/browse/libraries?sort=${sort}&offset=${offset}&limit=${limit}`,
    comicFullInfo: (libraryId, comicId) =>
        `${API_BASE_URL}/libraries/${libraryId}/comics/${comicId}`,
    continueReading: (limit = 50) => `${API_BASE_URL}/reading?limit=${limit}`
};

/**
 * Fetch sidebar data (libraries and series tree)
 * This is a common pattern used in multiple pages
 *
 * @param {Function} fetch - SvelteKit fetch function
 * @param {number|null} libraryId - Optional library ID to also fetch library-specific tree
 * @returns {Promise<{libraries: Array, seriesTree: Array}>}
 */
export async function fetchSidebarData(fetch, libraryId = null) {
    const urls = [
        API_ENDPOINTS.libraries(),
        API_ENDPOINTS.seriesTree()
    ];

    if (libraryId) {
        urls.push(API_ENDPOINTS.libraryTree(libraryId));
    }

    const responses = await Promise.all(urls.map(url => fetch(url)));

    const libraries = responses[0].ok ? await responses[0].json() : [];
    let seriesTree = responses[1].ok ? await responses[1].json() : [];

    // Merge library specific tree if fetched
    if (libraryId && responses[2]?.ok) {
        const libTree = await responses[2].json();
        seriesTree = seriesTree.map(node => {
            if (node.id === parseInt(libraryId)) {
                return { ...node, children: libTree.children || [] };
            }
            return node;
        });
    }

    return { libraries, seriesTree };
}
