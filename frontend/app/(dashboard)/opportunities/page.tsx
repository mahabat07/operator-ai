"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Opportunity = {
  id: string;
  title?: string;
  description?: string | null;
  status?: string | null;
  source_reference?: string | null;
};

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadOpportunities() {
    try {
      setLoading(true);
      setError("");
      const data = await api.get<Opportunity[]>("/opportunities");
      setOpportunities(data);
    } catch (err) {
      console.error(err);
      setError("Не удалось загрузить возможности.");
    } finally {
      setLoading(false);
    }
  }

  async function dismissOpportunity(id: string) {
    try {
      await api.post(`/opportunities/${id}/dismiss`);
      await loadOpportunities();
    } catch (err) {
      console.error(err);
      setError("Не удалось закрыть возможность.");
    }
  }

  useEffect(() => {
    loadOpportunities();
  }, []);

  return (
    <main className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Возможности</h1>
        <p className="mt-1 text-sm text-gray-500">
          Возможности, обнаруженные Operator AI в рабочем пространстве.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <section className="rounded-xl border bg-white shadow-sm">
        <div className="border-b px-6 py-4">
          <h2 className="font-medium">Обнаруженные возможности</h2>
        </div>

        {loading ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Загрузка...
          </div>
        ) : opportunities.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Сейчас открытых возможностей нет.
          </div>
        ) : (
          <div className="divide-y">
            {opportunities.map((opportunity) => (
              <div key={opportunity.id} className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-medium">
                      {opportunity.title || "Возможность"}
                    </h3>

                    {opportunity.description && (
                      <p className="mt-2 text-sm text-gray-600">
                        {opportunity.description}
                      </p>
                    )}

                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {opportunity.status && (
                        <span className="rounded-full bg-gray-100 px-3 py-1 text-gray-600">
                          {opportunity.status}
                        </span>
                      )}

                      {opportunity.source_reference && (
                        <span className="rounded-full bg-gray-100 px-3 py-1 text-gray-600">
                          Источник: {opportunity.source_reference}
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => dismissOpportunity(opportunity.id)}
                    className="shrink-0 rounded-lg border px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Закрыть
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
