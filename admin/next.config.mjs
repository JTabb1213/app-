/** @type {import('next').NextConfig} */
const nextConfig = {
    // Produces a self-contained server bundle in .next/standalone
    // Required for the Docker image to work without node_modules.
    output: "standalone",

    // Add cache headers to prevent browser caching issues
    async headers() {
        return [
            {
                source: '/(.*)',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'no-cache, no-store, must-revalidate',
                    },
                    {
                        key: 'Pragma',
                        value: 'no-cache',
                    },
                    {
                        key: 'Expires',
                        value: '0',
                    },
                ],
            },
            {
                source: '/_next/static/(.*)',
                headers: [
                    {
                        key: 'Cache-Control',
                        value: 'public, max-age=31536000, immutable',
                    },
                ],
            },
        ];
    },

    // Generate build ID based on timestamp for cache busting
    generateBuildId: async () => {
        return `build-${Date.now()}`;
    },
};

export default nextConfig;
