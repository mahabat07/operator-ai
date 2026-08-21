"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Project = { id: string; name: string; description: string | null; status: string; business_impact: string | null };

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [impact, setImpact] = useState("medium");

  async function load() { setProjects(await api.get<Project[]>("/projects")); }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await api.post("/projects", { name, business_impact: impact });
    setName("");
    await load();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Projects</h1>
        <p className="text-gray-500 text-sm mb-4">Business impact here feeds directly into task prioritization for tasks under this project.</p>
        <form onSubmit={create} className="flex gap-2">
          <input className="flex-1 border rounded-lg px-3 py-2" placeholder="Project name" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="border rounded-lg px-3 py-2" value={impact} onChange={(e) => setImpact(e.target.value)}>
            {["low", "medium", "high", "critical"].map((i) => <option key={i} value={i}>{i} impact</option>)}
          </select>
          <button className="bg-black text-white px-4 py-2 rounded-lg">Create</button>
        </form>
      </div>
      <ul className="flex flex-col gap-2">
        {projects.map((p) => (
          <li key={p.id} className="bg-white border rounded-xl p-4 flex justify-between">
            <div><p>{p.name}</p><p className="text-xs text-gray-400">{p.status}</p></div>
            <span className="text-xs text-gray-500">{p.business_impact} impact</span>
          </li>
        ))}
        {projects.length === 0 && <p className="text-gray-400 text-sm">No projects yet.</p>}
      </ul>
    </div>
  );
}
