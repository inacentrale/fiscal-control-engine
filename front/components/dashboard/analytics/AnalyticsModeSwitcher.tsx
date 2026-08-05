"use client";

import { motion } from "framer-motion";

export type AnalyticsMode = "ledger" | "withholding";

const modes: Array<{ id: AnalyticsMode; label: string }> = [
  { id: "ledger", label: "Grand Livre" },
  { id: "withholding", label: "RAS" },
];

export default function AnalyticsModeSwitcher({
  activeMode,
  onChange,
}: {
  activeMode: AnalyticsMode;
  onChange: (mode: AnalyticsMode) => void;
}) {
  return (
    <div className="grid w-full grid-cols-2 overflow-hidden rounded-[26px] bg-[#d9e3e8] p-[3px] shadow-[inset_0_1px_2px_rgba(255,255,255,0.82),0_14px_34px_rgba(64,81,92,0.08)]">
      {modes.map((mode) => {
        const isActive = activeMode === mode.id;

        return (
          <button
            aria-pressed={isActive}
            className={[
              "relative h-12 cursor-pointer rounded-[22px] px-4 text-[14px] font-semibold transition",
              isActive ? "text-[#102734]" : "text-[#5f717b] hover:text-[#203743]",
            ].join(" ")}
            key={mode.id}
            onClick={() => onChange(mode.id)}
            type="button"
          >
            {isActive && (
              <motion.span
                className="absolute inset-0 rounded-[22px] bg-white shadow-[0_8px_22px_rgba(64,81,92,0.14),inset_0_1px_0_rgba(255,255,255,0.95)]"
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
