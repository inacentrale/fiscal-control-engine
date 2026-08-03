import useAlertStore, { AlertTypeStatus } from "@/store/alertStore";

export class ApiError extends Error {
  status!: number;
  data?: any;

  constructor(status: number, data?: any) {
    super(typeof data === "string" ? data : JSON.stringify(data));
    this.status = status;
    this.data = data;
  }
}

export function handleServerError(
  error: any,
  delay: number | undefined = 5000,
  setErrors: ((errors: any) => void) | null = null
) {
  const { setAlert } = useAlertStore.getState();
  const responseData = error?.data;

  if (setErrors && (responseData?.errors || responseData?.message)) {
    setErrors((prev: any = {}) => ({
      ...prev,
      ...responseData.errors,
      generalMessage: responseData.message,
      type: "error",
    }));
  }

  if (responseData?.message) {
    setAlert({
      content: responseData?.message,
      delay: delay,
      type: AlertTypeStatus.ERROR,
    });
  }
}
