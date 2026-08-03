import { useMutation } from "@tanstack/react-query";

import { analyzeTaxDeclaration } from "@/api/taxDeclarations/analyzeTaxDeclaration";
import type { TaxDeclarationErrorResponse } from "@/api/taxDeclarations/types";
import useAlertStore, { AlertTypeStatus } from "@/store/alertStore";
import { ApiError } from "@/utils/api/errors";

const DEFAULT_ERROR_MESSAGE = "L'analyse de la declaration a echoue.";

const extractErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    const data = error.data as TaxDeclarationErrorResponse | undefined;
    return data?.error?.message || DEFAULT_ERROR_MESSAGE;
  }
  return DEFAULT_ERROR_MESSAGE;
};

export const useAnalyzeTaxDeclaration = () => {
  const { setAlert } = useAlertStore();

  const mutation = useMutation({
    mutationFn: analyzeTaxDeclaration,
    onError: (error: unknown) => {
      setAlert({ content: extractErrorMessage(error), type: AlertTypeStatus.ERROR });
    },
  });

  return {
    analyze: mutation.mutate,
    result: mutation.data ?? null,
    isAnalyzing: mutation.isPending,
    errorMessage: mutation.isError ? extractErrorMessage(mutation.error) : null,
    reset: mutation.reset,
  };
};
