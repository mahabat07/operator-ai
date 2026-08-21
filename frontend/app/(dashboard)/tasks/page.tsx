"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PriorityBadge from "@/components/PriorityBadge";

type Task = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  priority_source: string;
  priority_score: number | null;
  priority_reason: string | null;
  deadline: string | null;
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setTasks(await api.get<Task[]>("/tasks"));
  }
  useEffect(() => { load(); }, []);

  // Note: no priority field in this form on purpose. The backend's
  // POST /tasks auto-scores priority via the AI prioritizer whenever it's
  // omitted - this is the fix for "the assistant doesn't understand what's
  // important, I should just create the task". Priority can still be
  // corrected afterwards with one click if the AI got it wrong.
  async function createTask(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await api.post("/tasks", { title, deadline: deadline || null });
      setTitle("");
      setDeadline("");
      await load();
    } finally {
      setSubmitting(false);
    }
  }

  async function setStatus(id: string, status: string) {
    await api.patch(`/tasks/${id}`, { status });
    await load();
  }

  async function overridePriority(id: string, priority: string) {
    await api.patch(`/tasks/${id}`, { priority });
    await load();
  }

  async function reprioritize(id: string) {
    await api.post(`/tasks/${id}/reprioritize`);
    await load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Tasks</h1>
        <form onSubmit={createTask} className="flex gap-2 flex-wrap">
          <input className="flex-1 min-w-[240px] border rounded-lg px-3 py-2" placeholder="What needs doing?" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="border rounded-lg px-3 py-2" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          <button disabled={submitting} className="bg-black text-white px-4 py-2 rounded-lg disabled:opacity-50">Add — AI will set priority</button>
        </form>
      </div>

      <ul className="flex flex-col gap-2">
        {tasks.map((t) => (
          <li key={t.id} className="bg-white border rounded-xl p-4 flex flex-col gap-2">
            <div className="flex justify-between items-start gap-3">
              <div>
                <p className={t.status === "done" ? "line-through text-gray-400" : ""}>{t.title}</p>
                {t.deadline && <p className="text-xs text-gray-400">due {t.deadline}</p>}
                {t.priority_reason && <p className="text-xs text-gray-400 mt-1">why: {t.priority_reason}</p>}
              </div>
              <div className="flex items-center gap-2">
                <PriorityBadge priority={t.priority} source={t.priority_source} reason={t.priority_reason} />
                <select
                  className="text-xs border rounded px-1 py-0.5"
                  value={t.priority}
                  onChange={(e) => overridePriority(t.id, e.target.value)}
                >
                  {["low", "medium", "high", "urgent"].map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-2 text-sm">
              {t.status !== "done" ? (
                <button onClick={() => setStatus(t.id, "done")} className="text-green-700 underline">Mark done</button>
              ) : (
                <button onClick={() => setStatus(t.id, "todo")} className="text-gray-500 underline">Reopen</button>
              )}
              <button onClick={() => reprioritize(t.id)} className="text-gray-500 underline">Re-run AI priority</button>
            </div>
          </li>
        ))}
        {tasks.length === 0 && <p className="text-gray-400 text-sm">No tasks yet.</p>}
      </ul>
    </div>
  );
}
