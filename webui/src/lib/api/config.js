/**
 * Config API Client
 * Functions for interacting with server configuration endpoints
 */

const API_BASE = '/api/v2';

/**
 * Get current server configuration
 * @returns {Promise<Object>} Configuration object
 */
export async function getConfig() {
    const response = await fetch(`${API_BASE}/config`);
    if (!response.ok) {
        throw new Error(`Failed to get config: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Update server configuration
 * @param {Object} config - Configuration update object
 * @param {Object} [config.server] - Server configuration
 * @param {Object} [config.database] - Database configuration
 * @param {Object} [config.storage] - Storage configuration
 * @param {Object} [config.features] - Feature flags
 * @returns {Promise<Object>} Update result
 */
export async function updateConfig(config) {
    const response = await fetch(`${API_BASE}/config`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to update config: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Get config file path
 * @returns {Promise<Object>} Config file path and existence info
 */
export async function getConfigPath() {
    const response = await fetch(`${API_BASE}/config/path`);
    if (!response.ok) {
        throw new Error(`Failed to get config path: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Reload configuration from file
 * @returns {Promise<Object>} Reload result
 */
export async function reloadConfig() {
    const response = await fetch(`${API_BASE}/config/reload`, {
        method: 'POST',
    });

    if (!response.ok) {
        throw new Error(`Failed to reload config: ${response.statusText}`);
    }

    return response.json();
}
