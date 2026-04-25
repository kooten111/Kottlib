/**
 * Server-side data loading for library items browsing
 * Handles both single-library (libraryId = number) and all-libraries (libraryId = 'all') modes
 *
 * Sidebar data (libraries + shallow seriesTree) is sourced from the root layout server load
 * via parent() — it is cached for the session and not re-fetched on every navigation.
 * Only browse content and the per-library folder tree are fetched per navigation.
 */

import { redirect } from '@sveltejs/kit';
import { API_ENDPOINTS } from '$lib/server/config.js';


/** @type {import('./$types').PageServerLoad} */
export const load = async ({ params, url: pageUrl, fetch, parent }) => {
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

            // Fetch browse data and continue-reading in parallel; sidebar data comes from cached layout.
            const [{ libraries, seriesTree }, browseRes, continueReadingRes] = await Promise.all([
                parent(),
                fetch(apiUrl),
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
            if (libraries && continueReading.length > 0) {
                const hiddenLibraryIds = new Set(
                    libraries
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
                libraries,
                seriesTree,
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

            // Fetch browse data and per-library folder tree in parallel; base sidebar data from layout cache.
            const [{ libraries, seriesTree: baseSeriesTree }, browseRes, libraryTreeRes] = await Promise.all([
                parent(),
                fetch(apiUrl),
                fetch(API_ENDPOINTS.libraryTree(libraryId))
            ]);

            if (!browseRes.ok) {
                console.error(`Failed to browse library: ${browseRes.status} ${browseRes.statusText}`);
                return {
                    browseData: null,
                    error: `Failed to load folder: ${browseRes.statusText}`
                };
            }

            const browseData = await browseRes.json();

            // Merge per-library folder tree into the cached shallow series tree
            let seriesTree = baseSeriesTree;
            if (libraryTreeRes.ok) {
                const libTree = await libraryTreeRes.json();
                seriesTree = baseSeriesTree.map(node => {
                    if (node.id === parseInt(libraryId)) {
                        return { ...node, children: libTree.children || [] };
                    }
                    return node;
                });
            }

            return {
                browseData,
                libraries,
                seriesTree,
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
