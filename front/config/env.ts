const env = {
  API_URL: process.env.API_URL || "http://localhost:8001",
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || "/api",
  NEXT_PUBLIC_BASE_URL: process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3002",
};

export const APP_CONFIG = {
  env,
  isServer: typeof window === "undefined",
} as const;

export default APP_CONFIG;
