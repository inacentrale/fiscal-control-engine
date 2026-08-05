import { SearchZoomIcon } from "@/public/assets/icons/icons";

import TopbarIconButton from "./TopbarIconButton";

export default function TopbarSearch() {
  return (
    <div className="flex w-full min-w-0 items-center gap-3">
      <TopbarIconButton label="Rechercher">
        <SearchZoomIcon className="size-[20px]" />
      </TopbarIconButton>

      <label className="mt-1 block min-w-0 flex-1 cursor-text">
        <span className="sr-only">Recherche globale</span>
        <input
          type="search"
          placeholder="Start searching here ..."
          className="w-full cursor-text bg-transparent text-[17px] text-black outline-none placeholder:text-[#b8b8b8]"
        />
      </label>
    </div>
  );
}
