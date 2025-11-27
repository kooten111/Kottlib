/**
 * Theme Registry
 * Automatically discovers and loads all theme files
 */

// Dynamically import all theme files using Vite's glob import
// This automatically picks up any .js files in the themes directory
const themeModules = import.meta.glob('./*.js', { eager: true });

// Build themes object from discovered modules
export const themes = {};

for (const path in themeModules) {
    // Skip the index.js file itself
    if (path === './index.js') continue;

    const module = themeModules[path];
    // Get the first exported theme object from each module
    const themeExport = Object.values(module)[0];

    if (themeExport && themeExport.id && themeExport.name && themeExport.type && themeExport.colors) {
        themes[themeExport.id] = themeExport;
    }
}

// Get all themes as an array
export const getAllThemes = () => Object.values(themes);

// Get themes by type
export const getLightThemes = () => getAllThemes().filter(theme => theme.type === 'light');
export const getDarkThemes = () => getAllThemes().filter(theme => theme.type === 'dark');

// Get a specific theme by ID
export const getThemeById = (id) => themes[id] || null;

// Default themes
export const DEFAULT_LIGHT_THEME = 'catppuccin-latte';
export const DEFAULT_DARK_THEME = 'catppuccin-mocha';

/**
 * Apply a theme to the document
 * @param {Object} theme - The theme object to apply
 */
export function applyTheme(theme) {
    if (!theme || !theme.colors) {
        console.error('Invalid theme object', theme);
        return;
    }

    const root = document.documentElement;
    const colors = theme.colors;

    // Apply all color variables
    root.style.setProperty('--color-bg', colors.bg);
    root.style.setProperty('--color-secondary-bg', colors.bgSecondary);
    root.style.setProperty('--color-tertiary-bg', colors.bgTertiary);

    root.style.setProperty('--color-text', colors.text);
    root.style.setProperty('--color-text-secondary', colors.textSecondary);
    root.style.setProperty('--color-text-muted', colors.textMuted);

    root.style.setProperty('--color-accent', colors.accent);
    root.style.setProperty('--color-accent-hover', colors.accentHover);
    root.style.setProperty('--color-accent-blue', colors.accentBlue);

    root.style.setProperty('--color-border', colors.border);
    root.style.setProperty('--color-border-strong', colors.borderStrong);
    root.style.setProperty('--color-border-hover', colors.borderHover);

    root.style.setProperty('--color-success', colors.success);
    root.style.setProperty('--color-warning', colors.warning);
    root.style.setProperty('--color-error', colors.error);

    root.style.setProperty('--color-overlay', colors.overlay);
    root.style.setProperty('--color-overlay-light', colors.overlayLight);
}
