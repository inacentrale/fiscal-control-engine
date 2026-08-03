import { ROUTES } from "@/utils/constants/routes";
import { cn } from "@/utils/ui/styles";
import Link from "next/link";
import renderMessageContent from "@/utils/ui/renderMessage";

const GeneralError = ({
  serverErrors,
}: {
  serverErrors: Record<string, any>;
}) => {
  return (
    <div className="text-center text-sm -mt-2 mb-3">
      {serverErrors?.generalMessage && (
        <div
          className={cn(
            serverErrors.type == "error"
              ? "input-error-message"
              : "text-green-600",
            ""
          )}
        >
          {renderMessageContent(serverErrors.generalMessage)}
        </div>
      )}

      {serverErrors?.emailNotVerified && (
        <div>
          Reprendre en main en cliquant:{" "}
          <span className="text-primary text-sm font-medium">
            <Link
              href={ROUTES.FORGET_PASSWORD}
              className="w-fit underline underline-offset-2 decoration-primary font-medium"
            >
              Mot de passe <span className="">oublié</span>{" "}
            </Link>
          </span>
        </div>
      )}
    </div>
  );
};

export default GeneralError;
