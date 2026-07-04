/** @type {import('next').NextConfig} */
const nextConfig = {
  // No eslint config is shipped; skip lint during build (type checking stays on).
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
