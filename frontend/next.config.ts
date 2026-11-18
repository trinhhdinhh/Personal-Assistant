import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */

async rewrites() {
return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
},
  agentRules: false,
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    agentUpgrade: "security",
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};


export default nextConfig;
