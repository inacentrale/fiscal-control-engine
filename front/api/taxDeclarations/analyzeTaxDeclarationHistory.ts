import { postData } from "@/api/core/api";

import type {
  TaxDeclarationHistoryResponse,
  TaxDeclarationType,
} from "./types";

export type AnalyzeTaxDeclarationHistoryParams = {
  currentFile: File;
  previousFile: File;
  declarationType: TaxDeclarationType;
  currentPeriodEnd: string;
  previousPeriodEnd: string;
  tolerance?: string;
};

export const analyzeTaxDeclarationHistory = ({
  currentFile,
  previousFile,
  declarationType,
  currentPeriodEnd,
  previousPeriodEnd,
  tolerance,
}: AnalyzeTaxDeclarationHistoryParams): Promise<TaxDeclarationHistoryResponse> => {
  const formData = new FormData();
  formData.append("current_file", currentFile);
  formData.append("previous_file", previousFile);
  formData.append("declaration_type", declarationType);
  formData.append("current_period_end", currentPeriodEnd);
  formData.append("previous_period_end", previousPeriodEnd);
  if (tolerance) formData.append("tolerance", tolerance);

  return postData<TaxDeclarationHistoryResponse>(
    "tax-declarations/analyze-history",
    formData
  );
};
