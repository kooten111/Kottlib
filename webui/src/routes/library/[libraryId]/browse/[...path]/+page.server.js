/**
 * Server-side data loading for library items browsing
 */

import { redirect } from '@sveltejs/kit';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

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
    const browsePath = path ? encodeURIComponent(path) : '';
    let apiUrl = `${API_BASE_URL}/library/${libraryId}/browse?path=${browsePath}&sort=${sort}`;

    if (seed) {
        apiUrl += `&seed=${seed}`;
    }

    // URLs for sidebar data
    const librariesUrl = `${API_BASE_URL}/libraries`;
    const treeUrl = `${API_BASE_URL}/libraries/series-tree`;
    const libTreeUrl = `${API_BASE_URL}/library/${libraryId}/tree`;

    try {
        const [browseRes, librariesRes, treeRes, libTreeRes] = await Promise.all([
            fetch(apiUrl),
            fetch(librariesUrl),
            fetch(treeUrl),
            fetch(libTreeUrl)
        ]);

        if (!browseRes.ok) {
            console.error(`Failed to browse library: ${browseRes.status} ${browseRes.statusText}`);
            return {
                data: null,
                error: `Failed to load folder: ${browseRes.statusText}`
            };
        }

        const browseData = await browseRes.json();
        const libraries = librariesRes.ok ? await librariesRes.json() : [];
        let seriesTree = treeRes.ok ? await treeRes.json() : [];

        // Merge library specific tree to populate folders in sidebar
        if (libTreeRes.ok) {
            const libTree = await libTreeRes.json();
            seriesTree = seriesTree.map(node => {
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
