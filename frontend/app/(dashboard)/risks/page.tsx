"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Risk = {
  id: string;
  title?: string;
  description?: string | null;
  severity?: string | null;
  status?: string | null;
  source_reference?: string | null;
};

export default function RisksPage() {
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadRisks() {
    try {
      setLoading(true);
      setError("");
      const data = await api.get<Risk[]>("/risks");
      setRisks(data);
    } catch (err) {
      console.error(err);
      setError("Не удалось загрузить риски.");
    } finally {
      setLoading(false);
    }
  }

  async function dismissRisk(id: string) {
    try {
      await api.post(`/risks/${id}/dismiss`);
      await loadRisks();
    } catch (err) {
      console.error(err);
      setError("Не удалось закрыть риск.");
    }
  }

  useEffect(() => {
    loadRisks();
  }, []);

  return (
    <main className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Риски</h1>
        <p className="mt-1 text-sm text-gray-500">
          Риски, обнаруженные Operator AI в рабочем пространстве.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <section className="rounded-xl border bg-white shadow-sm">
        <div className="border-b px-6 py-4">
          <h2 className="font-medium">Обнаруженные риски</h2>
        </div>

        {loading ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Загрузка...
          </div>
        ) : risks.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Сейчас открытых рисков нет.
          </div>
        ) : (
          <div className="divide-y">
            {risks.map((risk) => (
              <div key={risk.id} className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-medium">
                      {risk.title || "Риск"}
                    </h3>

                    {risk.description && (
                      <p className="mt-2 text-sm text-gray-600">
                        {risk.description}
                      </p>
                    )}

                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {risk.severity && (
                        <span className="rounded-full bg-red-50 px-3 py-1 text-red-700">
                          Severity: {risk.severity}
                        </span>
                      )}

                      {risk.status && (
                        <span className="rounded-full bg-gray-100 px-3 py-1 text-gray-600">
                          {risk.status}
                        </span>
                      )}

                      {risk.source_reference && (
                        <span className="rounded-full bg-gray-100 px-3 py-1 text-gray-600">
                          Источник: {risk.source_reference}
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => dismissRisk(risk.id)}
                    className="shrink-0 rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Закрыть риск
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
