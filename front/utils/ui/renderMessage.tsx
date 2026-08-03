import React from "react";

export const renderMessageContent = (msg: any): React.ReactNode => {
  // On veut tout rendre dans un seul <span> plat, sans structure ni couleur
  const flatten = (m: any): string => {
    if (m === null || m === undefined) return "";
    if (typeof m === "string" || typeof m === "number") return String(m);
    if (Array.isArray(m)) return m.map(flatten).filter(Boolean).join(" | ");
    if (typeof m === "object") {
      if ((m as any).message || (m as any).msg)
        return flatten((m as any).message || (m as any).msg);
      return Object.entries(m)
        .map(([k, v]) => `${k}: ${flatten(v)}`)
        .filter(Boolean)
        .join("; ");
    }
    try {
      return String(m);
    } catch {
      return "";
    }
  };
  const text = flatten(msg);
  return <span>{text}</span>;
};

// New: stringify message into a single-line plain text
export const stringifyMessageContent = (msg: any): string => {
  if (msg === null || msg === undefined) return "";
  if (typeof msg === "string" || typeof msg === "number") return String(msg);

  if (Array.isArray(msg)) {
    return msg
      .map((m) => stringifyMessageContent(m))
      .filter(Boolean)
      .join(" | ");
  }

  if (typeof msg === "object") {
    // prefer message or msg properties
    if ((msg as any).message || (msg as any).msg)
      return stringifyMessageContent((msg as any).message || (msg as any).msg);

    return Object.entries(msg)
      .map(([k, v]) => `${k}: ${stringifyMessageContent(v)}`)
      .filter(Boolean)
      .join("; ");
  }

  try {
    return String(msg);
  } catch {
    return "";
  }
};

export default renderMessageContent;
