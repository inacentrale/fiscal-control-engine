"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

import type { AgentConversationMessage } from "@/api/agent/types";

import AgentAssistantMessage from "./AgentAssistantMessage";
import AgentUserMessage from "./AgentUserMessage";

export default function AgentConversation({
  messages,
  scrollContainerRef,
}: {
  messages: AgentConversationMessage[];
  scrollContainerRef?: RefObject<HTMLElement | null>;
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const scrollKey = messages
    .map((message) =>
      message.role === "assistant"
        ? `${message.id}:${message.status}:${message.content?.length || 0}:${message.executionEvents.length}`
        : `${message.id}:${message.content.length}`
    )
    .join("|");

  useLayoutEffect(() => {
    const animationFrame = requestAnimationFrame(() => {
      if (scrollContainerRef?.current) {
        scrollContainerRef.current.scrollTop =
          scrollContainerRef.current.scrollHeight;
        return;
      }
      bottomRef.current?.scrollIntoView({ block: "end", behavior: "auto" });
    });

    return () => cancelAnimationFrame(animationFrame);
  }, [scrollContainerRef, scrollKey]);

  if (messages.length === 0) return null;

  return (
    <div className="space-y-5 pt-3">
      {messages.map((message) =>
        message.role === "user" ? (
          <AgentUserMessage key={message.id} message={message} />
        ) : (
          <AgentAssistantMessage key={message.id} message={message} />
        )
      )}
      <div ref={bottomRef} />
    </div>
  );
}
