import type { LedgerQueryResult } from "@/api/agent/types";
import {
  formatLedgerValue,
  getEmptyLedgerColumns,
  getLedgerPageCount,
  getVisibleLedgerColumns,
  LEDGER_COLUMN_LABELS,
} from "@/api/agent/ledgerQueryResult";

export default function AgentLedgerEntriesTable({
  result,
}: {
  result: LedgerQueryResult;
}) {
  const visibleColumns = getVisibleLedgerColumns(result);
  const emptyColumns = getEmptyLedgerColumns(result);
  const pageCount = getLedgerPageCount(result);
  const firstEntry =
    result.totalMatches === 0 ? 0 : (result.page - 1) * result.pageSize + 1;
  const lastEntry = Math.min(
    result.page * result.pageSize,
    result.totalMatches
  );
  const account =
    typeof result.filters.account === "string"
      ? result.filters.account
      : null;

  return (
    <section className="overflow-hidden rounded-xl border border-[#dfe7eb] bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#e7edef] px-4 py-3">
        <div>
          <h3 className="font-semibold text-[#203743]">
            Écritures comptables
          </h3>
          <p className="text-sm text-[#607783]">
            {result.totalMatches.toLocaleString("fr-FR")} correspondance
            {result.totalMatches > 1 ? "s" : ""}
            {account ? ` pour le compte ${account}` : ""}
          </p>
        </div>
        <span className="rounded-full bg-[#eef5f7] px-3 py-1 text-xs font-semibold text-[#43606d]">
          Page {result.page} sur {pageCount}
        </span>
      </div>

      {result.entries.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead className="bg-[#f7f9fa] text-left text-xs uppercase tracking-wide text-[#607783]">
              <tr>
                {visibleColumns.map((column) => (
                  <th
                    key={column}
                    className={`whitespace-nowrap border-b border-[#e7edef] px-4 py-3 font-semibold ${
                      column === "amount" ? "text-right" : ""
                    }`}
                  >
                    {LEDGER_COLUMN_LABELS[column] ?? column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.entries.map((entry, rowIndex) => (
                <tr
                  key={`${result.page}-${rowIndex}`}
                  className="border-b border-[#edf1f3] last:border-b-0 hover:bg-[#f9fbfb]"
                >
                  {visibleColumns.map((column) => (
                    <td
                      key={column}
                      className={`whitespace-nowrap px-4 py-2.5 text-[#29414d] ${
                        column === "amount"
                          ? "text-right font-medium tabular-nums"
                          : ""
                      }`}
                    >
                      {formatLedgerValue(column, entry[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="px-4 py-6 text-sm text-[#607783]">
          Aucune écriture ne correspond aux filtres sélectionnés.
        </p>
      )}

      <div className="space-y-1 border-t border-[#e7edef] bg-[#fbfcfc] px-4 py-3 text-xs text-[#607783]">
        <p>
          Affichage de {firstEntry} à {lastEntry} sur{" "}
          {result.totalMatches.toLocaleString("fr-FR")} écriture
          {result.totalMatches > 1 ? "s" : ""}.
        </p>
        {result.signConvention === "debit_positive_credit_negative" && (
          <p>Montants signés : débit positif, crédit négatif.</p>
        )}
        {emptyColumns.length > 0 && (
          <p>
            Champs non renseignés sur cette page :{" "}
            {emptyColumns
              .map((column) => LEDGER_COLUMN_LABELS[column] ?? column)
              .join(", ")}
            .
          </p>
        )}
      </div>
    </section>
  );
}
