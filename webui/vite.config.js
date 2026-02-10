import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	build: {
		// PERFORMANCE OPTIMIZATION: Better minification and chunking
		minify: 'terser',
		terserOptions: {
			compress: {
				drop_console: true, // Remove console.logs in production
				passes: 2,
				dead_code: true,
				drop_debugger: true
			},
			mangle: {
				safari10: true
			}
		},
		rollupOptions: {
			onwarn(warning, warn) {
				// Ignore unused import warnings from external dependencies
				if (
					warning.code === 'UNUSED_EXTERNAL_IMPORT' &&
					warning.ids?.some(id => id.includes('node_modules'))
				) {
					return;
				}
				// Use default warning handler for other warnings
				warn(warning);
			},
			output: {
				// Manual chunking for better caching
				manualChunks: {
					'lucide': ['lucide-svelte'],
					'tanstack': ['@tanstack/svelte-query']
				}
			}
		},
		// Increase chunk size warning limit
		chunkSizeWarningLimit: 600,
		// Enable CSS code splitting
		cssCodeSplit: true,
		// Source maps for debugging (disable in production for smaller bundle)
		sourcemap: false
	},
	server: {
		host: '0.0.0.0', // Listen on all network interfaces
		port: 5173,
		allowedHosts: ['kottlib.kooten.dev', 'localhost'],
		headers: {
			// 'Permissions-Policy': 'browsing-topics=()' // Removed as it causes errors
		},
		// Proxy handled by hooks.server.js in production
		// proxy: {},
		hmr: false // Disable HMR to prevent WebSocket errors behind proxy (requires manual refresh)
	},
	optimizeDeps: {
		// Pre-bundle dependencies for faster dev server startup
		include: ['lucide-svelte', '@tanstack/svelte-query']
	}
});
