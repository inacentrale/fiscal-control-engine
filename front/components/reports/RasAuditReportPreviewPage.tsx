"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";

import {
  getRasAuditReportDownloadUrl,
  getRasAuditReportPreview,
  type RasAuditReportPreview,
  type RasAuditReportPreviewCase,
} from "@/api/agent/rasAuditReport";

type PreviewState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; preview: RasAuditReportPreview };

export default function RasAuditReportPreviewPage({
  auditId,
  sessionId,
  fileId,
}: {
  auditId: string;
  sessionId: string;
  fileId: string;
}) {
  const [state, setState] = useState<PreviewState>({ status: "loading" });

  const loadPreview = useCallback(async () => {
    if (!auditId || !sessionId || !fileId) {
      setState({
        status: "error",
        message: "Les informations nécessaires pour ouvrir ce rapport sont absentes.",
      });
      return;
    }
    setState({ status: "loading" });
    try {
      const preview = await getRasAuditReportPreview(
        auditId,
        sessionId,
        fileId
      );
      setState({ status: "ready", preview });
    } catch {
      setState({
        status: "error",
        message: "L’aperçu du rapport est indisponible ou a expiré.",
      });
    }
  }, [auditId, fileId, sessionId]);

  useEffect(() => {
    void loadPreview();
  }, [loadPreview]);

  return (
    <div className="h-full overflow-y-auto bg-[#f4f7f8]">
      <div className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link
              className="text-sm font-semibold text-[#607783] hover:text-[#203743]"
              href="/"
            >
              ← Retour au contrôle RAS
            </Link>
            <h1 className="mt-3 text-2xl font-bold text-[#102734]">
              Aperçu du rapport d’audit RAS
            </h1>
            <p className="mt-1 text-sm text-[#607783]">
              Consultez la synthèse et les dossiers avant de télécharger le rapport.
            </p>
          </div>
          {state.status === "ready" && (
            <DownloadActions preview={state.preview} sessionId={sessionId} />
          )}
        </header>

        {state.status === "loading" && <PreviewSkeleton />}
        {state.status === "error" && (
          <section className="rounded-2xl border border-red-100 bg-white p-8 text-center shadow-sm">
            <h2 className="font-semibold text-[#203743]">Aperçu indisponible</h2>
            <p className="mt-2 text-sm text-[#607783]">{state.message}</p>
            <button
              className="mt-4 rounded-lg bg-[#102734] px-4 py-2 text-sm font-semibold text-white"
              onClick={() => void loadPreview()}
              type="button"
            >
              Réessayer
            </button>
          </section>
        )}
        {state.status === "ready" && (
          <ReportContent preview={state.preview} />
        )}
      </div>
    </div>
  );
}

function ReportContent({ preview }: { preview: RasAuditReportPreview }) {
  const summary = preview.summary;
  return (
    <div className="space-y-6">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi label="Dossiers analysés" value={summary.case_count} />
        <Kpi label="Dossiers conclus" value={summary.concluded_count} />
        <Kpi label="Anomalies à examiner" value={summary.anomaly_count} />
        <Kpi label="Dossiers indéterminables" value={summary.indeterminate_count} />
        <Kpi label="Dossiers incomplets" value={summary.blocked_count} />
      </section>

      {(summary.amounts.length > 0 || summary.top_blockers.length > 0) && (
        <section className="grid gap-4 lg:grid-cols-2">
          <SummaryCard title="Montants par devise">
            {summary.amounts.length === 0 ? (
              <EmptyText>Les montants ne sont pas encore calculables.</EmptyText>
            ) : (
              summary.amounts.map((amount) => (
                <div
                  className="grid grid-cols-2 gap-2 border-t border-[#edf1f3] py-3 text-sm first:border-0"
                  key={`${amount.currency}-${amount.certainty}`}
                >
                  <div>
                    <p className="font-semibold text-[#203743]">{amount.currency}</p>
                    <p className="text-xs text-[#607783]">{amount.certainty}</p>
                  </div>
                  <div className="text-right text-[#43606d]">
                    <p>Théorique : {amount.expected_amount}</p>
                    <p>Comptabilisée : {amount.recorded_amount}</p>
                    <p>Écart : {amount.difference}</p>
                  </div>
                </div>
              ))
            )}
          </SummaryCard>
          <SummaryCard title="Principales informations manquantes">
            {summary.top_blockers.length === 0 ? (
              <EmptyText>Aucune information bloquante recensée.</EmptyText>
            ) : (
              summary.top_blockers.map((blocker) => (
                <div
                  className="flex items-center justify-between border-t border-[#edf1f3] py-3 text-sm first:border-0"
                  key={blocker.label}
                >
                  <span className="text-[#43606d]">{blocker.label}</span>
                  <span className="rounded-full bg-[#fff4ed] px-2.5 py-1 font-semibold text-[#c8563f]">
                    {blocker.count}
                  </span>
                </div>
              ))
            )}
          </SummaryCard>
        </section>
      )}

      <section className="overflow-hidden rounded-2xl border border-[#dfe7eb] bg-white shadow-sm">
        <div className="border-b border-[#edf1f3] px-5 py-4">
          <h2 className="font-semibold text-[#203743]">Dossiers du rapport</h2>
          <p className="mt-1 text-xs text-[#607783]">
            {preview.cases.length.toLocaleString("fr-FR")} dossier
            {preview.cases.length > 1 ? "s" : ""} affiché
            {preview.cases.length > 1 ? "s" : ""}
          </p>
        </div>
        {preview.cases.length === 0 ? (
          <div className="p-10 text-center text-sm text-[#607783]">
            Aucun dossier à présenter dans ce rapport.
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto lg:block">
              <DesktopTable cases={preview.cases} />
            </div>
            <div className="divide-y divide-[#edf1f3] lg:hidden">
              {preview.cases.map((item, index) => (
                <MobileCaseCard item={item} key={`${item.document_reference}-${index}`} />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function DesktopTable({ cases }: { cases: RasAuditReportPreviewCase[] }) {
  return (
    <table className="min-w-[1180px] w-full text-left text-xs">
      <thead className="sticky top-0 bg-[#f3f7f8] text-[#43606d]">
        <tr>
          {[
            "Pièce",
            "Période",
            "Compte",
            "Nature",
            "Fournisseur",
            "Statut",
            "Priorité",
            "Action recommandée",
            "Écart",
          ].map((label) => (
            <th className="whitespace-nowrap px-4 py-3 font-semibold" key={label}>
              {label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {cases.map((item, index) => (
          <tr className="border-t border-[#edf1f3] align-top" key={`${item.document_reference}-${index}`}>
            <Cell>{item.document_reference || "Non renseignée"}</Cell>
            <Cell>{item.period || "Non renseignée"}</Cell>
            <Cell>{item.account_number || "Non renseigné"}</Cell>
            <Cell>{item.operation_nature}</Cell>
            <Cell>{item.supplier_reference || "Non renseigné"}</Cell>
            <Cell>{item.status}</Cell>
            <Cell>{item.priority}</Cell>
            <Cell>{item.recommended_action}</Cell>
            <Cell>{formatDifference(item)}</Cell>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MobileCaseCard({ item }: { item: RasAuditReportPreviewCase }) {
  return (
    <article className="space-y-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-[#203743]">
            {item.document_reference || "Pièce non renseignée"}
          </p>
          <p className="text-xs text-[#607783]">
            {item.period || "Période inconnue"} · compte {item.account_number || "inconnu"}
          </p>
        </div>
        <span className="rounded-full bg-[#f2f6f8] px-2.5 py-1 text-xs font-semibold text-[#43606d]">
          {item.priority}
        </span>
      </div>
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <CaseFact label="Nature" value={item.operation_nature} />
        <CaseFact label="Fournisseur" value={item.supplier_reference || "Non renseigné"} />
        <CaseFact label="Statut" value={item.status} />
        <CaseFact label="Écart" value={formatDifference(item)} />
      </dl>
      <div className="rounded-lg bg-[#f7f9fa] p-3 text-sm text-[#43606d]">
        <span className="font-semibold">Action : </span>
        {item.recommended_action}
      </div>
    </article>
  );
}

function DownloadActions({
  preview,
  sessionId,
}: {
  preview: RasAuditReportPreview;
  sessionId: string;
}) {
  const formats = [
    { format: "xlsx", label: "Excel" },
    { format: "pdf", label: "PDF" },
  ] as const;
  return (
    <div className="flex flex-wrap gap-2">
      {formats.map(({ format, label }) => (
        <a
          className={
            format === "xlsx"
              ? "rounded-lg bg-[#102734] px-3 py-2 text-xs font-semibold text-white"
              : "rounded-lg border border-[#d7e0e4] bg-white px-3 py-2 text-xs font-semibold text-[#43606d]"
          }
          download
          href={getRasAuditReportDownloadUrl(
            preview.auditId,
            sessionId,
            preview.fileId,
            format
          )}
          key={format}
        >
          Télécharger {label}
        </a>
      ))}
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-[#dfe7eb] bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-[#607783]">{label}</p>
      <p className="mt-2 text-2xl font-bold text-[#203743]">
        {value.toLocaleString("fr-FR")}
      </p>
    </div>
  );
}

function SummaryCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-[#dfe7eb] bg-white p-5 shadow-sm">
      <h2 className="font-semibold text-[#203743]">{title}</h2>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function EmptyText({ children }: { children: ReactNode }) {
  return <p className="py-3 text-sm text-[#607783]">{children}</p>;
}

function Cell({ children }: { children: ReactNode }) {
  return <td className="max-w-[220px] px-4 py-3 text-[#203743]">{children}</td>;
}

function CaseFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-[#7d8d97]">{label}</dt>
      <dd className="mt-0.5 text-[#203743]">{value}</dd>
    </div>
  );
}

function formatDifference(item: RasAuditReportPreviewCase): string {
  return item.difference === null
    ? "Non calculable"
    : `${item.difference} ${item.currency || ""}`.trim();
}

function PreviewSkeleton() {
  return (
    <div aria-label="Chargement de l’aperçu" className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }, (_, index) => (
          <div className="h-24 animate-pulse rounded-2xl bg-white" key={index} />
        ))}
      </div>
      <div className="h-[420px] animate-pulse rounded-2xl bg-white" />
    </div>
  );
}
