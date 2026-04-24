/**
 * Redirect /browse to /library/all/browse for backward compatibility
 */

import { redirect } from '@sveltejs/kit';



/** @type {import('./$types').PageServerLoad} */
export const load = async () => {
    throw redirect(301, '/library/all/browse');
};
