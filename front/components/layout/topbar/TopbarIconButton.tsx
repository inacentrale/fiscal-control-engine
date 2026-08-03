import type { ReactNode } from "react";

import { cn } from "@/utils/ui/styles";

type TopbarIconButtonProps = {
  label: string;
  children: ReactNode;
  className?: string;
};

export default function TopbarIconButton({
  label,
  children,
  className,
}: TopbarIconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      className={cn(
        "flex size-[54px] shrink-0 cursor-pointer items-center justify-center rounded-full bg-white text-[#102734] shadow-[0_14px_30px_rgba(49,66,76,0.055)] ring-1 ring-[#e5edf1] transition hover:bg-[#f7f9fa]",
        className
      )}
    >
      {children}
    </button>
  );
}
