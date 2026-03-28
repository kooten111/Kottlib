import { appApi } from './client';

/**
 * Search comics in a library (basic search)
 */
export async function searchComics(libraryId, query, options = {}) {
	const params = new URLSearchParams({
		q: query,
		...options
	});

	return appApi.get(`/libraries/${libraryId}/search?${params}`);
}

/**
 * Advanced search with pagination
 */
export async function searchComicsAdvanced(libraryId, query, { limit = 100, offset = 0 } = {}) {
	const params = new URLSearchParams({
		q: query,
		limit: limit.toString(),
		offset: offset.toString()
	});

	return appApi.get(`/libraries/${libraryId}/search/advanced?${params}`);
}

/**
 * Get searchable fields for a library
 */
export async function getSearchableFields(libraryId) {
	return appApi.get(`/libraries/${libraryId}/search/fields`);
}

/**
 * Get existing values for a searchable metadata field.
 */
export async function getSearchValues({ field, libraryId = null, query = '', limit = 25 } = {}) {
	const params = new URLSearchParams({
		q: query,
		limit: limit.toString()
	});

	if (libraryId != null) {
		return appApi.get(`/libraries/${libraryId}/search/values/${field}?${params}`);
	}

	return appApi.get(`/search/values/${field}?${params}`);
}

/**
 * Backward-compatible tag helper.
 */
export async function getSearchTags({ libraryId = null, query = '', limit = 25 } = {}) {
	const response = await getSearchValues({ field: 'tags', libraryId, query, limit });
	return {
		...response,
		tags: response.values || []
	};
}

/**
 * Parse a search query (for debugging/preview)
 */
export async function parseSearchQuery(query) {
	const params = new URLSearchParams({ q: query });
	return appApi.get(`/search/query/parse?${params}`);
}

/**
 * Get discoverable facet fields for a library, based on existing metadata.
 */
export async function getSearchFacets({ libraryId, valuesLimit = 10 } = {}) {
	if (libraryId == null) {
		throw new Error('libraryId is required for facet discovery');
	}

	const params = new URLSearchParams({
		values_limit: valuesLimit.toString()
	});

	return appApi.get(`/libraries/${libraryId}/search/facets?${params}`);
}

/**
 * Get suggestions for multiple fields in one call.
 */
export async function getSearchFacetValues({ libraryId, fields = [], query = '', limit = 25 } = {}) {
	if (libraryId == null) {
		throw new Error('libraryId is required for facet values');
	}

	const normalizedFields = Array.isArray(fields)
		? fields.map((field) => `${field}`.trim()).filter(Boolean)
		: `${fields}`.split(',').map((field) => field.trim()).filter(Boolean);

	if (normalizedFields.length === 0) {
		throw new Error('At least one field is required');
	}

	const params = new URLSearchParams({
		fields: normalizedFields.join(','),
		q: query,
		limit: limit.toString()
	});

	return appApi.get(`/libraries/${libraryId}/search/facets/values?${params}`);
}
