import useAlertStore from "@/store/alertStore";
import { handleServerError } from "@/utils/api/errors";
import { useMutation } from "@tanstack/react-query";
import { deleteData } from "../api";

export const useDelete = ({
  url,
  onSuccess,
  onError,
  enabled = true,
}: UseDeleteOptions) => {
  const { setAlert } = useAlertStore.getState();

  const mutationFn = async (): Promise<any> => {
    const response = await deleteData(url);

    return response;
  };

  const mutation = useMutation({
    mutationFn,
    onSuccess: (data: any) => {
      if (onSuccess) {
        onSuccess(data?.data);
      }
      setAlert({ content: data.message });
    },
    onError: (error: any) => {
      handleServerError(error);
      if (onError) {
        onError(error);
      }
    },
  });

  const triggerMutation = (data: any) => {
    if (enabled) {
      mutation.mutate(data);
    }
  };

  return {
    ...mutation,
    triggerMutation,
  };
};
