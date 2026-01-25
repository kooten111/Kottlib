/**
 * Server-side data loading for series detail page
 */

import { API_ENDPOINTS } from '$lib/server/config.js';

export async function load({ params, fetch }) {
    const { libraryId, seriesName } = params;
    const url = API_ENDPOINTS.seriesDetail(libraryId, seriesName);

    try {
        const response = await fetch(url);

        if (!response.ok) {
            console.error(`Failed to fetch series detail: ${response.status} ${response.statusText}`);
            return {
                series: null,
                error: `Failed to load series: ${response.statusText}`
            };
        }

        const series = await response.json();
        return {
            series,
            libraryId: parseInt(libraryId),
            seriesName
        };

    } catch (error) {
        console.error('Server-side series load error:', error);
        return {
            series: null,
            error: error.message
        };
    }
}
