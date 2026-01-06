/**
 * Server-side data loading for unified browse page
 * This loads data from ALL libraries using the browseAllLibraries API
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

export async function load({ url: pageUrl, fetch }) {
    const sort = pageUrl.searchParams.get('sort') || 'name';
    const seed = pageUrl.searchParams.get('seed');

    // Construct API URL for browsing all libraries
    let apiUrl = `${API_BASE_URL}/libraries/browse-content?sort=${sort}&offset=0&limit=50`;
    
    if (seed) {
        apiUrl += `&seed=${seed}`;
    }

    // URLs for sidebar data
    const librariesUrl = `${API_BASE_URL}/libraries`;
    const treeUrl = `${API_BASE_URL}/libraries/series-tree`;
    const continueReadingUrl = `${API_BASE_URL}/reading?limit=50`;

    try {
        const [browseRes, librariesRes, treeRes, continueReadingRes] = await Promise.all([
            fetch(apiUrl),
            fetch(librariesUrl),
            fetch(treeUrl),
            fetch(continueReadingUrl)
        ]);

        if (!browseRes.ok) {
            console.error(`Failed to browse all libraries: ${browseRes.status} ${browseRes.statusText}`);
            return {
                browseData: null,
                error: `Failed to load content: ${browseRes.statusText}`
            };
        }

        const browseData = await browseRes.json();
        const libraries = librariesRes.ok ? await librariesRes.json() : [];
        const seriesTree = treeRes.ok ? await treeRes.json() : [];
        const continueReading = continueReadingRes.ok ? await continueReadingRes.json() : [];

        return {
            browseData,
            libraries,
            seriesTree,
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
