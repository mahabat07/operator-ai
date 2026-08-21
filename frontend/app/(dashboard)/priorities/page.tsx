"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PriorityBadge from "@/components/PriorityBadge";

type PriorityItem = {
  id: string; title: string; kind: string; priority?: string; priority_score?: number;
  score: number; deadline?: string | null; related_person?: string | null;
};

export default function PrioritiesPage() {
  const [items, setItems] = useState<PriorityItem[]>([]);

  useEffect(() => {
    api.get<{ top_priorities: PriorityItem[] }>("/priorities").then((d) => setItems(d.top_priorities));
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold mb-1">Priorities</h1>
        <p className="text-gray-500 text-sm">
          Ranked by the same AI priority score every task carries — urgency language, deadline proximity, and project business impact — not just a manual field.
        </p>
      </div>
      <ol className="flex flex-col gap-2">
        {items.map((item, idx) => (
          <li key={item.id} className="bg-white border rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-gray-300 font-mono text-sm w-5">{idx + 1}</span>
              <div>
                <p>{item.title}</p>
                <p className="text-xs text-gray-400 capitalize">{item.kind} {item.deadline ? `· due ${item.deadline}` : ""}</p>
              </div>
            </div>
            {item.priority && <PriorityBadge priority={item.priority} />}
          </li>
        ))}
        {items.length === 0 && <p className="text-gray-400 text-sm">Nothing to prioritize right now.</p>}
      </ol>
    </div>
  );
}
