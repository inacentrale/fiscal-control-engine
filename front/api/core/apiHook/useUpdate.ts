import useAlertStore from "@/store/alertStore";
import { handleServerError } from "@/utils/api/errors";
import { convertStringToNumber, getModifiedFields } from "@/utils/core/objects";
import { hasFiles, objectToFormData } from "@/utils/api/forms";
import { putData } from "../api";
import { useMutation } from "@tanstack/react-query";

export const useUpdate = <T = any>({
  url,
  onSuccess,
  onError,
  setErrors,
  setState,
  enabled = true,
}: UseUpdateOptions<T>) => {
  const { setAlert } = useAlertStore.getState();

  const mutationFn = async (primitiveData: any): Promise<ApiResponse<T>> => {
    if (setErrors) {
      setErrors({});
    }

    const data = convertStringToNumber(primitiveData);
    const isFormData = hasFiles(data);
    const submissionData = isFormData ? objectToFormData(data) : data;

    return await putData<ApiResponse<T>>(url, submissionData);
  };

  const mutation = useMutation({
    mutationFn,
    onSuccess: (data: ApiResponse<T>) => {
      if (onSuccess) {
        onSuccess(data.data);
      }

      if (setState) {
        setState();
      }

      setAlert({ content: data.message });
    },
    onError: (error: any) => {
      if (onError) {
        onError(error);
      }
      handleServerError(error, undefined, setErrors);
    },
  });

  const triggerMutation = (data?: any, formData?: any) => {
    if (enabled) {
      const submittingData = formData
        ? getModifiedFields({ data, formData })
        : data;
      if (Object.keys(submittingData).length === 0 && formData) return;

      mutation.mutate(submittingData);
    }
  };

  return {
    ...mutation,
    triggerMutation,
  };
};
