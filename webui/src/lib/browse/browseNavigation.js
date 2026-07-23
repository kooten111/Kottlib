/** URL helpers shared by browse and search result navigation. */

export function encodePath(path) {
	if (!path) return '';
	return path
		.split('/')
		.map((segment) => encodeURIComponent(segment))
		.join('/');
}

export function getResultLibraryId(result, fallbackLibraryId) {
	return result?.library_id || result?.libraryId || fallbackLibraryId;
}

export function getFolderBrowseUrl(item, fallbackLibraryId) {
	if (!item) {
		return null;
	}

	const itemLibraryId = getResultLibraryId(item, fallbackLibraryId);
	const itemPath =
		typeof item.path === 'string' ? item.path.replace(/^\/+|\/+$/g, '') : '';

	if (itemLibraryId && itemPath) {
		return `/library/${itemLibraryId}/browse/${encodePath(itemPath)}`;
	}

	if (item.browse_path) {
		return item.browse_path;
	}

	if (itemLibraryId && item.id) {
		return `/library/${itemLibraryId}/browse/${item.id}`;
	}

	return null;
}

export function normalizeSearchFolderResult(result, fallbackLibraryId) {
	return {
		...result,
		type: result.type || 'series',
		library_id: getResultLibraryId(result, fallbackLibraryId),
		cover_hash: result.cover_hash || result.coverHash,
		total_issues: result.total_issues || result.comic_count || 0,
	};
}
