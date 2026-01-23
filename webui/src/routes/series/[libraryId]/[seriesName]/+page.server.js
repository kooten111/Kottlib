/**
 * Server-side data loading for series detail page
 */

import { API_ENDPOINTS } from '$lib/server/config.js';

export async function load({ params, fetch }) {
    const { libraryId, seriesName } = params;
    const url = API_ENDPOINTS.seriesDetail(libraryId, seriesName);

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
