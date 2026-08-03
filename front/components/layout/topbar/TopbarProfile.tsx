import Image from "next/image";

export default function TopbarProfile() {
  return (
    <div className="hidden items-center gap-3 sm:flex">
      <Image
        src="/assets/default-profile.jpeg"
        alt="Dwayne Tatum"
        width={56}
        height={56}
        priority
        className="size-[56px] shrink-0 rounded-full object-cover object-center"
      />

      <div className="flex h-[56px] w-[168px] min-w-0 flex-col gap-y-1 justify-center">
        <p className="truncate text-[17px] font-bold leading-[1.08] text-black">
          Dwayne Tatum
        </p>
        <p className="truncate text-[14px] font-medium leading-[1.25] text-black">
          CEO Assistant
        </p>
      </div>
    </div>
  );
}
