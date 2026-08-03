import { SearchZoomIcon } from "@/public/assets/icons/icons";

import TopbarIconButton from "./TopbarIconButton";

export default function TopbarSearch() {
  return (
    <div className="hidden items-center gap-3 md:flex">
      <TopbarIconButton label="Rechercher">
        <SearchZoomIcon className="size-[20px]" />
      </TopbarIconButton>

      <label className="block w-[250px] mt-1 cursor-text">
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
