/** @type {import('next').NextConfig} */
const nextConfig = {
    // Produces a self-contained server bundle in .next/standalone
    // Required for the Docker image to work without node_modules.
    output: "standalone",
};

export default nextConfig;
