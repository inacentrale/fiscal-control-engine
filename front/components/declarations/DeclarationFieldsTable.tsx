import type {
  CanonicalDeclarationResponse,
  CanonicalFieldResponse,
} from "@/api/taxDeclarations/types";

export default function DeclarationFieldsTable({
  declaration,
}: {
  declaration: CanonicalDeclarationResponse;
}) {
  const records =
    declaration.records.length > 0
      ? declaration.records
      : declaration.fields.length > 0
        ? [{ record_type: "declaration", fields: declaration.fields }]
        : [];

  if (records.length === 0) {
    return (
      <p className="rounded-[14px] bg-[#f7fafb] px-4 py-3 text-[13px] font-medium text-[#60737e]">
        Aucune donnée exploitable n&apos;a été extraite de ce fichier.
      </p>
    );
  }

  const columnNames = Array.from(
    new Set(records.flatMap((record) => record.fields.map((field) => field.name)))
  );

  return (
    <div className="overflow-x-auto rounded-[14px] border border-[#edf3f6]">
      <table className="w-max min-w-full border-collapse text-left text-[12px] whitespace-nowrap">
        <thead className="bg-[#f2f6f8] text-[11px] font-semibold text-[#60737e]">
          <tr>
            {columnNames.map((name) => (
              <th key={name} className="px-3 py-2">
                {name.replaceAll("_", " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#edf3f6]">
          {records.map((record, index) => {
            const fieldsByName = new Map(
              record.fields.map((field) => [field.name, field])
            );
            return (
              <tr key={index}>
                {columnNames.map((name) => (
                  <td key={name} className="px-3 py-2 text-[#203743]">
                    {renderFieldValue(fieldsByName.get(name))}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function renderFieldValue(field: CanonicalFieldResponse | undefined): string {
  if (!field || field.normalized_value === null || field.normalized_value === undefined) {
    return "—";
  }
  return String(field.normalized_value);
}
