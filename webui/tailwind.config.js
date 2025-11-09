/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Dark mode palette
				dark: {
					bg: '#1a1a1a',
					'bg-secondary': '#242424',
					'bg-tertiary': '#2d2d2d',
					text: '#e0e0e0',
					'text-secondary': '#a0a0a0'
				},
				// Accent colors
				accent: {
					orange: '#ff6740',
					blue: '#4a90e2'
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
		require('@tailwindcss/typography'),
		require('@tailwindcss/forms')
	]
};
