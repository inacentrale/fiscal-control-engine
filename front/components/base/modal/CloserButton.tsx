import { CloseIcon } from "@/public/assets/icons/icons";
import { cn } from "@/utils/ui/styles";

const CloserButton = ({
  setState,
  className,
}: {
  setState: (value: boolean) => void;
  className?: string;
}) => {
  return (
    <button
      aria-label="Fermer"
      className={cn(
        "flex cursor-pointer items-center justify-center rounded-full bg-gray-100 p-[2px] transition-all duration-200 hover:bg-gray-200",
        className
      )}
      onClick={() => setState(false)}
      type="button"
    >
      <CloseIcon className="size-5" />
    </button>
  );
};

export default CloserButton;
