class LocalStorageService {
  private static isLocalStorageAvailable(): boolean {
    if (typeof window === "undefined") return false;

    try {
      return !!window.localStorage;
    } catch {
      return false;
    }
  }

  static setItemWithExpiration(
    key: string,
    value: any,
    expirationInMinutes?: number
  ): void {
    if (!this.isLocalStorageAvailable()) return;

    const data: any = {
      value,
    };

    if (expirationInMinutes) {
      data.expiry = Date.now() + expirationInMinutes * 60 * 1000;
    }

    localStorage.setItem(key, JSON.stringify(data));
  }

  static getItemWithExpiration(key: string): any {
    if (!this.isLocalStorageAvailable()) return null;

    const data = localStorage.getItem(key);
    if (!data) return null;

    try {
      const { value, expiry } = JSON.parse(data);

      if (expiry && Date.now() > expiry) {
        localStorage.removeItem(key);
        return null;
      }

      return value;
    } catch {
      localStorage.removeItem(key);
      return null;
    }
  }

  static removeItem(key: string): void {
    if (this.isLocalStorageAvailable()) {
      localStorage.removeItem(key);
    }
  }
}

export default LocalStorageService;
