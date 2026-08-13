"use client";

import { motion } from "framer-motion";

export type AnalyticsMode = "ledger" | "withholding";

const modes: Array<{ id: AnalyticsMode; label: string }> = [
  { id: "ledger", label: "Grand Livre" },
  { id: "withholding", label: "RAS" },
];

export default function AnalyticsModeSwitcher({
  activeMode,
  compact = false,
  onChange,
}: {
  activeMode: AnalyticsMode;
  compact?: boolean;
  onChange: (mode: AnalyticsMode) => void;
}) {
  return (
    <div
      className={[
        "grid w-full grid-cols-2 overflow-hidden bg-[#FCECEF] shadow-[inset_0_1px_2px_rgba(255,255,255,0.82),0_14px_34px_rgba(194,8,49,0.08)]",
        compact ? "rounded-[22px] p-0.5" : "rounded-[26px] p-[3px]",
      ].join(" ")}
    >
      {modes.map((mode) => {
        const isActive = activeMode === mode.id;

        return (
          <button
            aria-pressed={isActive}
            className={[
              "relative cursor-pointer font-semibold transition",
              compact
                ? "h-10 rounded-[19px] px-3 text-[13px]"
                : "h-12 rounded-[22px] px-4 text-[14px]",
              isActive ? "text-white" : "text-[#6B3E63] hover:text-[#9E0627]",
            ].join(" ")}
            key={mode.id}
            onClick={() => onChange(mode.id)}
            type="button"
          >
            {isActive && (
              <motion.span
                className={[
                  "absolute inset-0 bg-[#C20831] shadow-[0_8px_22px_rgba(194,8,49,0.22),inset_0_1px_0_rgba(255,255,255,0.22)]",
                  compact ? "rounded-[19px]" : "rounded-[22px]",
                ].join(" ")}
                layoutId="analytics-mode-switcher-active"
                transition={{
                  type: "spring",
                  stiffness: 300,
                  damping: 28,
                  mass: 0.9,
                }}
              />
            )}
            <span className="relative z-10">{mode.label}</span>
          </button>
        );
      })}
    </div>
  );
}
