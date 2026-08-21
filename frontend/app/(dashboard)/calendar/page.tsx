"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Event = { id: string; title: string; starts_at: string; ends_at: string; location: string | null };

export default function CalendarPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  async function load() { setEvents(await api.get<Event[]>("/calendar")); }
  useEffect(() => { load(); }, []);

  async function sync() {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await api.post<{ synced: number; detail?: string }>("/calendar/sync");
      setSyncMsg(res.detail || `Synced ${res.synced} event(s) from Google Calendar.`);
      await load();
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Calendar</h1>
        <button onClick={sync} disabled={syncing} className="text-sm border px-3 py-1.5 rounded-lg disabled:opacity-50">
          {syncing ? "Syncing..." : "Sync from Google"}
        </button>
      </div>
      {syncMsg && <p className="text-xs text-gray-500">{syncMsg}</p>}
      <ul className="flex flex-col gap-2">
        {events.map((e) => (
          <li key={e.id} className="bg-white border rounded-xl p-4">
            <p>{e.title}</p>
            <p className="text-xs text-gray-400">{new Date(e.starts_at).toLocaleString()} {e.location ? `· ${e.location}` : ""}</p>
          </li>
        ))}
        {events.length === 0 && <p className="text-gray-400 text-sm">No events yet — connect Google in Settings, then sync.</p>}
      </ul>
    </div>
  );
}
