import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  basePath: '/ui',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
