/**
 * Server-side data loading for home page
 * This loads critical data on the server before rendering, significantly improving
 * Time to First Byte (TTFB) and initial page load performance.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

/**
 * Fetch wrapper for server-side API calls
 */
async function fetchAPI(path) {
	const url = `${API_BASE_URL}${path}`;
	const response = await fetch(url);

	if (!response.ok) {
		console.error(`API error: ${response.status} ${response.statusText} for ${url}`);
		throw new Error(`Failed to fetch ${path}: ${response.statusText}`);
	}

	return response.json();
}

/**
 * Load data for the home page on the server
 * Strategy: Load only critical data needed for initial render
 * - Libraries list (small, required)
 * - Series tree (large but cached, needed for sidebar)
 * - First library's continue reading (for above-the-fold content)
 *
 * Other data loads progressively on the client side
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
				continueReading: [],
				recentSeries: []
			};
		}

		// Load first library's data for initial render
		// This gives users something to see immediately while other data loads
		const firstLibrary = libraries[0];
		const [continueReading, recentSeries] = await Promise.all([
			customFetch(`/library/${firstLibrary.id}/reading?limit=20`),
			customFetch(`/library/${firstLibrary.id}/series?sort=recent`)
		]);

		return {
			libraries: libraries || [],
			seriesTree: seriesTree || [],
			firstLibrary: {
				...firstLibrary,
				continueReading: (continueReading || []).map(c => ({
					...c,
					libraryId: firstLibrary.id
				})),
				recentSeries: (recentSeries || []).slice(0, 50).map(s => ({
					...s,
					libraryId: firstLibrary.id
				}))
			}
		};
	} catch (error) {
		console.error('Server-side data loading error:', error);

		// Return empty data structure on error - client will handle loading
		return {
			libraries: [],
			seriesTree: [],
			firstLibrary: null,
			continueReading: [],
			recentSeries: [],
			serverError: error.message
		};
	}
}
