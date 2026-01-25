import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter(),
		alias: {
			$lib: 'src/lib',
			$components: 'src/lib/components',
			$stores: 'src/lib/stores',
			$api: 'src/lib/api',
			$utils: 'src/lib/utils',
			$types: 'src/lib/types'
		}
	}
};

export default config;
