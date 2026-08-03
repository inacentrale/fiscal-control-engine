import { ApiError } from "@/utils/api/errors";
import { ROUTES } from "@/utils/constants/routes";
import { APP_CONFIG } from "@/config";

const buildHeaders = (): HeadersInit | undefined => {
  return {
    "Content-Type": "application/json",
  };
};

export function getApiBase(isServer?: boolean) {
  if (isServer) {
    return APP_CONFIG.env.API_URL;
  }
  return APP_CONFIG.env.NEXT_PUBLIC_API_BASE_URL;
}

export const buildUrl = (url: string, params?: Record<string, string | undefined | null>): string => {
  if (!params) return url;

  const filteredParams = Object.entries(params)
    .filter(([, value]) => value !== undefined)
    .reduce((acc, [key, value]) => ({ ...acc, [key]: value! }), {});

  const queryParams = new URLSearchParams(filteredParams).toString();
  return queryParams ? `${url}?${queryParams}` : url;
};

export const joinUrl = (base: string | undefined, url: string): string => {
  const sanitizedBase = base?.replace(/\/$/, "") || "";
  const sanitizedUrl = url.replace(/^\//, "");
  return `${sanitizedBase}/${sanitizedUrl}`;
};

let refreshTokenRequest: Promise<boolean> | null = null;

const refreshTokens = async (): Promise<boolean> => {
  if (!refreshTokenRequest) {
    refreshTokenRequest = (async () => {
      const apiBase = getApiBase(false);
      const response = await fetch(joinUrl(apiBase, "auth/refresh-token"), {
        method: "POST",
        credentials: "include",
      });

      return response.ok;
    })().finally(() => {
      refreshTokenRequest = null;
    });
  }

  return refreshTokenRequest;
};

const makeRequest = async (url: string, options: RequestInit & { isServer?: boolean }) => {
  try {
    const apiBase = getApiBase(options?.isServer);
    const response = await fetch(joinUrl(apiBase, url), options);
    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    return { response, data };
  } catch (error) {
    // Return a mock error response for server-side when API is not available
    if (options?.isServer) {
      return {
        response: { ok: false, status: 503 } as Response,
        data: { error: 'Service unavailable' }
      };
    }
    throw error;
  }
};

const fetchWithRetry = async <T>(
  url: string,
  options: RequestInit & { isServer?: boolean }
): Promise<T> => {
  const { response, data } = await makeRequest(url, options);

  if (!response.ok) {
    if (
      data?.code === 'TOKEN_EXPIRED' &&
      typeof window !== 'undefined' &&
      !url.startsWith('auth/refresh-token')
    ) {
      const refreshed = await refreshTokens();

      if (refreshed) {
        const retry = await makeRequest(url, options);
        if (retry.response.ok) {
          return retry.data as T;
        }
      }

      const from = window.location.pathname + window.location.search;
      window.location.href = `${ROUTES.LOGIN}?from=${encodeURIComponent(from)}`;
      return new Promise<T>(() => { });
    }

    throw new ApiError(response.status, data);
  }

  return data;
};

const fetchData = async <T>(
  url: string,
  options: FetchDataOptions & { cache?: RequestCache, isServer?: boolean } = { method: "GET", cache: "no-cache" }
): Promise<T> => {
  const { method, body, params, customHeaders, cache = "no-cache", isServer } = options;
  const fullUrl = buildUrl(url, params);

  let headers = buildHeaders();
  if (body instanceof FormData) {
    headers = {};
  }

  if (customHeaders) {
    headers = { ...headers, ...customHeaders };
  }

  const processedBody =
    body instanceof FormData ? body : body ? JSON.stringify(body) : undefined;

  const effectiveCache = isServer ? 'force-cache' : cache;

  return fetchWithRetry<T>(fullUrl, {
    method,
    headers,
    credentials: "include",
    body: processedBody,
    cache: effectiveCache,
    isServer
  });
};

export const getData = <T>(
  url: string,
  params?: Record<string, string | null | undefined>,
  customHeaders?: HeadersInit,
  isServer?: boolean
): Promise<T> => fetchData<T>(url, { method: "GET", params, customHeaders, isServer });

export const postData = <T>(url: string, body?: unknown, customHeaders?: HeadersInit): Promise<T> =>
  fetchData<T>(url, { method: "POST", body, customHeaders });

export const putData = <T>(url: string, body: unknown): Promise<T> =>
  fetchData<T>(url, { method: "PUT", body });

export const deleteData = <T>(url: string): Promise<T> =>
  fetchData<T>(url, { method: "DELETE" });
