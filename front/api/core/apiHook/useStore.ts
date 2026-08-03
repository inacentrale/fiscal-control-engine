import useAlertStore from "@/store/alertStore";
import { ApiError, handleServerError } from "@/utils/api/errors";
import { convertStringToNumber, getModifiedFields } from "@/utils/core/objects";
import { hasFiles, objectToFormData } from "@/utils/api/forms";
import { postData } from "../api";
import { useMutation } from "@tanstack/react-query";

export const useStore = <T = any>({
  url,
  onSuccess,
  onError,
  setErrors,
  setState,
  enabled = true,
  alertDelay = 5000,
  skipConvert = false,
}: UseStoreOptions<T> & { skipConvert?: boolean }) => {
  const { setAlert } = useAlertStore.getState();

  const mutationFn = async (primitiveData: any): Promise<ApiResponse<T>> => {
    if (setErrors) {
      setErrors({});
    }
    const data = skipConvert ? primitiveData : convertStringToNumber(primitiveData);
    const isFormData = hasFiles(primitiveData);
    const submissionData = isFormData ? objectToFormData(data) : data;

    return await postData<ApiResponse<T>>(url, submissionData);
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

      if (setErrors) {
        setErrors((prev: any = {}) => ({ ...prev, generalMessage: data.message, type: "success" }));
      }

      setAlert({ content: data.message });
    },
    onError: (error: any) => {
      if (error instanceof ApiError) {
        if (onError) {
          onError(error);
        }

        handleServerError(error, alertDelay, setErrors);
      }
    },
  });

  const triggerMutation = (data?: any, formData?: any) => {
    if (enabled) {
      const submittingData = formData
        ? getModifiedFields({ data, formData })
        : data;
      if (Object.keys(submittingData).length === 0) return;

      mutation.mutate(submittingData);
    }
  };

  return {
    ...mutation,
    triggerMutation,
  };
};
