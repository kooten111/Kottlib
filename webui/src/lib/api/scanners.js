import { api } from './client';

/**
 * Scan a single comic for metadata
 */
export async function scanComic(comicId, overwrite = false, confidenceThreshold = null) {
	const response = await fetch('/v2/scanners/scan/comic', {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			comic_id: comicId,
			overwrite: overwrite,
			confidence_threshold: confidenceThreshold
		})
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to scan comic: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}

/**
 * Scan all comics in a library
 */
export async function scanLibrary(libraryId, overwrite = false, rescanExisting = false, confidenceThreshold = null) {
	const response = await fetch('/v2/scanners/scan/library', {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			library_id: libraryId,
			overwrite: overwrite,
			rescan_existing: rescanExisting,
			confidence_threshold: confidenceThreshold
		})
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to scan library: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}

/**
 * Clear metadata from comics
 */
export async function clearMetadata(options) {
	const response = await fetch('/v2/scanners/clear-metadata', {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			comic_ids: options.comicIds || null,
			library_id: options.libraryId || null,
			clear_scanner_info: options.clearScannerInfo !== false,
			clear_tags: options.clearTags !== false,
			clear_metadata: options.clearMetadata || false
		})
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to clear metadata: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}

/**
 * Get available scanners
 */
export async function getAvailableScanners() {
	return api.get('/v2/scanners/available');
}

/**
 * Get library scanner configurations
 */
export async function getLibraryConfigs() {
	return api.get('/v2/scanners/libraries');
}

/**
 * Configure scanner for a library
 */
export async function configureLibraryScanner(libraryId, config) {
	const response = await fetch(`/v2/scanners/libraries/${libraryId}/configure`, {
		method: 'PUT',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(config)
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to configure scanner: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}
