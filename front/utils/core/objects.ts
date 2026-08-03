export const deepCompare = (obj1: any, obj2: any): boolean => {
  if (Object.is(obj1, obj2)) return false;

  if (
    typeof obj1 !== "object" ||
    typeof obj2 !== "object" ||
    obj1 === null ||
    obj2 === null
  ) {
    return obj1 !== obj2;
  }

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) return true;

  for (const key of keys1) {
    if (!keys2.includes(key)) return true;
    if (deepCompare(obj1[key], obj2[key])) return true;
  }

  return false;
};

export const getModifiedFields = ({ data, formData }: { data: any; formData: any }): Record<string, unknown> => {
  const modifiedFields: Record<string, unknown> = {};

  if (
    !data ||
    typeof data !== "object" ||
    !formData ||
    typeof formData !== "object"
  ) {
    return modifiedFields;
  }

  Object.keys(formData).forEach((key) => {
    const currentValue = data[key];
    const newDataValue = formData[key];

    if (deepCompare(currentValue, newDataValue)) {
      modifiedFields[key] = newDataValue;
    }
  });

  return modifiedFields;
};

export const stripNullish = <T extends Record<string, any>>(
  obj: T,
  options: {
    keepNull?: (key: string, value: any) => boolean;
    keepEmptyObjects?: (key: string, value: any) => boolean;
    removeEmptyStrings?: boolean;
  } = {}
): T => {
  if (obj === null || typeof obj !== "object") return obj;

  return Object.entries(obj).reduce((acc, [key, value]) => {
    if (value === undefined) {
      return acc;
    }
    if (value === null && !options.keepNull?.(key, value)) {
      return acc;
    }
    if (options.removeEmptyStrings && value === "") {
      return acc;
    }

    const cleaned = Array.isArray(value)
      ? (value as any[]).map((item) => (typeof item === 'object' && item !== null ? stripNullish(item, options) : item))
      : typeof value === 'object' && value !== null && !(value instanceof Date)
        ? stripNullish(value as any, options)
        : value;

    if (
      cleaned &&
      typeof cleaned === "object" &&
      !Array.isArray(cleaned) &&
      !(cleaned instanceof Date) &&
      Object.keys(cleaned).length === 0
    ) {
      if (!options.keepEmptyObjects?.(key, value)) {
        return acc;
      }
    }

    return { ...acc, [key]: cleaned } as T;
  }, {} as T);
};

export const convertStringToNumber = (data: any): any => {
  if (data === null || data === undefined) return data;
  if (data instanceof File || (typeof Blob !== 'undefined' && data instanceof Blob)) return data;

  if (Array.isArray(data)) {
    return data.map(item => convertStringToNumber(item));
  }

  if (typeof data === 'object' && !(data instanceof Date)) {
    const transformedData: Record<string, any> = {};

    for (const [key, value] of Object.entries(data)) {
      if (typeof value === 'string' && /^-?\d*\.?\d+$/.test(value)) {
        transformedData[key] = parseFloat(value);
      } else {
        transformedData[key] = convertStringToNumber(value);
      }
    }

    return transformedData;
  }

  return data;
};
