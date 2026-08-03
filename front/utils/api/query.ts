import { stripNullish } from "../core/objects";

export const cleanFilters = (filters: Record<string, any>): Record<string, any> => {
  return stripNullish(filters, {
    keepNull: () => false,
    keepEmptyObjects: () => false,
    removeEmptyStrings: true
  });
};
