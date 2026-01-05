/**
 * Cache warming utility
 * Pre-loads commonly accessed data into IndexedDB cache
 */

import { getLibraries, getSeries, getContinueReading, getLibrariesSeriesTree } from '$lib/api/libraries';
import { getCacheStats, clearExpired } from './persistentCache';

/**
 * Warm up the cache by pre-loading common data
 * This runs in the background after the page is loaded
 */
export async function warmCache() {


	try {
		// Clear expired entries first
		await clearExpired();

		// Load libraries and series tree (most commonly accessed)
		const libraries = await getLibraries();
		await getLibrariesSeriesTree();



		// Pre-load each library's data in the background
		for (const library of libraries) {
			try {
				// Small delay between requests to avoid overwhelming the server
				await new Promise(resolve => setTimeout(resolve, 500));

				// Load library data
				await Promise.all([
					getContinueReading(library.id, 50),
					getSeries(library.id, 'recent')
				]);


			} catch (error) {
				console.error(`[Cache Warmer] Failed to cache library ${library.id}:`, error);
			}
		}

		const stats = await getCacheStats();


		return stats;
	} catch (error) {
		console.error('[Cache Warmer] Error:', error);
	}
}

/**
 * Schedule cache warming for when the browser is idle
 */
export function scheduleCacheWarming() {
	if (typeof window === 'undefined') return;

	// Use requestIdleCallback if available, otherwise setTimeout
	if ('requestIdleCallback' in window) {
		requestIdleCallback(
			() => {
				warmCache();
			},
			{ timeout: 5000 } // Maximum 5 second delay
		);
	} else {
		setTimeout(() => {
			warmCache();
		}, 2000); // Start after 2 seconds
	}
}

/**
 * Get cache health status
 */
export async function getCacheHealth() {
	const stats = await getCacheStats();

	const health = {
		healthy: stats.valid > 0,
		entries: stats.total,
		validEntries: stats.valid,
		expiredEntries: stats.expired,
		totalSizeKB: stats.totalSize,
		hitRate: null, // Would need to track hits/misses separately
		details: stats.entries
	};

	return health;
}

/**
 * Refresh cache for a specific library
 */
export async function refreshLibraryCache(libraryId) {


	try {
		await Promise.all([
			getContinueReading(libraryId, 50),
			getSeries(libraryId, 'recent')
		]);


		return true;
	} catch (error) {
		console.error(`[Cache Warmer] Failed to refresh library ${libraryId}:`, error);
		return false;
	}
}
