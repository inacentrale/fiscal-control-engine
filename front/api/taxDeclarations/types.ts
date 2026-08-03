export type TaxDeclarationType =
  | "vat"
  | "withholding_tax"
  | "payroll_tax"
  | "corporate_income_tax";

export type CanonicalFieldResponse = {
  name: string;
  source_value: unknown;
  normalized_value: unknown;
  confidence: number;
  status: string;
  locator: string;
};

export type CanonicalRecordResponse = {
  record_type: string;
  fields: CanonicalFieldResponse[];
};

export type CanonicalDeclarationResponse = {
  schema_version: string;
  declaration_type: string;
  fields: CanonicalFieldResponse[];
  records: CanonicalRecordResponse[];
};

export type TaxDeclarationIngestionResponse = {
  file_name: string;
  source_format: string;
  format_confidence: number;
  format_evidence: string;
  content_sha256: string;
  declaration_type: string;
  status: string;
  reason: string | null;
  declaration: CanonicalDeclarationResponse | null;
};

export type ValidationCheckResponse = {
  check_id: string;
  layer: string;
  status: string;
  severity: string;
  message: string;
  source_url: string | null;
  source_locator: string | null;
  expected_value: string | null;
  actual_value: string | null;
  difference: string | null;
  expected_date: string | null;
  actual_date: string | null;
  affected_lines: string[];
};

export type TaxDeclarationValidationResponse = {
  overall_status: string;
  checks: ValidationCheckResponse[];
};

export type TaxAssuranceAssessmentResponse = {
  level: string;
  policy_id: string | null;
  policy_version: string | null;
  description: string;
  passed_layers: string[];
  missing_layers: string[];
  failed_layers: string[];
};

export type TaxDeclarationAnalysisResponse = TaxDeclarationIngestionResponse & {
  validation: TaxDeclarationValidationResponse | null;
  assurance: TaxAssuranceAssessmentResponse | null;
};

export type TaxDeclarationHistoryResponse = {
  current: TaxDeclarationIngestionResponse;
  previous: TaxDeclarationIngestionResponse;
  validation: TaxDeclarationValidationResponse | null;
};

export type TaxDeclarationErrorResponse = {
  error: {
    code: string;
    message: string;
  };
};

export const TAX_DECLARATION_TYPE_LABELS: Record<TaxDeclarationType, string> = {
  vat: "TVA",
  withholding_tax: "RAS",
  payroll_tax: "IUTS",
  corporate_income_tax: "IS",
};

// Cote API, seuls vat et corporate_income_tax ont un controle historique
// branche sur /analyze-history (RAS/IUTS retournent validation: null sans
// erreur) — voir api/app/routers/tax_declaration.py.
export const TAX_DECLARATION_TYPES_WITH_HISTORY: readonly TaxDeclarationType[] = [
  "vat",
  "corporate_income_tax",
];
