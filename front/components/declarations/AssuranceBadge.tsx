import type { TaxAssuranceAssessmentResponse } from "@/api/taxDeclarations/types";

const LEVEL_STYLES: Record<string, { label: string; className: string }> = {
  limited: { label: "Assurance limitée", className: "bg-[#fff6e5] text-[#a86a12]" },
  reinforced: {
    label: "Assurance renforcée",
    className: "bg-[#e6f0ff] text-[#2451c9]",
  },
  high: { label: "Assurance haute", className: "bg-[#e9f9f2] text-[#12855f]" },
};

const LAYER_LABELS: Record<string, string> = {
  structure: "Structure",
  completeness: "Complétude",
  arithmetic: "Arithmétique",
  fiscal: "Règles fiscales",
  historical: "Historique",
  reconciliation: "Rapprochement",
  statistical: "Statistique",
  supporting_documents: "Pièces justificatives",
  payment_reconciliation: "Rapprochement paiements",
};

export default function AssuranceBadge({
  assurance,
}: {
  assurance: TaxAssuranceAssessmentResponse;
}) {
  const level = LEVEL_STYLES[assurance.level] ?? {
    label: assurance.level,
    className: "bg-[#f2f6f8] text-[#60737e]",
  };

  return (
    <section className="rounded-[14px] border border-[#edf3f6] bg-white p-3.5">
      <div className="flex items-center gap-2">
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${level.className}`}
        >
          {level.label}
        </span>
        {assurance.policy_version && (
          <span className="text-[11px] font-medium text-[#8a98a2]">
            Référentiel {assurance.policy_version}
          </span>
        )}
      </div>
      <p className="mt-2 text-[12px] leading-5 text-[#40515c]">
        {assurance.description}
      </p>
      {assurance.missing_layers.length > 0 && (
        <p className="mt-2 text-[11px] font-medium text-[#8a98a2]">
          Couches manquantes :{" "}
          {assurance.missing_layers
            .map((layer) => LAYER_LABELS[layer] ?? layer)
            .join(", ")}
        </p>
      )}
      {assurance.failed_layers.length > 0 && (
        <p className="mt-1 text-[11px] font-medium text-[#c8563f]">
          Couches en échec :{" "}
          {assurance.failed_layers
            .map((layer) => LAYER_LABELS[layer] ?? layer)
            .join(", ")}
        </p>
      )}
    </section>
  );
}
