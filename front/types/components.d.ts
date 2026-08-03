import type { ReactElement, ReactNode } from "react";
import type { UseFormRegister } from "react-hook-form";

declare global {
  type Media = {
    url?: string;
    path?: string;
  };

  interface LabelProps {
    title: string;
    htmlFor: string;
    icon?: ReactNode;
    required?: boolean;
    className?: string;
  }

  interface InputFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label: string;
    name: string;
    errorMessage?: string | null;
    required?: boolean;
    className?: string;
    register?: UseFormRegister<any>;
    icon?: ReactNode;
  }

  type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
    className?: string;
    children?: ReactNode;
    icon?: ReactElement;
    isLoading?: boolean;
    isIconAfter?: boolean;
    loadingContent?: ReactNode;
  };
}

export {};
