/**
 * Server-side data loading for library items browsing
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

export async function load({ params, fetch }) {
    const { libraryId, path } = params;

    // Construct API URL
    // If path is present, we browse that path. If not (empty rest param?), we browse root.
    // SvelteKit rest param might be undefined or empty string if optional.
    // Since we put this in browse/[...path], it expects at least one segment usually, 
    // unless we made it [[...path]]. But we want to browse subfolders here.
    // Root browsing should probably be handled by the main library page or a redirect.
    // However, let's simple encode the path.

    // URL for browsing
    const browsePath = path ? encodeURIComponent(path) : '';
    const url = `${API_BASE_URL}/library/${libraryId}/browse?path=${browsePath}`;

    // URLs for sidebar data
    const librariesUrl = `${API_BASE_URL}/libraries`;
    const treeUrl = `${API_BASE_URL}/libraries/series-tree`;
    const libTreeUrl = `${API_BASE_URL}/library/${libraryId}/tree`;

    try {
        const [browseRes, librariesRes, treeRes, libTreeRes] = await Promise.all([
            fetch(url),
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
