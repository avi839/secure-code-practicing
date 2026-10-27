/** @type {import('next').NextConfig} */

// The browser only ever calls same-origin /api/* (decision D5). Next proxies those
// requests to the FastAPI backend. Use 127.0.0.1 rather than localhost: Node 24
// resolves localhost to ::1 first while uvicorn binds 127.0.0.1.
// Rewrites are evaluated at build time, so set BACKEND_URL before `npm run build`.
const BACKEND_URL = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
