import { type ReactNode } from "react";

type PageTitleProps = {
  readonly eyebrow?: string;
  readonly title: string;
  readonly description?: string;
  readonly actions?: ReactNode;
};

export function PageTitle({
  eyebrow,
  title,
  description,
  actions,
}: PageTitleProps) {
  return (
    <header className="flex flex-col justify-between gap-4 border-b border-[#d9dee8] pb-5 md:flex-row md:items-end">
      <div>
        {eyebrow ? (
          <p className="text-sm font-semibold text-[#476173]">{eyebrow}</p>
        ) : null}
        <h1 className="mt-2 text-2xl font-semibold leading-tight text-[#172033] md:text-3xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#5f6f7d]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}
