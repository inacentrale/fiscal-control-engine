import type { AnalyticsView } from "./analyticsViews";
import { analyticsViews } from "./analyticsViews";

export default function AnalyticsViewTabs({
  activeView,
  onChange,
}: {
  activeView: AnalyticsView;
  onChange: (view: AnalyticsView) => void;
}) {
  return (
    <div className="custom-scrollbar -mx-1 flex gap-1 overflow-x-auto px-1 pb-1">
      {analyticsViews.map((view) => (
        <button
          className={[
            "h-8 shrink-0 cursor-pointer rounded-full px-3 text-[12px] font-semibold transition",
            activeView === view.id
              ? "bg-[#C20831] text-white shadow-[0_10px_20px_rgba(194,8,49,0.20)]"
              : "bg-[#f5f8fa] text-[#60737e] hover:bg-[#FCECEF] hover:text-[#9E0627]",
          ].join(" ")}
          key={view.id}
          onClick={() => onChange(view.id)}
          type="button"
        >
          {view.label}
        </button>
      ))}
    </div>
  );
}
