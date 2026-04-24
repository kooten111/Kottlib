/**
 * Server-side data loading for library items browsing
 * Handles both single-library (libraryId = number) and all-libraries (libraryId = 'all') modes
 */

import { redirect } from '@sveltejs/kit';
import { API_ENDPOINTS, fetchSidebarData } from '$lib/server/config.js';


/** @type {import('./$types').PageServerLoad} */
export const load = async ({ params, url: pageUrl, fetch }) => {
    const { libraryId, path } = params;
    const isAllLibraries = libraryId === 'all';

    const sort = pageUrl.searchParams.get('sort') || 'name';
    const seed = pageUrl.searchParams.get('seed');
    const searchQuery = pageUrl.searchParams.get('q') || '';

    // If sort is random but no seed provided, redirect with a new seed
    if (sort === 'random' && !seed) {
        const newUrl = new URL(pageUrl);
        newUrl.searchParams.set('seed', String(Date.now()));
        throw redirect(307, newUrl.pathname + newUrl.search);
    }

    try {
        if (isAllLibraries) {
            // All-libraries mode: merged content from all libraries
            let apiUrl = API_ENDPOINTS.browseAllLibraries(sort, 0, 50);
            if (seed) {
                apiUrl += `&seed=${seed}`;
            }

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
            let continueReading = continueReadingRes.ok ? await continueReadingRes.json() : [];

            // Filter out continue reading items from hidden libraries
            if (sidebarData.libraries && continueReading.length > 0) {
                const hiddenLibraryIds = new Set(
                    sidebarData.libraries
                        .filter(lib => lib.exclude_from_webui)
                        .map(lib => String(lib.id))
                );
                if (hiddenLibraryIds.size > 0) {
                    continueReading = continueReading.filter(item =>
                        !hiddenLibraryIds.has(String(item.library_id))
                    );
                }
            }

            return {
                browseData,
                libraries: sidebarData.libraries,
                seriesTree: sidebarData.seriesTree,
                libraryId: 'all',
                currentPath: path || '',
                continueReading,
                searchQuery
            };
        } else {
            // Single-library mode
            let apiUrl = API_ENDPOINTS.libraryBrowse(libraryId, path || '', sort);
            if (seed) {
                apiUrl += `&seed=${seed}`;
            }

            const [browseRes, sidebarData] = await Promise.all([
                fetch(apiUrl),
                fetchSidebarData(fetch, libraryId)
            ]);

            if (!browseRes.ok) {
                console.error(`Failed to browse library: ${browseRes.status} ${browseRes.statusText}`);
                return {
                    browseData: null,
                    error: `Failed to load folder: ${browseRes.statusText}`
                };
            }

            const browseData = await browseRes.json();

            return {
                browseData,
                libraries: sidebarData.libraries,
                seriesTree: sidebarData.seriesTree,
                libraryId: parseInt(libraryId),
                currentPath: path || '',
                continueReading: null,
                searchQuery
            };
        }
    } catch (error) {
        console.error('Server-side browse error:', error);
        return {
            browseData: null,
            error: error.message
        };
    }
};
