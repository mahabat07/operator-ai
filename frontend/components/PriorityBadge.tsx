const COLORS: Record<string, string> = {
  urgent: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-blue-100 text-blue-700",
  low: "bg-gray-100 text-gray-600",
};

export default function PriorityBadge({ priority, source, reason }: { priority: string; source?: string; reason?: string | null }) {
  return (
    <span
      title={reason || undefined}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${COLORS[priority] || COLORS.medium}`}
    >
      {priority}
      {source === "ai" && <span className="text-[10px] opacity-70">✨ AI</span>}
    </span>
  );
}
