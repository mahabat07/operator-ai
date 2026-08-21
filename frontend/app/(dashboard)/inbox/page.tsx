"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type InboxItem = {
  id: string;
  raw_text: string;
  type: string | null;
  ai_suggestion: {
    type?: string;
    title?: string;
    priority?: string;
    deadline?: string | null;
    person?: string | null;
  } | null;
  status: string;
};

type GmailScanResult = {
  connected: boolean;
  scanned?: number;
  inbox_created?: number;
  risks_created?: string[];
  opportunities_created?: string[];
  detail?: string;
};

export default function InboxPage() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");

  async function load() {
    const data = await api.get<InboxItem[]>("/inbox");
    setItems(data);
  }

  useEffect(() => {
    load();
  }, []);

  async function capture(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;

    setSubmitting(true);

    try {
      await api.post("/inbox", { raw_text: text });
      setText("");
      await load();
    } finally {
      setSubmitting(false);
    }
  }

  async function syncGmail() {
    setSyncing(true);
    setSyncMessage("");

    try {
      const result = await api.post<GmailScanResult>("/integrations/gmail/scan");

      if (!result.connected) {
        setSyncMessage(
          "Google/Gmail не подключён. Сначала подключите Google в настройках."
        );
        return;
      }

      setSyncMessage(
        `Gmail проверен: ${result.scanned ?? 0} писем, новых в Inbox: ${
          result.inbox_created ?? 0
        }.`
      );

      await load();
    } catch (error) {
      console.error(error);
      setSyncMessage(
        "Не удалось синхронизировать Gmail. Проверь подключение Google."
      );
    } finally {
      setSyncing(false);
    }
  }

  async function confirm(id: string) {
    await api.post(`/inbox/${id}/confirm`);
    await load();
  }

  async function dismiss(id: string) {
    await api.post(`/inbox/${id}/dismiss`);
    await load();
  }

  const unprocessed = items.filter((i) => i.status === "unprocessed");
  const processed = items.filter((i) => i.status !== "unprocessed");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Universal Inbox</h1>

        <p className="text-gray-500 text-sm mb-4">
          Все важные входящие данные собираются здесь. Вы можете создать
          задачу самостоятельно или получить её из Gmail. AI определяет тип,
          приоритет и дедлайн, а вы подтверждаете создание задачи.
        </p>

        <div className="flex gap-2 mb-4">
          <button
            onClick={syncGmail}
            disabled={syncing}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {syncing ? "Проверяем Gmail..." : "Sync Gmail"}
          </button>

          <button
            onClick={load}
            className="border px-4 py-2 rounded-lg"
          >
            Refresh
          </button>
        </div>

        {syncMessage && (
          <div className="mb-4 rounded-lg border bg-gray-50 px-4 py-3 text-sm">
            {syncMessage}
          </div>
        )}

        <form onSubmit={capture} className="flex gap-2">
          <input
            className="flex-1 border rounded-lg px-3 py-2"
            placeholder="Например: Подготовить отчёт к пятнице"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <button
            disabled={submitting}
            className="bg-black text-white px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {submitting ? "Добавляем..." : "Create"}
          </button>
        </form>
      </div>

      <section>
        <h2 className="font-medium mb-2">
          Needs review ({unprocessed.length})
        </h2>

        <ul className="flex flex-col gap-3">
          {unprocessed.map((i) => (
            <li
              key={i.id}
              className="bg-white border rounded-xl p-4"
            >
              <p className="mb-2 whitespace-pre-line">{i.raw_text}</p>

              {i.ai_suggestion && (
                <div className="flex gap-2 text-xs text-gray-500 mb-3 flex-wrap">
                  {i.ai_suggestion.type && (
                    <span className="bg-gray-100 rounded-full px-2 py-0.5">
                      type: {i.ai_suggestion.type}
                    </span>
                  )}

                  {i.ai_suggestion.title && (
                    <span className="bg-gray-100 rounded-full px-2 py-0.5">
                      {i.ai_suggestion.title}
                    </span>
                  )}

                  {i.ai_suggestion.priority && (
                    <span className="bg-gray-100 rounded-full px-2 py-0.5">
                      priority: {i.ai_suggestion.priority}
                    </span>
                  )}

                  {i.ai_suggestion.deadline && (
                    <span className="bg-gray-100 rounded-full px-2 py-0.5">
                      due: {i.ai_suggestion.deadline}
                    </span>
                  )}

                  {i.ai_suggestion.person && (
                    <span className="bg-gray-100 rounded-full px-2 py-0.5">
                      person: {i.ai_suggestion.person}
                    </span>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => confirm(i.id)}
                  className="text-sm bg-black text-white px-3 py-1.5 rounded-lg"
                >
                  Confirm & create
                </button>

                <button
                  onClick={() => dismiss(i.id)}
                  className="text-sm border px-3 py-1.5 rounded-lg"
                >
                  Dismiss
                </button>
              </div>
            </li>
          ))}

          {unprocessed.length === 0 && (
            <p className="text-gray-400 text-sm">
              Nothing pending review.
            </p>
          )}
        </ul>
      </section>

      <section>
        <h2 className="font-medium mb-2">Processed</h2>

        <ul className="flex flex-col gap-2">
          {processed.map((i) => (
            <li
              key={i.id}
              className="text-sm text-gray-500 border-b py-2 flex justify-between gap-4"
            >
              <span className="whitespace-pre-line">
                {i.raw_text}
              </span>

              <span className="text-xs uppercase">
                {i.status}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
