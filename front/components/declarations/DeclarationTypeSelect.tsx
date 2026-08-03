import {
  TAX_DECLARATION_TYPE_LABELS,
  type TaxDeclarationType,
} from "@/api/taxDeclarations/types";

const TYPE_OPTIONS = Object.entries(TAX_DECLARATION_TYPE_LABELS) as [
  TaxDeclarationType,
  string,
][];

export default function DeclarationTypeSelect({
  value,
  onChange,
}: {
  value: TaxDeclarationType;
  onChange: (value: TaxDeclarationType) => void;
}) {
  return (
    <div className="mb-3">
      <label
        htmlFor="declaration-type"
        className="mb-[1px] block text-[14px] font-medium text-[#102734]"
      >
        Type de déclaration
      </label>
      <select
        id="declaration-type"
        value={value}
        onChange={(event) => onChange(event.target.value as TaxDeclarationType)}
        className="h-11 w-full rounded-[12px] border border-[#e5edf1] bg-white px-3.5 text-[14px] font-medium text-[#102734] outline-none focus:border-[#3664ff]"
      >
        {TYPE_OPTIONS.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </div>
  );
}
