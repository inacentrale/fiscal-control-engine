import { describe, expect, it } from "vitest";

import { parseMarkdownBlocks } from "./AgentMarkdownAnswer";

describe("parseMarkdownBlocks", () => {
  it("keeps reconciliation markdown tables structured", () => {
    const blocks = parseMarkdownBlocks(`Rapprochement par devise

| Devise | Brut | Débit | Crédit | Solde | Utilisées | Exclues |
|---|---:|---:|---:|---:|---:|---:|
| XOF | 61 173 000.00 XOF | 61 173 000.00 XOF | 0.00 XOF | 61 173 000.00 XOF | 227 | 0 |

Détail par clé de comptabilisation

| Clé | Sens | Écritures | Utilisées | Montant brut |
|---|---|---:|---:|---:|
| 40 | debit | 227 | 227 | 61 173 000.00 |`);

    expect(blocks).toEqual([
      { type: "paragraph", content: "Rapprochement par devise" },
      {
        type: "table",
        headers: [
          "Devise",
          "Brut",
          "Débit",
          "Crédit",
          "Solde",
          "Utilisées",
          "Exclues",
        ],
        rows: [
          [
            "XOF",
            "61 173 000.00 XOF",
            "61 173 000.00 XOF",
            "0.00 XOF",
            "61 173 000.00 XOF",
            "227",
            "0",
          ],
        ],
      },
      {
        type: "paragraph",
        content: "Détail par clé de comptabilisation",
      },
      {
        type: "table",
        headers: ["Clé", "Sens", "Écritures", "Utilisées", "Montant brut"],
        rows: [["40", "debit", "227", "227", "61 173 000.00"]],
      },
    ]);
  });
});
