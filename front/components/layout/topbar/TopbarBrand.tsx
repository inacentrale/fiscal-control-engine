import { MenuIcon } from "@/public/assets/icons/SideBarIcons";

import TopbarIconButton from "./TopbarIconButton";

export default function TopbarBrand() {
  return (
    <div className="flex min-w-0 items-center gap-7">
      <TopbarIconButton label="Ouvrir le menu">
        <MenuIcon className="size-[25px]" />
      </TopbarIconButton>

      <div className="flex min-w-0 items-center gap-3">
        <div className="flex size-[54px] shrink-0 items-center justify-center rounded-full bg-black text-[21px] font-bold leading-none text-white">
          <span className="translate-y-[2px] translate-x-[2px]">N°</span>
        </div>

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
