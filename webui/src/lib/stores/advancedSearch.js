/**
 * Advanced Search Store
 *
 * Manages state for advanced search features:
 * - Search history
 * - Saved searches
 * - Current search filters
 */

import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

// Search history (stored in localStorage)
function createSearchHistory() {
    const HISTORY_KEY = 'kottlib_search_history';
    const MAX_HISTORY = 20;

    // Load from localStorage (only in browser)
    let initial = [];
    if (browser) {
        try {
            const stored = localStorage.getItem(HISTORY_KEY);
            if (stored) {
                initial = JSON.parse(stored);
            }
        } catch (e) {
            console.error('Failed to load search history:', e);
        }
    }

    const { subscribe, set, update } = writable(initial);

    return {
        subscribe,
        add: (query) => {
            update(history => {
                // Remove if already exists
                const filtered = history.filter(h => h.query !== query);
                // Add to front
                const newHistory = [
                    { query, timestamp: Date.now() },
                    ...filtered
                ].slice(0, MAX_HISTORY);

                // Save to localStorage (only in browser)
                if (browser) {
                    try {
                        localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
                    } catch (e) {
                        console.error('Failed to save search history:', e);
                    }
                }

                return newHistory;
            });
        },
        clear: () => {
            set([]);
            if (browser) {
                try {
                    localStorage.removeItem(HISTORY_KEY);
                } catch (e) {
                    console.error('Failed to clear search history:', e);
                }
            }
        },
        remove: (query) => {
            update(history => {
                const newHistory = history.filter(h => h.query !== query);
                if (browser) {
                    try {
                        localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
                    } catch (e) {
                        console.error('Failed to save search history:', e);
                    }
                }
                return newHistory;
            });
        }
    };
}

// Saved searches (stored in localStorage)
function createSavedSearches() {
    const SAVED_KEY = 'kottlib_saved_searches';

    // Load from localStorage (only in browser)
    let initial = [];
    if (browser) {
        try {
            const stored = localStorage.getItem(SAVED_KEY);
            if (stored) {
                initial = JSON.parse(stored);
            }
        } catch (e) {
            console.error('Failed to load saved searches:', e);
        }
    }

    const { subscribe, set, update } = writable(initial);

    return {
        subscribe,
        save: (name, query, filters = {}) => {
            update(searches => {
                const newSearch = {
                    id: Date.now().toString(),
                    name,
                    query,
                    filters,
                    createdAt: Date.now()
                };

                const newSearches = [...searches, newSearch];

                // Save to localStorage (only in browser)
                if (browser) {
                    try {
                        localStorage.setItem(SAVED_KEY, JSON.stringify(newSearches));
                    } catch (e) {
                        console.error('Failed to save search:', e);
                    }
                }

                return newSearches;
            });
        },
        remove: (id) => {
            update(searches => {
                const newSearches = searches.filter(s => s.id !== id);
                if (browser) {
                    try {
                        localStorage.setItem(SAVED_KEY, JSON.stringify(newSearches));
                    } catch (e) {
                        console.error('Failed to remove saved search:', e);
                    }
                }
                return newSearches;
            });
        },
        clear: () => {
            set([]);
            if (browser) {
                try {
                    localStorage.removeItem(SAVED_KEY);
                } catch (e) {
                    console.error('Failed to clear saved searches:', e);
                }
            }
        }
    };
}

// Active search filters
export const activeFilters = writable({
    fields: {}, // { writer: 'Stan Lee', genre: 'superhero' }
    excludes: [] // ['tag:nsfw']
});

// Available searchable fields (cached)
export const searchableFields = writable(null);

// Search history
export const searchHistory = createSearchHistory();

// Saved searches
export const savedSearches = createSavedSearches();

// Advanced search modal state
export const showAdvancedSearch = writable(false);

// Build query string from active filters
export function buildQueryFromFilters(filters) {
    const parts = [];

    // Add field filters
    for (const [field, value] of Object.entries(filters.fields || {})) {
        if (value && value.trim()) {
            // Quote if contains spaces
            const quotedValue = value.includes(' ') ? `"${value}"` : value;
            parts.push(`${field}:${quotedValue}`);
        }
    }

    // Add exclusions
    for (const exclude of (filters.excludes || [])) {
        parts.push(`-${exclude}`);
    }

    return parts.join(' ');
}

// Parse query string into filters
export function parseQueryToFilters(query) {
    const filters = {
        fields: {},
        excludes: [],
        general: []
    };

    if (!query) return filters;

    // Pattern to match field:value or field:"quoted value"
    const fieldPattern = /(-?)(\w+):(?:"([^"]+)"|'([^']+)'|(\S+))/g;

    let match;
    const matchedPositions = new Set();

    while ((match = fieldPattern.exec(query)) !== null) {
        const [fullMatch, exclude, field, quotedValue1, quotedValue2, simpleValue] = match;
        const value = quotedValue1 || quotedValue2 || simpleValue;

        // Track matched positions
        for (let i = match.index; i < match.index + fullMatch.length; i++) {
            matchedPositions.add(i);
        }

        if (exclude === '-') {
            filters.excludes.push(`${field}:${value}`);
        } else {
            filters.fields[field] = value;
        }
    }

    // Extract general terms (not part of field-specific queries)
    let generalTerms = '';
    for (let i = 0; i < query.length; i++) {
        if (!matchedPositions.has(i)) {
            generalTerms += query[i];
        }
    }

    filters.general = generalTerms.trim().split(/\s+/).filter(t => t && t !== 'NOT');

    return filters;
}
