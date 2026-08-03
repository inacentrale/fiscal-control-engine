import type { ValidationCheckResponse } from "@/api/taxDeclarations/types";

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  passed: { label: "Conforme", className: "bg-[#e9f9f2] text-[#12855f]" },
  failed: { label: "Anomalie", className: "bg-[#fff1ed] text-[#c8563f]" },
  not_evaluated: {
    label: "À confirmer",
    className: "bg-[#fff6e5] text-[#a86a12]",
  },
};

const SEVERITY_LABELS: Record<string, string> = {
  error: "Erreur",
  warning: "Avertissement",
  info: "Information",
};

export default function ValidationReportPanel({
  overallStatus,
  checks,
}: {
  overallStatus: string;
  checks: ValidationCheckResponse[];
}) {
  if (checks.length === 0) {
    return (
      <p className="rounded-[14px] bg-[#f7fafb] px-4 py-3 text-[13px] font-medium text-[#60737e]">
        Aucun contrôle de validation disponible pour cette déclaration.
      </p>
    );
  }

  const overall = STATUS_STYLES[overallStatus] ?? {
    label: overallStatus,
    className: "bg-[#f2f6f8] text-[#60737e]",
  };

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-semibold text-[#102734]">
          Statut global
        </span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${overall.className}`}
        >
          {overall.label}
        </span>
      </div>

      <div className="space-y-2">
        {checks.map((check) => (
          <ValidationCheckCard key={check.check_id} check={check} />
        ))}
      </div>
    </section>
  );
}

function ValidationCheckCard({ check }: { check: ValidationCheckResponse }) {
  const status = STATUS_STYLES[check.status] ?? {
    label: check.status,
    className: "bg-[#f2f6f8] text-[#60737e]",
  };
  const hasComparison =
    check.expected_value !== null || check.actual_value !== null;

  return (
    <article className="rounded-[14px] border border-[#edf3f6] bg-white p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[13px] font-semibold text-[#102734]">
            {formatCheckId(check.check_id)}
          </p>
          <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-[#8a98a2]">
            {check.layer} · {SEVERITY_LABELS[check.severity] ?? check.severity}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${status.className}`}
        >
          {status.label}
        </span>
      </div>

      <p className="mt-2 text-[12px] leading-5 text-[#40515c]">
        {check.message}
      </p>

      {hasComparison && (
        <dl className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
          <ComparisonValue label="Attendu" value={check.expected_value} />
          <ComparisonValue label="Déclaré" value={check.actual_value} />
          <ComparisonValue label="Écart" value={check.difference} />
        </dl>
      )}

      {(check.expected_date || check.actual_date) && (
        <dl className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
          <ComparisonValue label="Échéance attendue" value={check.expected_date} />
          <ComparisonValue label="Date constatée" value={check.actual_date} />
        </dl>
      )}

      {check.affected_lines.length > 0 && (
        <p className="mt-2 text-[11px] font-medium text-[#8a98a2]">
          Lignes concernées : {check.affected_lines.join(", ")}
        </p>
      )}

      {(check.source_url || check.source_locator) && (
        <p className="mt-2 border-t border-[#edf3f6] pt-2 text-[11px] font-medium text-[#8a98a2]">
          Source :{" "}
          {check.source_url ? (
            <a
              href={check.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-[#3664ff] underline"
            >
              {check.source_locator || check.source_url}
            </a>
          ) : (
            check.source_locator
          )}
        </p>
      )}
    </article>
  );
}

function ComparisonValue({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-wide text-[#8a98a2]">
        {label}
      </dt>
      <dd className="mt-0.5 font-semibold text-[#203743]">{value ?? "—"}</dd>
    </div>
  );
}

function formatCheckId(checkId: string): string {
  return checkId.replaceAll("_", " ").replace(/^./, (char) => char.toUpperCase());
}
