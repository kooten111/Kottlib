/**
 * Server-side data loading for home page
 * This loads critical data on the server before rendering, significantly improving
 * Time to First Byte (TTFB) and initial page load performance.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

/**
 * Load data for the home page on the server
 * Loads data from ALL libraries on initial render
 */
export async function load({ fetch: svelteKitFetch }) {
	try {
		// Use SvelteKit's fetch for better cookie/auth handling
		const customFetch = async (path) => {
			const url = `${API_BASE_URL}${path}`;
			const response = await svelteKitFetch(url);

			if (!response.ok) {
				console.error(`API error: ${response.status} ${response.statusText} for ${url}`);
				return null;
			}

			return response.json();
		};

		// Load critical data in parallel
		const [libraries, seriesTree] = await Promise.all([
			customFetch('/libraries'),
			customFetch('/libraries/series-tree')
		]);

		// If no libraries, return early
		if (!libraries || libraries.length === 0) {
			return {
				libraries: [],
				seriesTree: [],
				firstLibrary: null,
				isPartialLoad: false
			};
		}

		// PERFORMANCE OPTIMIZATION: Only load FIRST library's data on SSR
		// Remaining libraries will be loaded in background on client
		const firstLibrary = libraries[0];

		const [continueReading, libraryFolders] = await Promise.all([
			customFetch(`/library/${firstLibrary.id}/reading?limit=50`),
			customFetch(`/library/${firstLibrary.id}/folders`)
		]);

		return {
			libraries: libraries || [],
			seriesTree: seriesTree || [],
			firstLibrary: {
				id: firstLibrary.id,
				continueReading: continueReading ? continueReading.map(comic => ({ ...comic, libraryId: firstLibrary.id })) : [],
				folders: libraryFolders ? libraryFolders.map(f => ({ ...f, libraryId: firstLibrary.id })) : []
			},
			// Flag to indicate only first library loaded, rest need background loading
			isPartialLoad: libraries.length > 1
		};
	} catch (error) {
		console.error('Server-side data loading error:', error);

		// Return empty data structure on error - client will handle loading
		return {
			libraries: [],
			seriesTree: [],
			firstLibrary: null,
			isPartialLoad: false,
			serverError: error.message
		};
	}
}
