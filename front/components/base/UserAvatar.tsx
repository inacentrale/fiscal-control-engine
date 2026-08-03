import { cn } from "@/utils/ui/styles";
import Image from "next/image";
import { createAvatar } from "@dicebear/core";
import * as shapes from "@dicebear/shapes";

type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

const sizeConfig = {
  xs: { container: "w-6 h-6", text: "text-[10px]" },
  sm: { container: "w-8 h-8", text: "text-sm" },
  md: { container: "w-9 h-9", text: "text-base" },
  lg: { container: "w-12 h-12", text: "text-lg" },
  xl: { container: "w-[44px] h-[44px]", text: "text-lg" },
};

interface UserAvatarProps {
  user: {
    firstName?: string;
    lastName?: string;
    name?: string;
    email?: string;
    profilePicture?: Media | null;
    isCompany?: boolean;
  };
  className?: string;
  size?: AvatarSize;
  forceRound?: boolean;
}

const UserAvatar = ({ user, className, size = "md", forceRound = false }: UserAvatarProps) => {
  const { container, text } = sizeConfig[size];

  const baseClasses = cn("select-none shrink-0", container, className);

  const profilePictureUrl = user.profilePicture?.url || null;

  if (profilePictureUrl) {
    return (
      <Image
        className={cn(
          baseClasses,
          forceRound || !user.isCompany ? "rounded-full" : "rounded-[32%]",
          "object-cover object-center"
        )}
        src={profilePictureUrl}
        alt={user.firstName || user.name || "Utilisateur"}
        title={user.firstName || user.name || "Utilisateur"}
        loading="lazy"
        height={50}
        width={50}
        draggable={false}
      />
    );
  }

  const seed = user.name || user.firstName || user.email || "U";
  const initials = seed
    .split(" ")
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join("");

  // --- Company default logo: premium DiceBear Shapes (matching background + shapes) ---
  if (user.isCompany) {
    const seed = user.name || user.firstName || user.email || "U";
    
    // Generate deterministic geometric shapes with its own matched background
    const avatar = createAvatar(shapes, {
      seed: seed,
    });
    const svgHtml = avatar.toString();

    return (
      <div
        className={cn(
          baseClasses,
          forceRound ? "rounded-full" : "rounded-[32%]",
          "relative overflow-hidden flex items-center justify-center shadow-sm bg-white"
        )}
        title={seed}
      >
        {/* Render geometric SVG shapes with background included */}
        <div 
          className="absolute inset-0 z-10 flex items-center justify-center [&>svg]:w-full [&>svg]:h-full [&>svg]:object-contain"
          dangerouslySetInnerHTML={{ __html: svgHtml }}
        />
      </div>
    );
  }

  // --- User: classic colored circle ---
  return (
    <div
      className={cn(
        baseClasses,
        "rounded-full flex items-center justify-center",
        "text-white font-medium leading-none bg-primary",
        text
      )}
      title={seed}
    >
      <span
        className="translate-y-[1px] mobile:translate-y-[2px]"
        style={{ display: "inline-block", lineHeight: 1 }}
      >
        {initials.charAt(0)}
      </span>
    </div>
  );
};

export default UserAvatar;
