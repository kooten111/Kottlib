/**
 * Redirect root path to /browse
 * Provides a unified browse experience for all libraries
 */

import { redirect } from '@sveltejs/kit';

export async function load() {
	throw redirect(302, '/browse');
}
