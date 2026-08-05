import { type ReactNode } from "react";

import CloserButton from "./CloserButton";

type ModalTitleProps = {
  readonly title: ReactNode;
  readonly icon?: ReactNode;
  readonly setActive?: (value: boolean) => void;
  readonly className?: string;
  readonly titleClass?: string;
  readonly count?: number;
  readonly description?: string;
};

const ModalTitle = ({
  title,
  icon,
  setActive,
  className = "",
  titleClass = "",
  count,
  description,
}: ModalTitleProps) => {
  return (
    <div className={`mb-8 flex items-center justify-between ${className}`}>
      <div className="flex items-center gap-3">
        {icon && (
          <div className="relative flex items-center justify-center rounded-full bg-primary/15 px-[10px] py-[8px]">
            {icon}
            {count && count > 0 && (
              <span className="absolute -right-1 top-0 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white bg-primary p-[7px] text-xs font-bold text-white">
                {count}
              </span>
            )}
          </div>
        )}

        <div className="flex flex-col gap-0">
          <h3
            className={`max-w-[260px] truncate whitespace-nowrap text-[20px] font-medium text-dark mobile:max-w-[420px] ${titleClass}`}
          >
            {title}
          </h3>

          {description && (
            <span className="text-sm text-gray-500">{description}</span>
          )}
        </div>
      </div>

      {setActive && <CloserButton setState={setActive} />}
    </div>
  );
};

export default ModalTitle;
