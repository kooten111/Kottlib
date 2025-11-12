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
				continueReading: [],
				recentSeries: []
			};
		}

		// Load data from ALL libraries
		const [continueReadingResults, allSeriesResults] = await Promise.all([
			// Continue reading from all libraries
			Promise.all(
				libraries.map(async (lib) => {
					try {
						const comics = await customFetch(`/library/${lib.id}/reading?limit=50`);
						return comics ? comics.map(comic => ({ ...comic, libraryId: lib.id })) : [];
					} catch {
						return [];
					}
				})
			),
			// All series from all libraries
			Promise.all(
				libraries.map(async (lib) => {
					try {
						const series = await customFetch(`/library/${lib.id}/series?sort=recent`);
						return series ? series.map(s => ({ ...s, libraryId: lib.id })) : [];
					} catch (err) {
						console.error(`Failed to fetch series for library ${lib.id}:`, err);
						return [];
					}
				})
			)
		]);

		// Flatten and combine continue reading from all libraries
		const continueReading = continueReadingResults.flat().slice(0, 20);

		// Interleave series from different libraries for variety
		const maxLength = Math.max(...allSeriesResults.map(r => r.length));
		const allSeries = [];
		for (let i = 0; i < maxLength; i++) {
			for (const libraryResults of allSeriesResults) {
				if (i < libraryResults.length) {
					allSeries.push(libraryResults[i]);
				}
			}
		}

		return {
			libraries: libraries || [],
			seriesTree: seriesTree || [],
			firstLibrary: {
				continueReading: continueReading,
				recentSeries: allSeries  // Return all series, not just 50
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
