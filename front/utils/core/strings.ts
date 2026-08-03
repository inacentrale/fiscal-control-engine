export const normalizeText = (value: string): string =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

export const truncate = (str: string, max: number): string =>
  str.length > max ? str.slice(0, max) + "…" : str;

export const getInitials = (firstName: string, lastName: string): string => {
  return `${firstName?.charAt(0) || ""}${lastName?.charAt(0) || ""}`.toUpperCase();
};
