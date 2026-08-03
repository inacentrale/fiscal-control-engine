import { cn } from "@/utils/ui/styles";
import React from "react";
import { RiLoader2Line } from "react-icons/ri";

const ButtonLoading = ({ size = 24, className }: { size?: number, className?: string; }) => {
  return <RiLoader2Line className={cn("animate-spin", className)} size={size} />;
};

export default ButtonLoading;
