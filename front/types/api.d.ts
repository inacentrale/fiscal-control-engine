import type { Dispatch, SetStateAction } from "react";

declare global {
  interface ApiResponse<T> {
    data: T;
    message: string;
  }

  interface ApiPagination {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  }

  interface ApiPaginatedResponse<T> {
    data: T[];
    pagination: ApiPagination;
    message?: string;
  }

  interface FetchDataOptions {
    method: "GET" | "POST" | "PUT" | "DELETE";
    body?: unknown;
    params?: Record<string, string | null | undefined>;
    customHeaders?: HeadersInit;
  }

  type SetErrors = Dispatch<SetStateAction<Record<string, unknown>>>;

  type UseApiOptions<T = unknown> = {
    url: string;
    onSuccess?: (data: T) => void;
    onError?: (error: unknown) => void;
    enabled?: boolean;
    alertDelay?: number;
  };

  type UseGetOptions<T = unknown> = UseApiOptions<T> & {
    queryKey?: string[] | string;
    params?: Record<string, string | number | boolean | null | undefined>;
    retry?: number;
  };

  type UseStoreOptions<T = unknown> = UseApiOptions<T> & {
    setErrors?: SetErrors;
    setState?: () => void;
  };

  type UseDeleteOptions = UseApiOptions<unknown>;
  type UseUpdateOptions<T = unknown> = UseStoreOptions<T>;
}

export {};
