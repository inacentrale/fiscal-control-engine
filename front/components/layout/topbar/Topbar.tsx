import { PlusIcon } from "@/public/assets/icons/icons";

import TopbarBrand from "./TopbarBrand";
import TopbarIconButton from "./TopbarIconButton";
import TopbarProfile from "./TopbarProfile";
import TopbarSearch from "./TopbarSearch";

export default function Topbar() {
  return (
    <header className="w-full border-b border-[#edf1f3] bg-white px-6 py-2">
      <div className="flex h-[64px] items-center justify-between gap-8">
        <TopbarBrand />

        <div className="flex min-w-0 items-center gap-8">
          <TopbarIconButton label="Nouvelle action">
            <PlusIcon className="size-[19px]" />
          </TopbarIconButton>
          <TopbarProfile />
          <TopbarSearch />
        </div>
      </div>
    </header>
  );
}
