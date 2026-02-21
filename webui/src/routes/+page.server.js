/**
 * Redirect root path to /library/all/browse
 * Provides a unified browse experience for all libraries
 */

import { redirect } from '@sveltejs/kit';

export async function load() {
	throw redirect(302, '/library/all/browse');
}
