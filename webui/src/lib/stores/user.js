import { writable } from 'svelte/store';

// User state store
function createUserStore() {
	const { subscribe, set, update } = writable({
		isAuthenticated: false,
		username: null,
		session: null
	});

	return {
		subscribe,
		login: (username, session) => {
			set({
				isAuthenticated: true,
				username,
				session
			});
		},
		logout: () => {
			set({
				isAuthenticated: false,
				username: null,
				session: null
			});
		},
		update
	};
}

export const userStore = createUserStore();
