import type { AgentRunEvent } from "@/api/agent/types";
import {
  ChevronRightIcon,
  ClockIcon,
  TickCircleIcon,
} from "@/public/assets/icons/AgentInputIcons";

type AgentExecutionTraceProps = {
  events: AgentRunEvent[];
  hasFile: boolean;
  isLoading: boolean;
};

type AgentTraceItem = {
  key: string;
  message: string;
  status: string;
};

export default function AgentExecutionTrace({
  events,
  hasFile,
  isLoading,
}: AgentExecutionTraceProps) {
  const visibleEvents = normalizeTraceEvents(
    events.length > 0 ? events : getFallbackThinkingEvents(hasFile)
  );

  if (isLoading) {
    return <AgentExecutionEventList events={visibleEvents} isLoading />;
  }

  return (
    <details className="group w-fit text-[12px] font-medium leading-6 text-[#667781]">
      <summary className="flex cursor-pointer list-none items-center gap-2">
        <span>{getSummaryLabel(visibleEvents)}</span>
        <ChevronRightIcon className="size-3 text-[#9aa8b0] transition group-open:rotate-90" />
      </summary>
      <div className="mt-2">
        <AgentExecutionEventList events={visibleEvents} />
      </div>
    </details>
  );
}

function AgentExecutionEventList({
  events,
  isLoading = false,
}: {
  events: AgentTraceItem[];
  isLoading?: boolean;
}) {
  const currentEvent = getCurrentEvent(events);
  const { hiddenEvents, visibleEvents } = compactTraceEvents(events);

  return (
    <div className="space-y-1.5">
      {hiddenEvents.length > 0 && (
        <details className="group w-fit text-[11px] font-medium leading-5 text-[#9aa8b0]">
          <summary className="flex cursor-pointer list-none items-center gap-1.5">
            <span>{hiddenEvents.length} étape(s) précédente(s)</span>
            <ChevronRightIcon className="size-3 text-[#a8b4bb] transition group-open:rotate-90" />
          </summary>
          <div className="mt-1.5">
            <TraceList events={hiddenEvents} currentEvent={currentEvent} />
          </div>
        </details>
      )}
      <TraceList
        events={visibleEvents}
        currentEvent={currentEvent}
        isLoading={isLoading}
      />
    </div>
  );
}

function TraceList({
  events,
  currentEvent,
  isLoading = false,
}: {
  events: AgentTraceItem[];
  currentEvent?: AgentTraceItem;
  isLoading?: boolean;
}) {
  if (events.length === 0) return null;

  return (
    <ol className="relative ml-2 space-y-1.5 pl-7 before:absolute before:left-0 before:top-1 before:h-[calc(100%-8px)] before:w-px before:bg-[#d9e5eb]">
      {events.map((event, index) => {
        const isCurrent = isLoading && event === currentEvent;

        return (
          <li
            key={`${event.key}-${index}`}
            className="relative"
            title={event.message}
          >
            <span
              className={`absolute -left-[35px] top-1.5 flex size-4 items-center justify-center rounded-full bg-white ${getEventIconClassName(
                event.status,
                isCurrent,
                isLoading
              )}`}
            >
              <EventStatusIcon
                status={event.status}
                isCurrent={isCurrent}
                isLoading={isLoading}
              />
            </span>
            <span
              className={`block ${
                isCurrent ? "agent-thinking-light text-[#40515c]" : "text-[#8a98a2]"
              }`}
            >
              {event.message}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function EventStatusIcon({
  status,
  isCurrent,
  isLoading,
}: {
  status: string;
  isCurrent: boolean;
  isLoading: boolean;
}) {
  if (status === "error") {
    return <span className="text-[11px] leading-none">!</span>;
  }
  if (isLoading && isCurrent) {
    return <ClockIcon className="size-4" />;
  }
  return <TickCircleIcon className="size-4" />;
}

function getFallbackThinkingEvents(hasFile: boolean): AgentRunEvent[] {
  const messages = hasFile
    ? [
        "Demande prise en compte.",
        "Fichier prêt pour l'analyse.",
        "Préparation de la réponse.",
      ]
    : ["Demande prise en compte.", "Préparation de la réponse."];

  return messages.map((message, index) => ({
    event_type: `fallback_${index}`,
    title: message,
    message,
    status: index === messages.length - 1 ? "running" : "completed",
    tool_name: null,
    provider_name: null,
    model_name: null,
  }));
}

function normalizeTraceEvents(events: AgentRunEvent[]): AgentTraceItem[] {
  const items: AgentTraceItem[] = [];
  let hasConnectionEvent = false;

  events.forEach((event) => {
    if (event.event_type === "answer_delta" || event.event_type === "answer_ready") {
      return;
    }

    if (event.event_type === "fallback_used") {
      if (hasConnectionEvent) return;
      hasConnectionEvent = true;
    }

    const item = toTraceItem(event);
    if (!item) return;

    if (event.tool_name && isToolProgressEvent(event.event_type)) {
      upsertTraceItem(items, item);
      return;
    }

    items.push(item);
  });

  return items;
}

function toTraceItem(event: AgentRunEvent): AgentTraceItem | null {
  if (event.event_type === "tool_requested") return null;

  return {
    key: event.tool_name || event.event_type,
    message: normalizeTraceMessage(event.message),
    status: event.status,
  };
}

function normalizeTraceMessage(message: string) {
  return message
    .replace(
      "L'analyse de la feuille Excel est terminée:",
      "Analyse de la feuille Excel terminée:"
    )
    .replace(
      "L'analyse du Grand Livre est terminée:",
      "Analyse du Grand Livre terminée:"
    );
}

function isToolProgressEvent(eventType: string) {
  return eventType === "tool_started" || eventType === "tool_finished";
}

function upsertTraceItem(items: AgentTraceItem[], item: AgentTraceItem) {
  const existingIndex = items.findIndex(
    (candidate) => candidate.key === item.key
  );
  if (existingIndex === -1) {
    items.push(item);
    return;
  }
  items[existingIndex] = item;
}

function getCurrentEvent(events: AgentTraceItem[]) {
  return events.at(-1);
}

function compactTraceEvents(events: AgentTraceItem[]) {
  if (events.length <= 3) {
    return {
      hiddenEvents: [],
      visibleEvents: events,
    };
  }

  return {
    hiddenEvents: events.slice(0, -3),
    visibleEvents: events.slice(-3),
  };
}

function getSummaryLabel(events: AgentTraceItem[]) {
  const hasError = events.some((event) => event.status === "error");
  if (hasError) return "Analyse arrêtée.";
  return "Réponse prête.";
}

function getEventIconClassName(
  status: string,
  isCurrent: boolean,
  isLoading: boolean
) {
  if (status === "error") return "text-red-500";
  if (isLoading && isCurrent) return "text-[#40515c]";
  return "text-[#6f7f88]";
}
