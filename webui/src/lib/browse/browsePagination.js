/** Infinite-scroll helpers for the library browse page. */

export const INFINITE_SCROLL_MIN_PRELOAD_PX = 1200;
export const INFINITE_SCROLL_VIEWPORT_MULTIPLIER = 1.5;

export function getPreloadDistancePx(scrollContainer) {
	const viewportHeight =
		scrollContainer?.clientHeight ||
		(typeof window !== 'undefined' ? window.innerHeight : 0);
	return Math.max(
		INFINITE_SCROLL_MIN_PRELOAD_PX,
		Math.round(viewportHeight * INFINITE_SCROLL_VIEWPORT_MULTIPLIER),
	);
}

export function isNearListEnd(scrollContainer) {
	if (typeof window === 'undefined') {
		return false;
	}

	const preloadDistance = getPreloadDistancePx(scrollContainer);

	if (scrollContainer) {
		const remaining =
			scrollContainer.scrollHeight -
			scrollContainer.scrollTop -
			scrollContainer.clientHeight;
		return remaining <= preloadDistance;
	}

	const doc = document.documentElement;
	const remaining = doc.scrollHeight - window.scrollY - window.innerHeight;
	return remaining <= preloadDistance;
}

/**
 * Svelte action: observe a sentinel and trigger pagination near the list end.
 */
export function infiniteScroll(node, options) {
	let scrollContainer = options?.scrollContainer ?? null;
	let onLoadMore = options?.onLoadMore ?? (() => {});
	let onPrefetch = options?.onPrefetch ?? (() => {});

	const createObserver = () =>
		new IntersectionObserver(
			(entries) => {
				if (entries[0]?.isIntersecting) {
					onLoadMore();
				}
			},
			{
				root: scrollContainer || null,
				rootMargin: `0px 0px ${getPreloadDistancePx(scrollContainer)}px 0px`,
				threshold: 0,
			},
		);

	let observer = createObserver();

	const onScroll = () => {
		// Prefetch only from scroll; IntersectionObserver owns loadMore to avoid dual triggers.
		onPrefetch();
	};

	const onResize = () => {
		observer.disconnect();
		observer = createObserver();
		observer.observe(node);
		if (isNearListEnd(scrollContainer)) {
			onLoadMore();
		}
	};

	observer.observe(node);
	(scrollContainer || window).addEventListener('scroll', onScroll, { passive: true });
	window.addEventListener('resize', onResize);
	onScroll();

	return {
		update(nextOptions) {
			scrollContainer = nextOptions?.scrollContainer ?? scrollContainer;
			onLoadMore = nextOptions?.onLoadMore ?? onLoadMore;
			onPrefetch = nextOptions?.onPrefetch ?? onPrefetch;
			onResize();
		},
		destroy() {
			observer.disconnect();
			(scrollContainer || window).removeEventListener('scroll', onScroll);
			window.removeEventListener('resize', onResize);
		},
	};
}
