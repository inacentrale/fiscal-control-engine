import { PlusIcon } from "@/public/assets/icons/icons";

import TopbarBrand from "./TopbarBrand";
import TopbarIconButton from "./TopbarIconButton";
import TopbarSearch from "./TopbarSearch";

export default function Topbar() {
  return (
    <header className="w-full border-b border-[#edf1f3] bg-white px-6 py-2">
      <div className="grid h-[64px] grid-cols-1 items-center lg:grid-cols-[22%_50%_28%]">
        <div className="min-w-0">
          <TopbarBrand />
        </div>

        <div className="hidden min-w-0 justify-end pr-2 lg:flex">
          <TopbarIconButton label="Nouvelle action">
            <PlusIcon className="size-[19px]" />
          </TopbarIconButton>
        </div>

        <div className="hidden min-w-0 pl-2 lg:flex">
          <TopbarSearch />
        </div>
      </div>
    </header>
  );
}
