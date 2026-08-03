import { cn } from "@/utils/ui/styles";

const Label = ({ title, htmlFor, icon, required, className }: LabelProps) => {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        "flex items-center w-fit gap-1 mb-[1px] text-gray-800 line-clamp-1",
        className
      )}
    >
      <p className="text-primary">{icon}</p>

      <p className="text-[14px] text-dark/90 font-medium sm:text-[14px] first-letter:uppercase">
        {title}
        {required && (
          <span className="text-black/70 text-[13px] !font-normal !font-sans"> *</span>
        )}
      </p>
    </label>
  );
};

export default Label;
