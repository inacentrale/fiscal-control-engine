import { create } from "zustand";

export enum AlertTypeStatus {
  ERROR = "error",
  SUCCESS = "success",
  INFO = "info",
}

interface AlertType {
  content: string;
  type?: AlertTypeStatus;
  delay?: number;
}

interface AlertStoreType {
  content: string;
  visible: boolean;
  type: AlertTypeStatus;
  delay: number;
  setAlert: (alert: AlertType) => void;
  clearAlert: () => void;
}

const useAlertStore = create<AlertStoreType>((set) => ({
  content: "",
  visible: false,
  type: AlertTypeStatus.SUCCESS,
  delay: 5000,

  setAlert: (alert: AlertType) =>
    set({
      content: alert.content,
      visible: true,
      type: alert.type || AlertTypeStatus.SUCCESS,
      delay: alert.delay || 5000,
    }),

  clearAlert: () =>
    set({
      content: "",
      visible: false,
    }),
}));

export default useAlertStore;
