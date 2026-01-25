/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
    const { url, request } = event;

    // API endpoints to proxy
    // We strictly proxy paths starting with /v2/ or /api/
    // This allows the backend to handle all data requests
    if (url.pathname.startsWith('/v2/') || url.pathname.startsWith('/api/')) {
        // Use environment variable for backend URL, fallback to localhost for development
        const backendUrl = process.env.BACKEND_URL || 'http://localhost:8081';
        const targetUrl = `${backendUrl}${url.pathname}${url.search}`;

        try {
            // Forward the request to the backend
            // We copy valid headers, excluding ones that might confuse the backend or are controlled by fetch
            const proxiedHeaders = new Headers(request.headers);
            proxiedHeaders.delete('host');
            proxiedHeaders.delete('connection');

            // Forward credentials (cookies) if present
            // Note: In a production environment with different domains, you might need more complex CORS handling
            // But for localhost/same-domain proxying, this usually works well.

            const response = await fetch(targetUrl, {
                method: request.method,
                headers: proxiedHeaders,
                body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.blob() : undefined,
                duplex: 'half' // Required for streaming bodies in some fetch implementations
            });

            // Prepare response headers
            const responseHeaders = new Headers();
            const hasCompression = response.headers.has('content-encoding');

            for (const [key, value] of response.headers) {
                // Always strip connection and host
                if (key === 'connection' || key === 'host') continue;

                // Strip content-encoding (because Node decompressed it)
                if (key === 'content-encoding') continue;

                // Strip transfer-encoding (Node.js handles this automatically)
                if (key === 'transfer-encoding') continue;

                // Strip content-length ONLY if the body was decompressed
                // (The original length refers to the compressed size, which is wrong for the decompressed stream we are sending)
                // If there was no compression (e.g. images, huge CBZ files), we KEEP the length for progress bars.
                if (key === 'content-length' && hasCompression) continue;

                responseHeaders.set(key, value);
            }

            // Return the response from the backend
            return new Response(response.body, {
                status: response.status,
                statusText: response.statusText,
                headers: responseHeaders
            });

        } catch (err) {
            console.error('[Proxy Error]', err);
            return new Response(JSON.stringify({ error: 'Backend unavailable' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            });
        }
    }

    // Default: let SvelteKit handle the request (render the app)
    const response = await resolve(event);
    
    // Filter out problematic Permissions-Policy headers (e.g., browsing-topics which is unrecognized)
    const headers = new Headers(response.headers);
    if (headers.has('permissions-policy')) {
        const policy = headers.get('permissions-policy');
        // Remove browsing-topics if present (unrecognized feature)
        if (policy && policy.includes('browsing-topics')) {
            headers.delete('permissions-policy');
        }
    }
    
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
    });
}
