"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, SVGProps } from "react";

import { HomeIcon } from "@/public/assets/icons/SideBarIcons";
import { ShieldCheckFilledIcon } from "@/public/assets/icons/icons";

type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Analyse du Grand Livre", icon: HomeIcon },
  { href: "/declarations", label: "Gestion des déclarations", icon: ShieldCheckFilledIcon },
];

export default function AppSidebar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Navigation principale"
      className="flex h-full w-[212px] shrink-0 flex-col gap-1 border-r border-[#edf3f6] bg-white px-3 py-4"
    >
      {NAV_ITEMS.map((item) => {
        const isActive =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={[
              "flex items-center gap-3 rounded-[12px] px-3.5 py-2.5 text-[14px] font-medium transition",
              isActive
                ? "bg-[#FCECEF] text-[#C20831]"
                : "text-[#40515c] hover:bg-[#FCECEF]/65 hover:text-[#9E0627]",
            ].join(" ")}
          >
            <Icon className="size-[18px] shrink-0" />
            <span className="leading-tight">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
