/** @type {import('next').NextConfig} */

const ARCHITECT_BASE_PATH =
  process.env.NEXT_PUBLIC_ARCHITECT_BASE_PATH || "/semantik_architect";

// Lets you override host/port without rewriting paths.
const ARCHITECT_API_ORIGIN =
  process.env.NEXT_PUBLIC_ARCHITECT_API_ORIGIN || "http://localhost:8000";

const origin = (ARCHITECT_API_ORIGIN || "").replace(/\/+$/, "");
const basePath = (ARCHITECT_BASE_PATH || "/semantik_architect").startsWith("/")
  ? ARCHITECT_BASE_PATH
  : `/${ARCHITECT_BASE_PATH}`;

const DEFAULT_API_BASE_URL = `${origin}${basePath}/api/v1`;

const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,

  // Semantik Architect lives under this path on the main site
  // (matches Nginx + docs/hosting.md).
  basePath,

  // Produce a self-contained build for easier Docker deployment.
  output: "standalone",

  // Public env defaults; can be overridden at build time.
  env: {
    NEXT_PUBLIC_ARCHITECT_API_BASE_URL:
      process.env.NEXT_PUBLIC_ARCHITECT_API_BASE_URL || DEFAULT_API_BASE_URL,
  },
};

export default nextConfig;