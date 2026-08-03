import { postData } from "@/api/core/api";

import type {
  TaxDeclarationAnalysisResponse,
  TaxDeclarationType,
} from "./types";

export type AnalyzeTaxDeclarationParams = {
  file: File;
  declarationType: TaxDeclarationType;
  periodEnd?: string;
  filingDate?: string;
  tolerance?: string;
};

export const analyzeTaxDeclaration = ({
  file,
  declarationType,
  periodEnd,
  filingDate,
  tolerance,
}: AnalyzeTaxDeclarationParams): Promise<TaxDeclarationAnalysisResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("declaration_type", declarationType);
  if (periodEnd) formData.append("period_end", periodEnd);
  if (filingDate) formData.append("filing_date", filingDate);
  if (tolerance) formData.append("tolerance", tolerance);

  return postData<TaxDeclarationAnalysisResponse>(
    "tax-declarations/analyze",
    formData
  );
};
