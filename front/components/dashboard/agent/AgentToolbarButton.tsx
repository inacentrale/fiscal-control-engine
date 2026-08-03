import type { ReactNode } from "react";

import { cn } from "@/utils/ui/styles";

type AgentToolbarButtonProps = {
  label: string;
  children: ReactNode;
  variant?: "default" | "primary";
  onClick?: () => void;
  disabled?: boolean;
};

export default function AgentToolbarButton({
  label,
  children,
  variant = "default",
  onClick,
  disabled = false,
}: AgentToolbarButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex size-8 cursor-pointer items-center justify-center rounded-full transition disabled:cursor-default disabled:opacity-50",
        variant === "primary"
          ? "bg-[#edf4f7] text-[#31424c] shadow-[inset_0_1px_0_rgba(255,255,255,0.75),0_6px_14px_rgba(49,66,76,0.08)] hover:bg-[#e2edf2]"
          : "text-black/54 hover:bg-black/[0.04] hover:text-black"
      )}
    >
      {children}
    </button>
  );
}
