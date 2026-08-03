type AgentMarkdownAnswerProps = {
  content: string;
  isError: boolean;
};

type MarkdownBlock =
  | {
      type: "heading" | "paragraph";
      content: string;
    }
  | {
      type: "list";
      items: string[];
    }
  | {
      type: "table";
      headers: string[];
      rows: string[][];
    };

export default function AgentMarkdownAnswer({
  content,
  isError,
}: AgentMarkdownAnswerProps) {
  return (
    <div
      className={`space-y-3 ${
        isError ? "font-medium text-red-700" : "text-[#203743]"
      }`}
    >
      {parseMarkdownBlocks(content).map((block, index) => {
        if (block.type === "heading") {
          return <p key={`${block.type}-${index}`}>{block.content}</p>;
        }

        if (block.type === "list") {
          return (
            <ul
              key={`${block.type}-${index}`}
              className="list-disc space-y-1 pl-5"
            >
              {block.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          );
        }

        if (block.type === "table") {
          return (
            <div
              className="overflow-x-auto rounded-xl border border-[#dfe8ec]"
              key={`${block.type}-${index}`}
            >
              <table className="min-w-full border-collapse text-left text-[12px]">
                <thead className="bg-[#f2f6f8] text-[#526873]">
                  <tr>
                    {block.headers.map((header, headerIndex) => (
                      <th
                        className="whitespace-nowrap px-3 py-2 font-semibold"
                        key={`${header}-${headerIndex}`}
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e8eff2] bg-white">
                  {block.rows.map((row, rowIndex) => (
                    <tr key={`row-${rowIndex}`}>
                      {row.map((cell, cellIndex) => (
                        <td
                          className="whitespace-nowrap px-3 py-2 text-[#203743]"
                          key={`${cell}-${cellIndex}`}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        return <p key={`${block.type}-${index}`}>{block.content}</p>;
      })}
    </div>
  );
}

export function parseMarkdownBlocks(content: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  let paragraphLines: string[] = [];
  let listItems: string[] = [];
  let tableRows: string[][] = [];
  const normalizedContent = normalizeInlineMarkdownLists(content);

  const flushParagraph = () => {
    if (paragraphLines.length === 0) return;
    blocks.push({
      type: "paragraph",
      content: paragraphLines.join(" "),
    });
    paragraphLines = [];
  };

  const flushList = () => {
    if (listItems.length === 0) return;
    blocks.push({
      type: "list",
      items: listItems,
    });
    listItems = [];
  };

  const flushTable = () => {
    if (tableRows.length === 0) return;
    const [headers, ...rows] = tableRows;
    blocks.push({ type: "table", headers, rows });
    tableRows = [];
  };

  normalizedContent.split("\n").forEach((line) => {
    const trimmedLine = line.trim();
    if (!trimmedLine) {
      flushParagraph();
      flushList();
      flushTable();
      return;
    }

    const tableCells = parseTableRow(trimmedLine);
    if (tableCells) {
      flushParagraph();
      flushList();
      if (!isTableSeparator(tableCells)) {
        tableRows.push(tableCells.map(cleanMarkdownText));
      }
      return;
    }

    flushTable();

    const headingMatch = trimmedLine.match(/^#{1,3}\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      if (isBoilerplateHeading(headingMatch[1])) {
        return;
      }
      blocks.push({
        type: "heading",
        content: cleanMarkdownText(headingMatch[1]),
      });
      return;
    }

    const listMatch = trimmedLine.match(/^[-*]\s+(.+)$/);
    if (listMatch) {
      flushParagraph();
      listItems.push(cleanMarkdownText(listMatch[1]));
      return;
    }

    flushList();
    paragraphLines.push(cleanMarkdownText(trimmedLine));
  });

  flushParagraph();
  flushList();
  flushTable();

  return blocks;
}

function parseTableRow(line: string): string[] | null {
  if (!line.startsWith("|") || !line.endsWith("|")) return null;
  const cells = line
    .slice(1, -1)
    .split("|")
    .map((cell) => cell.trim());
  return cells.length > 1 ? cells : null;
}

function isTableSeparator(cells: string[]): boolean {
  return cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function normalizeInlineMarkdownLists(content: string) {
  return content
    .trim()
    .replace(/\s+:\s+-\s+/g, ":\n- ")
    .replace(/\s+-\s+(?=[A-ZÀ-Ý0-9])/g, "\n- ");
}

function cleanMarkdownText(content: string) {
  return content.replace(/\*\*(.*?)\*\*/g, "$1").trim();
}

function isBoilerplateHeading(content: string) {
  return ["introduction"].includes(content.trim().toLowerCase());
}
