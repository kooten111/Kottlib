/**
 * Zinc Dark Theme
 * Based on Tailwind's Zinc color palette
 */
export const zincDark = {
    id: 'zinc-dark',
    name: 'Zinc Dark',
    type: 'dark',
    colors: {
        // Background colors
        // zinc-950: #09090b
        bg: '#09090b',
        // zinc-900: #18181b
        bgSecondary: '#18181b',
        // zinc-800: #27272a
        bgTertiary: '#27272a',

        // Text colors
        // white: #ffffff
        text: '#ffffff',
        // zinc-400: #a1a1aa
        textSecondary: '#a1a1aa',
        // zinc-500: #71717a
        textMuted: '#71717a',

        // Accent colors (using orange as default accent to match existing app feel, or could use zinc-100)
        accent: '#ff6740',
        accentHover: '#ff8566',
        accentBlue: '#4a90e2',

        // Border colors
        // zinc-800: #27272a -> used as border-zinc-800
        border: '#27272a',
        // zinc-700: #3f3f46
        borderStrong: '#3f3f46',
        borderHover: '#52525b',

        // Status colors
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',

        // Overlay colors
        overlay: 'rgba(9, 9, 11, 0.8)', // zinc-950 with opacity
        overlayLight: 'rgba(9, 9, 11, 0.5)'
    }
};
