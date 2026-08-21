"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type WaitingItem = { id: string; title: string; related_person: string | null; expected_by: string | null; status: string };

export default function WaitingForPage() {
  const [items, setItems] = useState<WaitingItem[]>([]);
  const [title, setTitle] = useState("");
  const [person, setPerson] = useState("");

  async function load() { setItems(await api.get<WaitingItem[]>("/waiting-for")); }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await api.post("/waiting-for", { title, related_person: person || null });
    setTitle(""); setPerson("");
    await load();
  }

  async function markReceived(id: string) {
    await api.post(`/waiting-for/${id}/received`);
    await load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Waiting For</h1>
        <p className="text-gray-500 text-sm mb-4">Things someone else owes you.</p>
        <form onSubmit={create} className="flex gap-2">
          <input className="flex-1 border rounded-lg px-3 py-2" placeholder="What are you waiting for?" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="border rounded-lg px-3 py-2" placeholder="From whom?" value={person} onChange={(e) => setPerson(e.target.value)} />
          <button className="bg-black text-white px-4 py-2 rounded-lg">Add</button>
        </form>
      </div>
      <ul className="flex flex-col gap-2">
        {items.map((w) => (
          <li key={w.id} className="bg-white border rounded-xl p-4 flex justify-between items-center">
            <div>
              <p className={w.status === "received" ? "line-through text-gray-400" : ""}>{w.title}</p>
              <p className="text-xs text-gray-400">{w.related_person} {w.expected_by ? `· expected ${w.expected_by}` : ""}</p>
            </div>
            {w.status !== "received" && <button onClick={() => markReceived(w.id)} className="text-sm text-green-700 underline">Mark received</button>}
          </li>
        ))}
        {items.length === 0 && <p className="text-gray-400 text-sm">Nothing pending.</p>}
      </ul>
    </div>
  );
}
