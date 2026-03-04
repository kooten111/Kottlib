import { api } from './client';

/**
 * Scan a series for metadata
 * Returns { success, error?, candidates?, auto_match_threshold?, ... } 
 */
export async function scanSeries(libraryId, seriesName, overwrite = false, confidenceThreshold = null) {
	const params = new URLSearchParams({
		library_id: libraryId.toString(),
		series_name: seriesName,
		overwrite: overwrite.toString()
	});
	
	if (confidenceThreshold !== null) {
		params.append('confidence_threshold', confidenceThreshold.toString());
	}
	
	const response = await fetch(`/api/scanners/scan/series?${params.toString()}`, {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		}
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to scan series: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}

/**
 * Apply metadata from a manually selected candidate to a series
 */
export async function applySeriesMetadata(libraryId, seriesName, candidate, overwrite = false) {
	const response = await fetch('/api/scanners/apply/series', {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			library_id: libraryId,
			series_name: seriesName,
			source_id: candidate.source_id,
			source_url: candidate.source_url || null,
			confidence: candidate.confidence,
			metadata: candidate.metadata,
			overwrite: overwrite
		})
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to apply metadata: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}

/**
 * Scan a single comic for metadata
 */
export async function scanComic(comicId, overwrite = false, confidenceThreshold = null) {
	const response = await fetch('/api/scanners/scan/comic', {
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
 * Apply metadata from a manually selected candidate to a comic
 */
export async function applyComicMetadata(comicId, candidate, overwrite = false) {
	const response = await fetch('/api/scanners/apply/comic', {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			comic_id: comicId,
			source_id: candidate.source_id,
			source_url: candidate.source_url || null,
			confidence: candidate.confidence,
			metadata: candidate.metadata,
			overwrite: overwrite
		})
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Failed to apply metadata: ${response.statusText} - ${errorText}`);
	}

	return response.json();
}

/**
 * Scan all comics in a library
 */
export async function scanLibrary(libraryId, overwrite = false, rescanExisting = false, confidenceThreshold = null) {
	const response = await fetch('/api/scanners/scan/library', {
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
	const response = await fetch('/api/scanners/clear-metadata', {
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
	return api.get('/scanners/available');
}

/**
 * Get library scanner configurations
 */
export async function getLibraryConfigs() {
	return api.get('/scanners/libraries');
}

/**
 * Configure scanner for a library
 */
export async function configureLibraryScanner(libraryId, config) {
	const response = await fetch(`/api/scanners/libraries/${libraryId}/configure`, {
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

/**
 * Get scanner capabilities for a specific scanner
 */
export async function getScannerCapabilities(scannerName) {
	const scanners = await getAvailableScanners();
	return scanners.find((s) => s.name === scannerName);
}

/**
 * Get the primary scanner capabilities for a library
 */
export async function getLibraryScannerCapabilities(libraryId) {
	const configs = await getLibraryConfigs();
	const libraryConfig = configs.find((c) => c.library_id === parseInt(libraryId));

	if (libraryConfig?.primary_scanner) {
		return getScannerCapabilities(libraryConfig.primary_scanner);
	}

	return null;
}
