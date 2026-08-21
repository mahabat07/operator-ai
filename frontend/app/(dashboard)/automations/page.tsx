"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Automation = {
  id: string;
  name: string;
  trigger: string;
  action: string;
  is_active: boolean;
  last_run_at: string | null;
  created_at: string;
};

export default function AutomationsPage() {
  const [items, setItems] = useState<Automation[]>([]);
  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState("");
  const [action, setAction] = useState("notify");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadAutomations() {
    try {
      setLoading(true);
      setError("");
      const data = await api.get<Automation[]>("/automations");
      setItems(data);
    } catch (err) {
      console.error(err);
      setError("Не удалось загрузить автоматизации.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAutomations();
  }, []);

  async function createAutomation(e: React.FormEvent) {
    e.preventDefault();

    if (!name.trim() || !trigger.trim() || creating) return;

    try {
      setCreating(true);
      setError("");
      setMessage("");

      await api.post("/automations", {
        name: name.trim(),
        trigger: trigger.trim(),
        action,
        config: null,
      });

      setName("");
      setTrigger("");
      setAction("notify");
      setMessage("Автоматизация создана.");
      await loadAutomations();
    } catch (err) {
      console.error(err);
      setError("Не удалось создать автоматизацию.");
    } finally {
      setCreating(false);
    }
  }

  async function deleteAutomation(id: string) {
    try {
      setError("");
      setMessage("");

      await api.del(`/automations/${id}`);

      setMessage("Автоматизация удалена.");
      await loadAutomations();
    } catch (err) {
      console.error(err);
      setError("Не удалось удалить автоматизацию.");
    }
  }

  async function runDueAutomations() {
    try {
      setRunning(true);
      setError("");
      setMessage("");

      const result = await api.post<{ notifications_created: number }>(
        "/automations/run-due"
      );

      setMessage(
        `Готово. Создано уведомлений: ${result.notifications_created}.`
      );

      await loadAutomations();
    } catch (err) {
      console.error(err);
      setError("Не удалось запустить автоматизации.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Automations</h1>
          <p className="mt-1 text-sm text-gray-500">
            Автоматические действия Operator AI по заданным триггерам.
          </p>
        </div>

        <button
          onClick={runDueAutomations}
          disabled={running}
          className="rounded-lg bg-black px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
        >
          {running ? "Запуск..." : "Запустить сейчас"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {message && (
        <div className="rounded-lg border bg-gray-50 px-4 py-3 text-sm text-gray-700">
          {message}
        </div>
      )}

      <section className="rounded-xl border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Создать автоматизацию</h2>

        <form onSubmit={createAutomation} className="mt-4 space-y-4">
          <div>
            <label className="text-sm font-medium">Название</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Напоминание о просроченной задаче"
              className="mt-2 w-full rounded-lg border px-4 py-3 text-sm outline-none focus:ring-2"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Триггер</label>
            <input
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
              placeholder="Например: task_overdue"
              className="mt-2 w-full rounded-lg border px-4 py-3 text-sm outline-none focus:ring-2"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Действие</label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="mt-2 w-full rounded-lg border px-4 py-3 text-sm"
            >
              <option value="notify">Уведомление</option>
              <option value="create_task">Создать задачу</option>
              <option value="email">Email</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={creating || !name.trim() || !trigger.trim()}
            className="rounded-lg bg-black px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
          >
            {creating ? "Создание..." : "Создать автоматизацию"}
          </button>
        </form>
      </section>

      <section className="rounded-xl border bg-white shadow-sm">
        <div className="border-b px-6 py-4">
          <h2 className="font-medium">Мои автоматизации</h2>
        </div>

        {loading ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Загрузка...
          </div>
        ) : items.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-500">
            Автоматизаций пока нет.
          </div>
        ) : (
          <div className="divide-y">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between gap-4 px-6 py-5"
              >
                <div>
                  <div className="font-medium">{item.name}</div>

                  <div className="mt-1 text-sm text-gray-500">
                    Триггер: {item.trigger}
                  </div>

                  <div className="mt-1 text-sm text-gray-500">
                    Действие: {item.action}
                  </div>

                  <div className="mt-2 text-xs text-gray-400">
                    {item.is_active ? "Активна" : "Неактивна"}
                    {item.last_run_at
                      ? ` · Последний запуск: ${new Date(
                          item.last_run_at
                        ).toLocaleString()}`
                      : " · Ещё не запускалась"}
                  </div>
                </div>

                <button
                  onClick={() => deleteAutomation(item.id)}
                  className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Удалить
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
