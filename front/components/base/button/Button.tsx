import { cn } from "@/utils/ui/styles";
import React, { forwardRef } from "react";
import ButtonLoading from "./ButtonLoading";

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      icon,
      children,
      isLoading,
      isIconAfter,
      loadingContent,
      ...rest
    },
    ref
  ) => {
    return (
      <button
        type="button"
        ref={ref}
        className={cn(
          "btn-base flex items-center justify-center relative",
          className
        )}
        {...rest}
      >
        {isLoading && (loadingContent || <ButtonLoading />)}

        {!isIconAfter && icon && !isLoading && (
          <span className="transition opacity-100">{icon}</span>
        )}

        {children && !isLoading && (
          <span className="transition opacity-100">{children}</span>
        )}

        {isIconAfter && icon && !isLoading && (
          <span className="transition opacity-100">{icon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
