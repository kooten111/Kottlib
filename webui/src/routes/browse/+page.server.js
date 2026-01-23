/**
 * Server-side data loading for unified browse page
 * This loads data from ALL libraries using the browseAllLibraries API
 */

import { API_ENDPOINTS, fetchSidebarData } from '$lib/server/config.js';

export async function load({ url: pageUrl, fetch }) {
    const sort = pageUrl.searchParams.get('sort') || 'name';
    const seed = pageUrl.searchParams.get('seed');

    // Construct API URL for browsing all libraries
    let apiUrl = API_ENDPOINTS.browseAllLibraries(sort, 0, 50);
    if (seed) {
        apiUrl += `&seed=${seed}`;
    }

    try {
        const [browseRes, sidebarData, continueReadingRes] = await Promise.all([
            fetch(apiUrl),
            fetchSidebarData(fetch),
            fetch(API_ENDPOINTS.continueReading(50))
        ]);

        if (!browseRes.ok) {
            console.error(`Failed to browse all libraries: ${browseRes.status} ${browseRes.statusText}`);
            return {
                browseData: null,
                error: `Failed to load content: ${browseRes.statusText}`
            };
        }

        const browseData = await browseRes.json();
        const continueReading = continueReadingRes.ok ? await continueReadingRes.json() : [];

        return {
            browseData,
            libraries: sidebarData.libraries,
            seriesTree: sidebarData.seriesTree,
            continueReading
        };

    } catch (error) {
        console.error('Server-side browse error:', error);
        return {
            browseData: null,
            error: error.message
        };
    }
}
