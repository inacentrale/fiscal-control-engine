type AgentModelMetaProps = {
  providerName: string;
  modelName: string;
};

export default function AgentModelMeta({
  providerName,
  modelName,
}: AgentModelMetaProps) {
  if (providerName === "internal" || modelName.startsWith("direct-")) {
    return null;
  }

  return (
    <p className="pt-1 text-right text-[11px] font-medium text-[#9aa8b0] opacity-0 transition group-hover/answer:opacity-100">
      {providerName} · {modelName}
    </p>
  );
}
