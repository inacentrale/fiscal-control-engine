export const openInboxLink = (email: string | null): string | undefined => {
  if (!email) return;

  const domain = email.split("@")[1]?.toLowerCase();
  if (!domain) return "https://mail.google.com/mail/u/0/#inbox";

  const links: Record<string, string> = {
    "gmail.com": "https://mail.google.com/mail/u/0/#inbox",
    "outlook.com": "https://outlook.live.com/mail/inbox",
    "yahoo.com": "https://mail.yahoo.com",
    "protonmail.com": "https://mail.protonmail.com/inbox",
    "icloud.com": "https://www.icloud.com/mail",
    "zoho.com": "https://mail.zoho.com",
    "gmx.com": "https://mail.gmx.com",
  };

  return links[domain] || "https://mail.google.com/mail/u/0/#inbox";
};

export const getUserLocaleData = () => {
  if (typeof navigator === "undefined") {
    return { preferredLanguage: "fr-FR", timezone: "UTC" };
  }

  const preferredLanguage = navigator.language;
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  return { preferredLanguage, timezone };
};

export const storage = {
  get: <T>(key: string): T | null => {
    if (typeof window === "undefined") return null;
    const item = localStorage.getItem(key);
    if (!item) return null;
    try {
      return JSON.parse(item) as T;
    } catch {
      return null;
    }
  },
  set: <T>(key: string, value: T): void => {
    if (typeof window === "undefined") return;
    localStorage.setItem(key, JSON.stringify(value));
  },
  remove: (key: string): void => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(key);
  },
};
