import TopbarBrand from "./TopbarBrand";

export default function Topbar() {
  return (
    <header className="w-full bg-white px-6 py-2">
      <div className="flex h-[64px] items-center justify-between gap-8">
        <TopbarBrand />
      </div>
    </header>
  );
}
