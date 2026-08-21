"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type WeeklyReview = {
  stats: {
    completed_this_week: number;
    overdue: number;
    open_commitments: number;
  };
  ai_summary: string | null;
  wins: string[];
  at_risk: string[];
};

export default function WeeklyReviewPage() {
  const [data, setData] = useState<WeeklyReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadReview() {
    try {
      setLoading(true);
      setError("");

      const result = await api.get<WeeklyReview>("/weekly-review");
      setData(result);
    } catch (err) {
      console.error(err);
      setError("Не удалось загрузить Weekly Review.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReview();
  }, []);

  if (loading) {
    return (
      <main>
        <h1 className="text-2xl font-semibold">Weekly Review</h1>
        <p className="mt-4 text-sm text-gray-500">AI анализирует вашу неделю...</p>
      </main>
    );
  }

  return (
    <main className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Weekly Review</h1>
        <p className="mt-1 text-sm text-gray-500">
          Итоги недели, достижения и то, что требует внимания.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {data && (
        <>
          <section className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border bg-white p-5 shadow-sm">
              <div className="text-2xl font-semibold">
                {data.stats.completed_this_week}
              </div>
              <div className="mt-1 text-sm text-gray-500">
                Выполнено за неделю
              </div>
            </div>

            <div className="rounded-xl border bg-white p-5 shadow-sm">
              <div className="text-2xl font-semibold">
                {data.stats.overdue}
              </div>
              <div className="mt-1 text-sm text-gray-500">
                Просрочено
              </div>
            </div>

            <div className="rounded-xl border bg-white p-5 shadow-sm">
              <div className="text-2xl font-semibold">
                {data.stats.open_commitments}
              </div>
              <div className="mt-1 text-sm text-gray-500">
                Открытые обязательства
              </div>
            </div>
          </section>

          <section className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium">AI Review</h2>

            <p className="mt-3 text-sm leading-6 text-gray-700">
              {data.ai_summary || "AI пока не сформировал итог недели."}
            </p>
          </section>

          <section className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-medium">Победы недели</h2>

              {data.wins.length === 0 ? (
                <p className="mt-4 text-sm text-gray-500">
                  Пока нет отмеченных достижений.
                </p>
              ) : (
                <ul className="mt-4 space-y-2">
                  {data.wins.map((win, index) => (
                    <li
                      key={index}
                      className="rounded-lg bg-gray-50 p-3 text-sm"
                    >
                      {win}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-medium">Требует внимания</h2>

              {data.at_risk.length === 0 ? (
                <p className="mt-4 text-sm text-gray-500">
                  Сейчас ничего критичного не обнаружено.
                </p>
              ) : (
                <ul className="mt-4 space-y-2">
                  {data.at_risk.map((item, index) => (
                    <li
                      key={index}
                      className="rounded-lg bg-gray-50 p-3 text-sm"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <button
            onClick={loadReview}
            className="rounded-lg bg-black px-5 py-3 text-sm font-medium text-white"
          >
            Обновить анализ
          </button>
        </>
      )}
    </main>
  );
}
