"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type HistoryMessage = {
  role: string;
  content: string;
};

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await api.get<HistoryMessage[]>("/assistant/history");

        setMessages(
          history
            .filter(
              (message) =>
                message.role === "user" || message.role === "assistant"
            )
            .map((message) => ({
              role: message.role as "user" | "assistant",
              content: message.content,
            }))
        );
      } catch (err) {
        console.error("Failed to load assistant history", err);
      }
    }

    loadHistory();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(e?: React.FormEvent) {
    e?.preventDefault();

    const text = input.trim();

    if (!text || loading) return;

    setError(null);
    setInput("");

    setMessages((current) => [
      ...current,
      { role: "user", content: text },
    ]);

    setLoading(true);

    try {
      const response = await api.post<{
        reply: string;
        actions_taken: unknown[];
      }>("/assistant/chat", {
        message: text,
      });

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.reply,
        },
      ]);
    } catch (err) {
      console.error(err);

      setError(
        "Не удалось получить ответ от Operator AI. Проверьте подключение к серверу."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">Assistant</h1>
          <p className="mt-1 text-sm text-gray-500">
            Ваш AI Chief of Staff. Попросите его создать задачу,
            запомнить обязательство или помочь с приоритетами.
          </p>
        </div>

        <div className="flex-1 rounded-xl border bg-white p-6 shadow-sm">
          {messages.length === 0 && !loading ? (
            <div className="flex min-h-[400px] items-center justify-center">
              <div className="max-w-md text-center">
                <h2 className="text-lg font-medium">
                  Чем я могу помочь?
                </h2>

                <p className="mt-2 text-sm text-gray-500">
                  Например:
                </p>

                <div className="mt-4 space-y-2 text-left text-sm">
                  <div className="rounded-lg bg-gray-50 p-3">
                    Создай задачу: подготовить презентацию к пятнице
                  </div>

                  <div className="rounded-lg bg-gray-50 p-3">
                    Что у меня сейчас самое важное?
                  </div>

                  <div className="rounded-lg bg-gray-50 p-3">
                    Напомни мне связаться с клиентом завтра
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={
                    message.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }
                >
                  <div
                    className={
                      message.role === "user"
                        ? "max-w-[80%] rounded-2xl bg-black px-4 py-3 text-sm text-white"
                        : "max-w-[80%] rounded-2xl border bg-gray-50 px-4 py-3 text-sm text-gray-900"
                    }
                  >
                    {message.content}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl border bg-gray-50 px-4 py-3 text-sm text-gray-500">
                    Operator AI думает...
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {error && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <form
          onSubmit={sendMessage}
          className="mt-4 flex gap-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Напишите Operator AI..."
            disabled={loading}
            className="flex-1 rounded-xl border bg-white px-4 py-3 text-sm outline-none focus:ring-2 disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl bg-black px-6 py-3 text-sm font-medium text-white disabled:opacity-50"
          >
            Отправить
          </button>
        </form>
      </div>
    </main>
  );
}
