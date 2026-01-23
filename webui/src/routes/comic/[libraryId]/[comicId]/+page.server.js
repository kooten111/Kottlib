/**
 * Server-side data loading for comic detail page
 * Fetches comic info and sidebar data (libraries, series tree)
 */

import { API_ENDPOINTS, fetchSidebarData } from '$lib/server/config.js';

export async function load({ params, fetch }) {
    const { libraryId, comicId } = params;

    try {
        // Fetch comic info and sidebar data in parallel
        const [comicRes, sidebarData] = await Promise.all([
            fetch(API_ENDPOINTS.comicFullInfo(libraryId, comicId)),
            fetchSidebarData(fetch, libraryId)
        ]);

        if (!comicRes.ok) {
            console.error(`Failed to load comic: ${comicRes.status} ${comicRes.statusText}`);
            return {
                comic: null,
                error: `Failed to load comic: ${comicRes.statusText}`,
                libraries: [],
                seriesTree: [],
                libraryId: parseInt(libraryId),
                comicId: parseInt(comicId)
            };
        }

        const comic = await comicRes.json();

        return {
            comic,
            libraries: sidebarData.libraries,
            seriesTree: sidebarData.seriesTree,
            libraryId: parseInt(libraryId),
            comicId: parseInt(comicId),
            error: null
        };

    } catch (error) {
        console.error('Server-side comic load error:', error);
        return {
            comic: null,
            error: error.message,
            libraries: [],
            seriesTree: [],
            libraryId: parseInt(libraryId),
            comicId: parseInt(comicId)
        };
    }
}
