/**
 * Color utilities for Kottlib frontend
 */

/**
 * Generate gradient colors from a hash string
 * 
 * Used for fallback cover backgrounds when no cover image is available.
 * Generates consistent colors based on the hash value.
 * 
 * @param {string} hash - Hash string to generate colors from (can be null/undefined)
 * @param {string} fallback - Optional fallback string to use if hash is empty
 * @returns {[string, string]} - Array of two color hex strings for gradient
 */
export function getGradientColors(hash, fallback = null) {
    const value = hash || fallback || "";
    
    if (!value) return ["#3f3f46", "#18181b"];
    
    const colorPairs = [
        ["#f97316", "#dc2626"],  // Orange to Red
        ["#3b82f6", "#8b5cf6"],  // Blue to Purple
        ["#22c55e", "#14b8a6"],  // Green to Teal
        ["#ec4899", "#f43f5e"],  // Pink to Rose
        ["#eab308", "#f97316"],  // Yellow to Orange
        ["#6366f1", "#3b82f6"],  // Indigo to Blue
        ["#06b6d4", "#0ea5e9"],  // Cyan to Sky
        ["#a855f7", "#ec4899"],  // Purple to Pink
    ];
    
    let sum = 0;
    for (let i = 0; i < value.length; i++) {
        sum += value.charCodeAt(i);
    }
    
    return colorPairs[sum % colorPairs.length];
}
