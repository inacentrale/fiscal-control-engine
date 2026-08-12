"use client";

import Link from "next/link";
import { useState } from "react";

import UserAvatar from "@/components/base/UserAvatar";
import {
  LogoutIcon,
  UserIcon,
} from "@/public/assets/icons/SideBarIcons";
import { ArrowDownIcon } from "@/public/assets/icons/icons";
import { cn } from "@/utils/ui/styles";

type AISidebarProfileProps = {
  readonly className?: string;
};

export default function AISidebarProfile({ className }: AISidebarProfileProps) {
  const [isOpen, setIsOpen] = useState(false);
  const name = "Nadia Kaboré";
  const role = "Responsable Financier";

  return (
    <div className={cn("relative", className)}>
      <button
        aria-label="Profil"
        className="flex !w-full cursor-pointer items-center justify-between gap-2.5 rounded-full border border-gray-200 bg-white py-2 pl-2 pr-3 shadow-soft transition-all"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <div className="flex min-w-0 items-center gap-3">
          <UserAvatar
            className="!m-0 h-[44px] w-[44px] !p-0"
            forceRound
            size="xl"
            user={{
              name,
              profilePicture: { url: "/assets/profile-assia.png" } as Media,
            }}
          />

          <div className="flex min-w-0 flex-col !items-start gap-0.5 whitespace-nowrap">
            <p className="max-w-[150px] truncate text-[14px] font-semibold leading-[1.15] text-[#102734]">
              {name}
            </p>
            <span className="max-w-[150px] truncate text-[13px] leading-[1.15] text-[#667781]">
              {role}
            </span>
          </div>
        </div>

        <div className="rounded-full p-1 transition-colors">
          <ArrowDownIcon
            className={cn(
              "h-[18px] w-[18px] text-[#102734] transition-transform",
              isOpen ? "rotate-180" : "rotate-0",
            )}
          />
        </div>
      </button>

      {isOpen ? (
        <div className="absolute bottom-[calc(100%+10px)] left-0 z-30 w-full overflow-hidden rounded-[18px] border border-gray-200 bg-white p-2 shadow-soft">
          <Link
            className="flex cursor-pointer items-center gap-2 rounded-[12px] px-3 py-2 text-sm text-gray-700 transition hover:bg-[#edf4f7] hover:text-black"
            href="/"
          >
            <UserIcon className="h-4 w-4" />
            Profil
          </Link>
          <button
            className="flex w-full cursor-pointer items-center gap-2 rounded-[12px] px-3 py-2 text-left text-sm text-gray-700 transition hover:bg-[#edf4f7] hover:text-black"
            onClick={() => setIsOpen(false)}
            type="button"
          >
            <LogoutIcon className="h-4 w-4" />
            Déconnexion
          </button>
        </div>
      ) : null}
    </div>
  );
}
