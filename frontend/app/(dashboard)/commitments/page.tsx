"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Commitment = { id: string; title: string; related_person: string | null; deadline: string | null; status: string };

export default function CommitmentsPage() {
  const [items, setItems] = useState<Commitment[]>([]);
  const [title, setTitle] = useState("");
  const [person, setPerson] = useState("");

  async function load() { setItems(await api.get<Commitment[]>("/commitments")); }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await api.post("/commitments", { title, related_person: person || null });
    setTitle(""); setPerson("");
    await load();
  }

  async function complete(id: string) {
    await api.post(`/commitments/${id}/complete`);
    await load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Commitments</h1>
        <p className="text-gray-500 text-sm mb-4">Things you promised someone else.</p>
        <form onSubmit={create} className="flex gap-2">
          <input className="flex-1 border rounded-lg px-3 py-2" placeholder="What did you promise?" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="border rounded-lg px-3 py-2" placeholder="To whom?" value={person} onChange={(e) => setPerson(e.target.value)} />
          <button className="bg-black text-white px-4 py-2 rounded-lg">Add</button>
        </form>
      </div>
      <ul className="flex flex-col gap-2">
        {items.map((c) => (
          <li key={c.id} className="bg-white border rounded-xl p-4 flex justify-between items-center">
            <div>
              <p className={c.status === "completed" ? "line-through text-gray-400" : ""}>{c.title}</p>
              <p className="text-xs text-gray-400">{c.related_person} {c.deadline ? `· due ${c.deadline}` : ""}</p>
            </div>
            {c.status !== "completed" && <button onClick={() => complete(c.id)} className="text-sm text-green-700 underline">Mark done</button>}
          </li>
        ))}
        {items.length === 0 && <p className="text-gray-400 text-sm">No open commitments.</p>}
      </ul>
    </div>
  );
}
