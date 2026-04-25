/**
 * Root layout server load — fetches sidebar data once per session.
 * Libraries list and global series tree (shallow) are static during a session,
 * so caching them here avoids re-fetching on every browse page navigation.
 */

import { fetchSidebarData } from '$lib/server/config.js';

/** @type {import('./$types').LayoutServerLoad} */
export const load = async ({ fetch }) => {
    const sidebarData = await fetchSidebarData(fetch);
    return {
        libraries: sidebarData.libraries,
        seriesTree: sidebarData.seriesTree,
    };
};
