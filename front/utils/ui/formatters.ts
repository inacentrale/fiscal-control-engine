export const formatPrice = (price: number): string => {
  return new Intl.NumberFormat("fr-FR", {
    style: "decimal",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
};

export const formatNumber = (num?: number): string => {
  if (!num) return "";
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, "") + "m";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, "") + "k";
  }
  return num.toString();
};

export const formatDate = (dateString: string | Date): string => {
  if (!dateString) return "Date non disponible";
  return new Date(dateString).toLocaleString("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const formatShortDate = (dateStr?: string | Date): string => {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("fr-FR");
};

export const formatTimeAgo = (dateString: string | Date): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return "À l'instant";
  if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `Il y a ${minutes} min`;
  }
  if (diffInSeconds < 84600) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `Il y a ${hours} h`;
  }
  if (diffInSeconds < 604800) {
    const days = Math.floor(diffInSeconds / 86400);
    return `Il y a ${days} j`;
  }
  if (diffInSeconds < 2592000) {
    const weeks = Math.floor(diffInSeconds / 604800);
    return `Il y a ${weeks} ${weeks > 1 ? "semaines" : "semaine"}`;
  }
  if (diffInSeconds < 31536000) {
    const months = Math.floor(diffInSeconds / 2592000);
    return `Il y a ${months} mois`;
  }
  const years = Math.floor(diffInSeconds / 31536000);
  return `Il y a ${years} an${years > 1 ? "s" : ""}`;
};

export const formatDeliveryAddress = (address?: { city?: string; district?: string } | null): string => {
  if (!address) return "Adresse non disponible";
  return `${address.city || ""}, ${address.district || ""}`.trim().replace(/^,/, "").trim() || "Adresse non disponible";
};

export const formatColorsForLabel = (colors: { hex: string; name: string }[]): string => {
  if (colors.length === 0) return "";
  const firstColor = colors[0];
  return (firstColor.name || firstColor.hex).toLowerCase();
};
