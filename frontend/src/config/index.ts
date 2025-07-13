// Frontend configuration based on environment
export const config = {
  // API Configuration
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "/api",
} as const;

export const getApiUrl = (endpoint: string) => {
  const baseUrl = config.apiBaseUrl;
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${baseUrl}${cleanEndpoint}`;
};
