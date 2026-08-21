"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type KnowledgeItem = { id: string; title: string; source_type: string; chunk_index: number };

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  async function load() { setItems(await api.get<KnowledgeItem[]>("/knowledge")); }
  useEffect(() => { load(); }, []);

  async function index(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    await api.post("/knowledge", { title, content, source_type: "document" });
    setTitle(""); setContent("");
    await load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Knowledge</h1>
        <p className="text-gray-500 text-sm mb-4">Paste a document or notes to index it — meeting prep and the assistant can then cite it.</p>
        <form onSubmit={index} className="flex flex-col gap-2">
          <input className="border rounded-lg px-3 py-2" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <textarea className="border rounded-lg px-3 py-2 h-32" placeholder="Paste content..." value={content} onChange={(e) => setContent(e.target.value)} />
          <button className="bg-black text-white px-4 py-2 rounded-lg self-start">Index</button>
        </form>
      </div>
      <ul className="flex flex-col gap-2">
        {items.map((k) => (
          <li key={k.id} className="bg-white border rounded-xl p-4 flex justify-between">
            <span>{k.title}</span>
            <span className="text-xs text-gray-400">{k.source_type} · chunk {k.chunk_index}</span>
          </li>
        ))}
        {items.length === 0 && <p className="text-gray-400 text-sm">Nothing indexed yet.</p>}
      </ul>
    </div>
  );
}
