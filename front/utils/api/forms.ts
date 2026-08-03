export const getFieldError = (
  fieldName: string | undefined,
  errors: Record<string, any>,
  serverErrors?: Record<string, any>
): string | null => {
  if (!fieldName) return null;

  if (fieldName.includes(".")) {
    const parts = fieldName.split(".");

    let currentClientErrors = errors;
    let clientError = null;

    for (let i = 0; i < parts.length && currentClientErrors; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        clientError = currentClientErrors?.[part]?.message || null;
        break;
      }
      currentClientErrors = currentClientErrors?.[part];
    }

    let currentServerErrors = serverErrors;
    let serverError = null;

    for (let i = 0; i < parts.length && currentServerErrors; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        serverError = Array.isArray(currentServerErrors?.[part])
          ? currentServerErrors[part][0]
          : currentServerErrors?.[part];
        break;
      }
      currentServerErrors = currentServerErrors?.[part];
    }

    return clientError || serverError || null;
  }

  const serverError = Array.isArray(serverErrors?.[fieldName])
    ? serverErrors[fieldName][0]
    : serverErrors?.[fieldName];

  const clientError = errors[fieldName]?.message;

  return clientError || serverError || null;
};

export const objectToFormData = (
  data: any,
  options: {
    arrayNotation?: boolean;
    jsonStringifyObjects?: boolean;
  } = {
    arrayNotation: false,
    jsonStringifyObjects: false,
  },
  formData = new FormData(),
  parentKey = ""
): FormData => {
  const { jsonStringifyObjects } = options;

  if (data === null || data === undefined) {
    return formData;
  }

  if (data instanceof File || (typeof Blob !== 'undefined' && data instanceof Blob)) {
    formData.append(parentKey, data);
  } else if (Array.isArray(data)) {
    data.forEach((item, index) => {
      const key = parentKey ? `${parentKey}[${index}]` : `${index}`;

      if (typeof item === "object" && item !== null && item.file instanceof File) {
        formData.append(parentKey, item.file);
      } else if (
        typeof item === "object" &&
        item !== null &&
        !(item instanceof File) &&
        !(typeof Blob !== 'undefined' && item instanceof Blob)
      ) {
        objectToFormData(item, options, formData, key);
      } else {
        formData.append(parentKey, item);
      }
    });
  } else if (typeof data === "object" && !(data instanceof Date)) {
    if (jsonStringifyObjects) {
      formData.append(parentKey, JSON.stringify(data));
    } else {
      Object.keys(data).forEach((key) => {
        const value = data[key];
        if (value !== null && value !== undefined) {
          const formKey = parentKey ? `${parentKey}[${key}]` : key;
          objectToFormData(value, options, formData, formKey);
        }
      });
    }
  } else {
    formData.append(parentKey, data.toString());
  }

  return formData;
};

export const hasFiles = (data: any): boolean => {
  if (!data) return false;

  const checkRecursively = (obj: any): boolean => {
    if (!obj || typeof obj !== "object") return false;

    if (Array.isArray(obj)) {
      return obj.some((item) => {
        if (item instanceof File) return true;
        if (item && typeof item === "object" && item.file instanceof File) return true;
        return checkRecursively(item);
      });
    }

    for (const key in obj) {
      if (obj[key] instanceof File) return true;
      if (typeof FileList !== 'undefined' && obj[key] instanceof FileList) return true;
      if (obj[key] && typeof obj[key] === "object" && obj[key].file instanceof File) return true;
      if (
        Array.isArray(obj[key]) &&
        obj[key].some((item: any) => {
          return (
            item instanceof File || (item && typeof item === "object" && item.file instanceof File)
          );
        })
      ) {
        return true;
      }
      if (typeof obj[key] === "object" && obj[key] !== null) {
        if (checkRecursively(obj[key])) return true;
      }
    }

    return false;
  };

  return checkRecursively(data);
};
