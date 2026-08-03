"use client";

import { FormEvent, useState } from "react";
import { SearchZoomIcon } from "@/public/assets/icons/icons";
import { SendIcon } from "@/public/assets/icons/filterIcons";
import { cn } from "@/utils/ui/styles";

interface SearchInputProps {
  placeholder?: string;
  onSearch: (searchValue: string) => void;
  className?: string;
  buttonClassName?: string;
  autoFocus?: boolean;
}

const SearchInput = ({
  placeholder = "Rechercher...",
  onSearch,
  className = "",
  buttonClassName = "",
  autoFocus = false
}: SearchInputProps) => {
  const [query, setQuery] = useState("");

  const handleSearch = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();
    onSearch(trimmed);
  };

  return (
    <form onSubmit={handleSearch} className={cn("relative")}>
      <input
        type="search"
        name="search"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className={cn("input !pr-12", className)}
        autoFocus={autoFocus}
      />

      <button
        type="submit"
        className={cn(
          "absolute right-1 top-1/2 -translate-y-1/2 flex items-center justify-center gap-2 cursor-pointer h-9 w-9 rounded-full",
          query.trim().length > 0
            ? "bg-primary text-white"
            : "bg-primary/10 shadow-soft hover:bg-gray-50 text-gray-800",
          buttonClassName
        )}
      >
        {query.trim().length > 0 ? (
          <SendIcon className="w-5 h-5" />
        ) : (
          <SearchZoomIcon className="w-4 h-4" />
        )}
      </button>
    </form>
  );
};

export default SearchInput;
