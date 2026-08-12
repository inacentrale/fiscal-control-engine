import Image from "next/image";

import { MenuIcon } from "@/public/assets/icons/SideBarIcons";

import TopbarIconButton from "./TopbarIconButton";

export default function TopbarBrand() {
  return (
    <div className="flex min-w-0 items-center gap-7">
      <TopbarIconButton label="Ouvrir le menu">
        <MenuIcon className="size-[25px]" />
      </TopbarIconButton>

      <div className="flex min-w-0 items-center gap-3">
        <Image
          alt="Royal Air Maroc"
          className="h-[48px] w-[65px] shrink-0 rounded-[10px] object-contain"
          height="59"
          src="https://www.royalairmaroc.com/o/ram-airways-theme/2025/assets/images/logo_ram.svg"
          unoptimized
          width="80"
        />

        <div className="flex h-[58px] mt-1 min-w-0 flex-col justify-center">
          <p className="truncate text-[20px] font-bold leading-[1.02] text-black">
            Analyse
          </p>
          <p className="truncate text-[20px] leading-[1.02] text-[#8f8f8f]">
            Grand Livre
          </p>
        </div>
      </div>
    </div>
  );
}
