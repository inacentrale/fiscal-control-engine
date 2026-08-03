"use client";

import { useRef } from "react";

import AgentPromptCard from "@/components/dashboard/agent/AgentPromptCard";

export default function AgentColumn() {
  const scrollContainerRef = useRef<HTMLElement | null>(null);

  return (
    <section
      ref={scrollContainerRef}
      className="custom-scrollbar min-h-[560px] overflow-y-auto bg-white px-6 pb-1 pt-6 lg:min-h-0"
    >
      <div className="mx-auto flex min-h-full w-full justify-center">
        <AgentPromptCard scrollContainerRef={scrollContainerRef} />
      </div>
    </section>
  );
}
