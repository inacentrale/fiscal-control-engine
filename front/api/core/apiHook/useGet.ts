import useAlertStore from "@/store/alertStore";
import { getData } from "../api";
import { handleServerError } from "@/utils/api/errors";
import { useQuery } from "@tanstack/react-query";

const isApiResponse = <U,>(value: ApiResponse<U> | U): value is ApiResponse<U> =>
  typeof value === "object" && value !== null && "data" in value;

export const useGet = <T = any>({
  queryKey = [],
  url,
  params = {},
  onSuccess,
  onError,
  retry = 0,
  enabled = true,
  alertDelay,
}: UseGetOptions<T>) => {
  const { setAlert } = useAlertStore.getState();
  const cleanParams = params
    ? Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, v === null ? null : String(v)])
      )
    : undefined;

  const queryFn = async (): Promise<T> => {
    try {
      const response = await getData<ApiResponse<T> | T>(url, cleanParams);
      const finalData: T = isApiResponse(response) ? response.data : response;
      
      if (onSuccess) {
        onSuccess(finalData);
      }

      if (isApiResponse(response) && response.message) {
        setAlert({ content: response.message });
      }

      return finalData;
    } catch (error) {
      if (error instanceof Error) {
        handleServerError(error, alertDelay, null);

        if (onError) {
          onError(error);
        }
      }

      throw error;
    }
  };

  return useQuery({
    queryKey: Array.isArray(queryKey) ? queryKey : [queryKey as string],
    queryFn,
    enabled,
    retry,
  });
};
