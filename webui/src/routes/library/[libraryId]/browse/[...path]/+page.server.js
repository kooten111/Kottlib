/**
 * Server-side data loading for library items browsing
 */

import { redirect } from '@sveltejs/kit';
import { API_ENDPOINTS, fetchSidebarData } from '$lib/server/config.js';

export async function load({ params, url: pageUrl, fetch }) {
    const { libraryId, path } = params;

    const sort = pageUrl.searchParams.get('sort') || 'name';
    const seed = pageUrl.searchParams.get('seed');

    // If sort is random but no seed provided, redirect with a new seed
    // This prevents the "flash" of old order when navigating back to a shuffled view
    if (sort === 'random' && !seed) {
        const newUrl = new URL(pageUrl);
        newUrl.searchParams.set('seed', String(Date.now()));
        throw redirect(307, newUrl.pathname + newUrl.search);
    }

    // Construct API URL
    let apiUrl = API_ENDPOINTS.libraryBrowse(libraryId, path || '', sort);
    if (seed) {
        apiUrl += `&seed=${seed}`;
    }

    try {
        const [browseRes, sidebarData] = await Promise.all([
            fetch(apiUrl),
            fetchSidebarData(fetch, libraryId)
        ]);

        if (!browseRes.ok) {
            console.error(`Failed to browse library: ${browseRes.status} ${browseRes.statusText}`);
            return {
                data: null,
                error: `Failed to load folder: ${browseRes.statusText}`
            };
        }

        const browseData = await browseRes.json();

        return {
            browseData,
            libraries: sidebarData.libraries,
            seriesTree: sidebarData.seriesTree,
            libraryId: parseInt(libraryId),
            currentPath: path || ''
        };

    } catch (error) {
        console.error('Server-side browse error:', error);
        return {
            data: null,
            error: error.message
        };
    }
}
