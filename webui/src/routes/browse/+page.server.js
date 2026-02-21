/**
 * Redirect /browse to /library/all/browse for backward compatibility
 */

import { redirect } from '@sveltejs/kit';

export async function load() {
    throw redirect(301, '/library/all/browse');
}
