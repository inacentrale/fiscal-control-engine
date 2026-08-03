import { UseFormRegister } from "react-hook-form";
import Label from "../form/Label";

interface TextAreaFieldProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    label: string;
    name: string;
    register?: UseFormRegister<any>;
    errorMessage?: string | null;
    icon?: React.ReactNode;
    isRequired?: boolean;
    className?: string;
    placeholder?: string;
    rows?: number;
    maxLength?: number;
}

const TextAreaField = ({
    label,
    name,
    register,
    errorMessage,
    icon,
    isRequired = false,
    placeholder,
    ...rest
}: TextAreaFieldProps) => {
    return (
        <div>
            <Label
                title={label}
                htmlFor={name}
                icon={icon}
                required={isRequired}
                className="ml-0"
            />

            <textarea
                id={name}
                {...(register ? register(name) : {})}
                {...rest}
                placeholder={placeholder}
                className={`input !rounded-[13px] !text-[16px] !border-gray-300 ${errorMessage ? "input-error" : ""} `}
            />

            {errorMessage && (
                <p className="input-error-message">
                    {errorMessage}
                </p>
            )}
        </div>
    );
};

export default TextAreaField;