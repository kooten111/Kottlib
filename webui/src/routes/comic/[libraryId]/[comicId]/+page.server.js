/**
 * Server-side data loading for comic detail page
 * Fetches comic info and sidebar data (libraries, series tree)
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

export async function load({ params, fetch }) {
    const { libraryId, comicId } = params;

    // URLs for data fetching
    const comicUrl = `${API_BASE_URL}/library/${libraryId}/comic/${comicId}/fullinfo`;
    const librariesUrl = `${API_BASE_URL}/libraries`;
    const treeUrl = `${API_BASE_URL}/libraries/series-tree`;
    const libTreeUrl = `${API_BASE_URL}/library/${libraryId}/tree`;

    try {
        const [comicRes, librariesRes, treeRes, libTreeRes] = await Promise.all([
            fetch(comicUrl),
            fetch(librariesUrl),
            fetch(treeUrl),
            fetch(libTreeUrl)
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
            comic,
            libraries,
            seriesTree,
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
