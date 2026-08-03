import React from "react";
import Label from "./Label";
import { cn } from "@/utils/ui/styles";

const InputField = React.forwardRef<HTMLInputElement, InputFieldProps>(
  (
    { label, name, errorMessage, required, className, register, icon, ...rest },
    ref
  ) => {
    const registration = register ? register(name) : undefined;

    return (
      <div className="mb-3">
        {label && (
          <Label title={label} htmlFor={name} icon={icon} required={required} />
        )}

        <input
          id={name}
          {...rest}
          {...registration}
          name={registration?.name || name}
          ref={registration?.ref || ref}
          className={cn("input", errorMessage ? "input-error" : "", className)}
        />

        {Boolean(errorMessage) && (
          <p className="input-error-message">{errorMessage}</p>
        )}
      </div>
    );
  }
);

InputField.displayName = "InputField";

export default InputField;
