"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Meeting = {
  id: string;
  title: string;
  prep_brief: string | null;
  notes: string | null;
  extracted_follow_ups: string[] | null;
};

type PrepResponse = {
  id: string;
  title: string;
  prep_brief: string;
  talking_points: string[];
  source_citations: string[];
};

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);
  const [prep, setPrep] = useState<PrepResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [notesLoading, setNotesLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadMeetings() {
    try {
      const data = await api.get<Meeting[]>("/meetings");
      setMeetings(data);
    } catch (err) {
      console.error(err);
      setError("Не удалось загрузить встречи.");
    }
  }

  useEffect(() => {
    loadMeetings();
  }, []);

  async function prepareMeeting(e: React.FormEvent) {
    e.preventDefault();

    if (!title.trim() || loading) return;

    setLoading(true);
    setError("");
    setPrep(null);

    try {
      const result = await api.post<PrepResponse>("/meetings/prep", {
        title: title.trim(),
      });

      setPrep(result);
      setTitle("");
      await loadMeetings();
    } catch (err) {
      console.error(err);
      setError("Не удалось подготовить встречу.");
    } finally {
      setLoading(false);
    }
  }

  async function saveNotes() {
    if (!selectedMeeting || !notes.trim() || notesLoading) return;

    setNotesLoading(true);
    setError("");

    try {
      const result = await api.post<{
        id: string;
        extracted_follow_ups: string[];
      }>(`/meetings/${selectedMeeting.id}/notes`, {
        notes: notes.trim(),
      });

      setSelectedMeeting({
        ...selectedMeeting,
        notes: notes.trim(),
        extracted_follow_ups: result.extracted_follow_ups,
      });

      setNotes("");
      await loadMeetings();
    } catch (err) {
      console.error(err);
      setError("Не удалось сохранить заметки.");
    } finally {
      setNotesLoading(false);
    }
  }

  return (
    <main className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Meetings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Подготовка встреч, заметки и автоматическое извлечение follow-ups.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <section className="rounded-xl border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Подготовить встречу</h2>

        <form onSubmit={prepareMeeting} className="mt-4 flex gap-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Например: Встреча с клиентом Acme"
            className="flex-1 rounded-lg border px-4 py-3 text-sm outline-none focus:ring-2"
          />

          <button
            type="submit"
            disabled={loading || !title.trim()}
            className="rounded-lg bg-black px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
          >
            {loading ? "AI готовит..." : "Подготовить"}
          </button>
        </form>
      </section>

      {prep && (
        <section className="rounded-xl border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-medium">{prep.title}</h2>

          <div className="mt-5">
            <h3 className="text-sm font-semibold">Executive summary</h3>
            <p className="mt-2 text-sm text-gray-700">
              {prep.prep_brief}
            </p>
          </div>

          {prep.talking_points.length > 0 && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold">Talking points</h3>

              <ul className="mt-2 space-y-2 text-sm text-gray-700">
                {prep.talking_points.map((point, index) => (
                  <li key={index} className="rounded-lg bg-gray-50 p-3">
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {prep.source_citations.length > 0 && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold">Sources</h3>

              <div className="mt-2 flex flex-wrap gap-2">
                {prep.source_citations.map((source) => (
                  <span
                    key={source}
                    className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600"
                  >
                    {source}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      <section className="rounded-xl border bg-white shadow-sm">
        <div className="border-b px-6 py-4">
          <h2 className="font-medium">История встреч</h2>
        </div>

        {meetings.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Пока нет встреч.
          </div>
        ) : (
          <div className="divide-y">
            {meetings.map((meeting) => (
              <button
                key={meeting.id}
                onClick={() => {
                  setSelectedMeeting(meeting);
                  setNotes(meeting.notes || "");
                  setPrep(null);
                }}
                className="block w-full px-6 py-4 text-left hover:bg-gray-50"
              >
                <div className="font-medium">{meeting.title}</div>

                {meeting.prep_brief && (
                  <p className="mt-1 line-clamp-2 text-sm text-gray-500">
                    {meeting.prep_brief}
                  </p>
                )}

                {meeting.extracted_follow_ups &&
                  meeting.extracted_follow_ups.length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      {meeting.extracted_follow_ups.length} follow-up(s)
                    </div>
                  )}
              </button>
            ))}
          </div>
        )}
      </section>

      {selectedMeeting && (
        <section className="rounded-xl border bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">
              {selectedMeeting.title}
            </h2>

            <button
              onClick={() => setSelectedMeeting(null)}
              className="text-sm text-gray-400 hover:text-gray-700"
            >
              Закрыть
            </button>
          </div>

          <div className="mt-5">
            <label className="text-sm font-medium">
              Заметки встречи
            </label>

            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Введите заметки после встречи..."
              rows={7}
              className="mt-2 w-full rounded-lg border px-4 py-3 text-sm outline-none focus:ring-2"
            />

            <button
              onClick={saveNotes}
              disabled={notesLoading || !notes.trim()}
              className="mt-3 rounded-lg bg-black px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
            >
              {notesLoading ? "AI анализирует..." : "Сохранить и извлечь follow-ups"}
            </button>
          </div>

          {selectedMeeting.extracted_follow_ups &&
            selectedMeeting.extracted_follow_ups.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold">
                  AI Follow-ups
                </h3>

                <ul className="mt-3 space-y-2">
                  {selectedMeeting.extracted_follow_ups.map(
                    (followUp, index) => (
                      <li
                        key={index}
                        className="rounded-lg bg-gray-50 p-3 text-sm"
                      >
                        {followUp}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}
        </section>
      )}
    </main>
  );
}
