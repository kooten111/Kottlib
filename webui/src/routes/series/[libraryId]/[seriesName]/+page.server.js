/**
 * Server-side data loading for series detail page
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8081/v2';

export async function load({ params, fetch }) {
    const { libraryId, seriesName } = params;
    const encodedName = encodeURIComponent(seriesName);
    const url = `${API_BASE_URL}/library/${libraryId}/series/${encodedName}`;

    const fs = await import('fs');
    fs.appendFileSync('/tmp/ssr_debug.log', `[SSR] Requesting: ${url}\n`);
    fs.appendFileSync('/tmp/ssr_debug.log', `[SSR] Params: ${JSON.stringify(params)}\n`);

    try {
        const response = await fetch(url);

        if (!response.ok) {
            fs.appendFileSync('/tmp/ssr_debug.log', `[SSR] Error: ${response.status} ${response.statusText}\n`);
            console.error(`Failed to fetch series detail: ${response.status} ${response.statusText}`);
            return {
                series: null,
                error: `Failed to load series: ${response.statusText}`
            };
        }

        const series = await response.json();
        fs.appendFileSync('/tmp/ssr_debug.log', `[SSR] Success: ${JSON.stringify(series).substring(0, 100)}...\n`);
        return {
            series,
            libraryId: parseInt(libraryId),
            seriesName
        };

    } catch (error) {
        fs.appendFileSync('/tmp/ssr_debug.log', `[SSR] Exception: ${error.message}\n`);
        console.error('Server-side series load error:', error);
        return {
            series: null,
            error: error.message
        };
    }
}
