/**
 * Base API client for Kottlib with persistent caching
 */

import { getCached, setCached, clearCachePattern } from '$lib/utils/persistentCache';

class APIError extends Error {
	constructor(message, status, response) {
		super(message);
		this.name = 'APIError';
		this.status = status;
		this.response = response;
	}
}

class APIClient {
	constructor(baseURL = '') {
		this.baseURL = baseURL;
		this.cacheEnabled = true;
	}

	/**
	 * Check if endpoint should be cached
	 */
	isCacheable(endpoint) {
		// Cache GET requests for mostly-static data
		const cacheableEndpoints = [
			'/libraries',
			'/libraries/series-tree',
			'/library/',
			'/series/'
		];

		return cacheableEndpoints.some(pattern => endpoint.includes(pattern));
	}

	async request(endpoint, options = {}) {
		const url = `${this.baseURL}${endpoint}`;
		const cacheKey = `${this.baseURL}${endpoint}`;
		const isGET = !options.method || options.method === 'GET';
		const shouldCache = this.cacheEnabled && isGET && this.isCacheable(endpoint);

		// Use custom fetch if provided, otherwise use global fetch
		const fetchFn = options.fetch || fetch;

		// Try to get from cache first (stale-while-revalidate)
		if (shouldCache) {
			const cached = await getCached(cacheKey);
			if (cached) {


				// Return cached data immediately
				// Then fetch fresh data in background and update cache
				this._fetchAndCache(url, cacheKey, { ...options, fetch: fetchFn }).catch(err => {
					console.error('[API] Background refresh failed:', err);
				});

				return cached;
			}
		}

		// Not in cache or not cacheable - fetch from network
		const config = {
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			...options
		};

		// Remove the fetch option from config as it's not a standard fetch option
		delete config.fetch;

		try {
			const response = await fetchFn(url, config);

			if (!response.ok) {
				const errorText = await response.text();
				throw new APIError(
					`API request failed: ${response.statusText}`,
					response.status,
					errorText
				);
			}

			if (options.responseType === 'blob') {
				return await response.blob();
			}

			const contentType = response.headers.get('content-type');
			if (contentType && contentType.includes('application/json')) {
				const data = await response.json();

				// Cache the response
				if (shouldCache) {
					await setCached(cacheKey, data);
				}

				return data;
			}

			return await response.text();
		} catch (error) {
			if (error instanceof APIError) {
				throw error;
			}
			throw new APIError(`Network error: ${error.message}`, 0, null);
		}
	}

	/**
	 * Fetch and cache in background (for stale-while-revalidate)
	 */
	async _fetchAndCache(url, cacheKey, options) {
		// Use custom fetch if provided, otherwise use global fetch
		const fetchFn = options.fetch || fetch;

		const config = {
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			...options
		};

		// Remove the fetch option from config as it's not a standard fetch option
		delete config.fetch;

		try {
			const response = await fetchFn(url, config);

			if (response.ok) {
				const contentType = response.headers.get('content-type');
				if (contentType && contentType.includes('application/json')) {
					const data = await response.json();
					await setCached(cacheKey, data);

				}
			}
		} catch (error) {
			// Silent fail for background refresh
			console.error('[API] Background fetch error:', error);
		}
	}

	async get(endpoint, options = {}) {
		return this.request(endpoint, { ...options, method: 'GET' });
	}

	async post(endpoint, data, options = {}) {
		const result = await this.request(endpoint, {
			...options,
			method: 'POST',
			body: JSON.stringify(data)
		});

		// Invalidate cache for library endpoints after POST
		await this._invalidateRelatedCache(endpoint);
		return result;
	}

	async put(endpoint, data, options = {}) {
		const result = await this.request(endpoint, {
			...options,
			method: 'PUT',
			body: JSON.stringify(data)
		});

		// Invalidate cache for library endpoints after PUT
		await this._invalidateRelatedCache(endpoint);
		return result;
	}

	async patch(endpoint, data, options = {}) {
		const result = await this.request(endpoint, {
			...options,
			method: 'PATCH',
			body: JSON.stringify(data)
		});

		// Invalidate cache for library endpoints after PATCH
		await this._invalidateRelatedCache(endpoint);
		return result;
	}

	async delete(endpoint, options = {}) {
		const result = await this.request(endpoint, { ...options, method: 'DELETE' });

		// Invalidate cache for library endpoints after DELETE
		await this._invalidateRelatedCache(endpoint);
		return result;
	}

	/**
	 * Invalidate cache for related endpoints after mutations
	 */
	async _invalidateRelatedCache(endpoint) {

		// If library was modified, clear library-related caches
		if (endpoint.includes('/libraries')) {
			await clearCachePattern('v2/libraries');
		}

		// If series was modified, clear series-related caches
		if (endpoint.includes('/series')) {
			await clearCachePattern('v2/series');
			await clearCachePattern('v2/libraries/series-tree');
		}

		// If reading list was modified, clear reading list caches
		if (endpoint.includes('/reading_list')) {
			await clearCachePattern('reading_list');
		}
	}

	async getBlob(endpoint, options = {}) {
		return this.request(endpoint, {
			...options,
			responseType: 'blob'
		});
	}
}

// Export singleton instance
export const api = new APIClient('/v2');

export { APIError };
