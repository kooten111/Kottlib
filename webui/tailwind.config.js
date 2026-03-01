/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Use CSS variables for dynamic theming
				dark: {
					bg: 'var(--color-bg)',
					'bg-secondary': 'var(--color-secondary-bg)',
					'bg-tertiary': 'var(--color-tertiary-bg)',
					text: 'var(--color-text)',
					'text-secondary': 'var(--color-text-secondary)',
					'text-muted': 'var(--color-text-muted)'
				},
				// Accent colors
				accent: {
					orange: 'var(--color-accent)',
					'orange-hover': 'var(--color-accent-hover)',
					blue: 'var(--color-accent-blue)'
				},
				// Status colors
				status: {
					success: 'var(--color-success)',
					warning: 'var(--color-warning)',
					error: 'var(--color-error)'
				}
			},
			spacing: {
				// 4px base spacing scale
				'0.5': '2px',
				'1': '4px',
				'2': '8px',
				'3': '12px',
				'4': '16px',
				'6': '24px',
				'8': '32px',
				'12': '48px',
				'16': '64px'
			},
			borderRadius: {
				card: '8px',
				button: '4px'
			},
			maxWidth: {
				content: '1400px'
			}
		}
	},
	plugins: [
		require('@tailwindcss/forms')
	]
};
