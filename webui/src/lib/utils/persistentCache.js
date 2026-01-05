/**
 * Persistent cache using IndexedDB for comic library data
 * Stores API responses locally to survive browser restarts
 */

const DB_NAME = 'yaclib-cache';
const DB_VERSION = 1;
const STORE_NAME = 'api-cache';
const MAX_AGE = 1000 * 60 * 60 * 24; // 24 hours

/**
 * Open IndexedDB connection
 */
function openDB() {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => resolve(request.result);

		request.onupgradeneeded = (event) => {
			const db = event.target.result;

			// Create object store if it doesn't exist
			if (!db.objectStoreNames.contains(STORE_NAME)) {
				const store = db.createObjectStore(STORE_NAME, { keyPath: 'key' });
				store.createIndex('timestamp', 'timestamp', { unique: false });
			}
		};
	});
}

/**
 * Get cached data by key
 * @param {string} key - Cache key (e.g., '/v2/libraries')
 * @returns {Promise<any>} Cached data or null
 */
export async function getCached(key) {
	try {
		const db = await openDB();
		const transaction = db.transaction(STORE_NAME, 'readonly');
		const store = transaction.objectStore(STORE_NAME);

		return new Promise((resolve) => {
			const request = store.get(key);

			request.onsuccess = () => {
				const result = request.result;

				if (!result) {
					resolve(null);
					return;
				}

				// Check if cache is expired
				const age = Date.now() - result.timestamp;
				if (age > MAX_AGE) {

					resolve(null);
					return;
				}


				resolve(result.data);
			};

			request.onerror = () => {
				console.error('[Cache] Get error:', request.error);
				resolve(null);
			};
		});
	} catch (error) {
		console.error('[Cache] Error:', error);
		return null;
	}
}

/**
 * Set cached data
 * @param {string} key - Cache key
 * @param {any} data - Data to cache
 */
export async function setCached(key, data) {
	try {
		const db = await openDB();
		const transaction = db.transaction(STORE_NAME, 'readwrite');
		const store = transaction.objectStore(STORE_NAME);

		const cacheEntry = {
			key,
			data,
			timestamp: Date.now()
		};

		return new Promise((resolve, reject) => {
			const request = store.put(cacheEntry);

			request.onsuccess = () => {

				resolve();
			};

			request.onerror = () => {
				console.error('[Cache] Set error:', request.error);
				reject(request.error);
			};
		});
	} catch (error) {
		console.error('[Cache] Error:', error);
	}
}

/**
 * Clear all cached data
 */
export async function clearCache() {
	try {
		const db = await openDB();
		const transaction = db.transaction(STORE_NAME, 'readwrite');
		const store = transaction.objectStore(STORE_NAME);

		return new Promise((resolve, reject) => {
			const request = store.clear();

			request.onsuccess = () => {

				resolve();
			};

			request.onerror = () => {
				console.error('[Cache] Clear error:', request.error);
				reject(request.error);
			};
		});
	} catch (error) {
		console.error('[Cache] Error:', error);
	}
}

/**
 * Clear cached data matching a pattern
 * @param {string} pattern - Pattern to match cache keys (e.g., 'v2/libraries')
 */
export async function clearCachePattern(pattern) {
	try {
		const db = await openDB();
		const transaction = db.transaction(STORE_NAME, 'readwrite');
		const store = transaction.objectStore(STORE_NAME);

		return new Promise((resolve) => {
			const request = store.openCursor();
			let deletedCount = 0;

			request.onsuccess = (event) => {
				const cursor = event.target.result;

				if (cursor) {
					if (cursor.value.key.includes(pattern)) {
						cursor.delete();
						deletedCount++;
					}
					cursor.continue();
				} else {

					resolve();
				}
			};

			request.onerror = () => {
				console.error('[Cache] Clear pattern error:', request.error);
				resolve();
			};
		});
	} catch (error) {
		console.error('[Cache] Error:', error);
	}
}

/**
 * Clear expired cache entries
 */
export async function clearExpired() {
	try {
		const db = await openDB();
		const transaction = db.transaction(STORE_NAME, 'readwrite');
		const store = transaction.objectStore(STORE_NAME);

		return new Promise((resolve) => {
			const request = store.openCursor();
			let deletedCount = 0;

			request.onsuccess = (event) => {
				const cursor = event.target.result;

				if (cursor) {
					const age = Date.now() - cursor.value.timestamp;
					if (age > MAX_AGE) {
						cursor.delete();
						deletedCount++;
					}
					cursor.continue();
				} else {

					resolve();
				}
			};

			request.onerror = () => {
				console.error('[Cache] Clear expired error:', request.error);
				resolve();
			};
		});
	} catch (error) {
		console.error('[Cache] Error:', error);
	}
}

/**
 * Get cache statistics
 */
export async function getCacheStats() {
	try {
		const db = await openDB();
		const transaction = db.transaction(STORE_NAME, 'readonly');
		const store = transaction.objectStore(STORE_NAME);

		return new Promise((resolve) => {
			const request = store.getAll();

			request.onsuccess = () => {
				const entries = request.result;
				const now = Date.now();

				const stats = {
					total: entries.length,
					valid: 0,
					expired: 0,
					totalSize: 0,
					entries: []
				};

				entries.forEach((entry) => {
					const age = now - entry.timestamp;
					const sizeKB = Math.round(JSON.stringify(entry.data).length / 1024);

					if (age > MAX_AGE) {
						stats.expired++;
					} else {
						stats.valid++;
					}

					stats.totalSize += sizeKB;
					stats.entries.push({
						key: entry.key,
						age: Math.round(age / 1000 / 60), // minutes
						sizeKB
					});
				});

				resolve(stats);
			};

			request.onerror = () => {
				console.error('[Cache] Stats error:', request.error);
				resolve({ total: 0, valid: 0, expired: 0, totalSize: 0, entries: [] });
			};
		});
	} catch (error) {
		console.error('[Cache] Error:', error);
		return { total: 0, valid: 0, expired: 0, totalSize: 0, entries: [] };
	}
}
