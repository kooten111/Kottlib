/**
 * Base API client for YACLib Enhanced
 */

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
	}

	async request(endpoint, options = {}) {
		const url = `${this.baseURL}${endpoint}`;
		const config = {
			credentials: 'include', // Include cookies for session management
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			...options
		};

		try {
			const response = await fetch(url, config);

			// Handle non-OK responses
			if (!response.ok) {
				const errorText = await response.text();
				throw new APIError(
					`API request failed: ${response.statusText}`,
					response.status,
					errorText
				);
			}

			// Return blob for binary data
			if (options.responseType === 'blob') {
				return await response.blob();
			}

			// Parse JSON response
			const contentType = response.headers.get('content-type');
			if (contentType && contentType.includes('application/json')) {
				return await response.json();
			}

			// Return text for other content types
			return await response.text();
		} catch (error) {
			if (error instanceof APIError) {
				throw error;
			}
			throw new APIError(`Network error: ${error.message}`, 0, null);
		}
	}

	async get(endpoint, options = {}) {
		return this.request(endpoint, { ...options, method: 'GET' });
	}

	async post(endpoint, data, options = {}) {
		return this.request(endpoint, {
			...options,
			method: 'POST',
			body: JSON.stringify(data)
		});
	}

	async put(endpoint, data, options = {}) {
		return this.request(endpoint, {
			...options,
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	async delete(endpoint, options = {}) {
		return this.request(endpoint, { ...options, method: 'DELETE' });
	}

	async getBlob(endpoint) {
		return this.request(endpoint, { responseType: 'blob' });
	}
}

// Export singleton instance
export const api = new APIClient('/v2');

export { APIError };
