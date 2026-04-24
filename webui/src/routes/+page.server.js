/**
 * Redirect root path to /library/all/browse
 * Provides a unified browse experience for all libraries
 */

import { redirect } from '@sveltejs/kit';



/** @type {import('./$types').PageServerLoad} */
export const load = async () => {
	throw redirect(302, '/library/all/browse');
};
