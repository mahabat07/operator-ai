"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PriorityBadge from "@/components/PriorityBadge";

type Task = {
  id: string;
  title: string;
  description?: string | null;
  priority: string;
  priority_source?: string | null;
  priority_score?: number | null;
  priority_reason?: string | null;
  status: string;
  deadline?: string | null;
};

type Commitment = {
  id: string;
  title: string;
  deadline?: string | null;
};

type WaitingFor = {
  id: string;
  title: string;
  expected_by?: string | null;
};

type DashboardData = {
  today: {
    tasks: Task[];
    overdue_tasks: Task[];
    upcoming_tasks: Task[];
    important_tasks: Task[];
    commitments: Commitment[];
    waiting_for: WaitingFor[];
  };
  metrics: {
    open_tasks: number;
    completed_today: number;
    overdue: number;
    active_projects: number;
    upcoming_deadlines: number;
    open_commitments: number;
    waiting_for: number;
    risks: number;
  };
  ai_briefing: string;
};

const metricCards = [
  ["open_tasks", "Открытые задачи"],
  ["completed_today", "Завершено сегодня"],
  ["overdue", "Просрочено"],
  ["active_projects", "Активные проекты"],
  ["upcoming_deadlines", "Ближайшие дедлайны"],
  ["open_commitments", "Обязательства"],
  ["waiting_for", "В ожидании"],
  ["risks", "Риски"],
] as const;

function TaskRow({ task }: { task: Task }) {
  return (
    <div className="flex items-start justify-between gap-4 border rounded-xl p-4 bg-white">
      <div className="min-w-0">
        <div className="font-medium text-gray-900">
          {task.title}
        </div>

        {task.deadline && (
          <div className="text-xs text-gray-500 mt-1">
            Дедлайн: {task.deadline}
          </div>
        )}

        {task.priority_reason && (
          <div className="text-xs text-gray-500 mt-2">
            {task.priority_reason}
          </div>
        )}
      </div>

      <div className="flex flex-col items-end gap-1 shrink-0">
        <PriorityBadge
          priority={task.priority}
          source={task.priority_source || undefined}
          reason={task.priority_reason}
        />

        {task.priority_score !== null &&
          task.priority_score !== undefined && (
            <span className="text-[11px] text-gray-400">
              score {task.priority_score}/100
            </span>
          )}
      </div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="border border-dashed rounded-xl p-5 text-sm text-gray-400 bg-white">
      {text}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState(false);

  async function load() {
    try {
      setError(false);
      const result = await api.get<DashboardData>("/dashboard");
      setData(result);
    } catch {
      setError(true);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) {
    return (
      <div className="border border-red-200 bg-red-50 rounded-xl p-5">
        <h1 className="font-semibold text-red-800">
          Не удалось загрузить Dashboard
        </h1>
        <button
          onClick={load}
          className="mt-3 underline text-sm text-red-700"
        >
          Повторить
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-gray-400">
        Загружаем Dashboard...
      </div>
    );
  }

  const { metrics } = data;

  return (
    <div className="flex flex-col gap-8 pb-10">

      {/* HEADER */}
      <header>
        <div className="text-sm text-gray-400 mb-1">
          Оператор ИИ
        </div>

        <h1 className="text-3xl font-semibold text-gray-900">
          Панель управления
        </h1>

        <p className="text-gray-500 mt-1">
          Главное, что требует твоего внимания сейчас.
        </p>
      </header>

      {/* AI BRIEF */}
      <section className="rounded-2xl border bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">✨</span>
          <h2 className="text-lg font-semibold">
            Утренний брифинг
          </h2>
        </div>

        <p className="text-gray-700 leading-7">
          {data.ai_briefing}
        </p>
      </section>

      {/* METRICS */}
      <section>
        <h2 className="font-semibold text-lg mb-3">
          Состояние рабочего пространства
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {metricCards.map(([key, label]) => {
            const value = metrics[key];

            return (
              <div
                key={key}
                className="bg-white border rounded-xl p-4"
              >
                <div className="text-2xl font-semibold text-gray-900">
                  {value}
                </div>

                <div className="text-xs text-gray-500 mt-1">
                  {label}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* IMPORTANT */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg">
            🎯 Главное внимание
          </h2>

          <a
            href="/tasks"
            className="text-sm text-gray-500 underline"
          >
            Все задачи
          </a>
        </div>

        {data.today.important_tasks.length > 0 ? (
          <div className="flex flex-col gap-2">
            {data.today.important_tasks.map((task) => (
              <TaskRow key={task.id} task={task} />
            ))}
          </div>
        ) : (
          <Empty text="Активных задач пока нет." />
        )}
      </section>

      {/* OVERDUE + TODAY */}
      <div className="grid md:grid-cols-2 gap-6">

        <section>
          <h2 className="font-semibold text-lg mb-3">
            🔴 Просрочено
          </h2>

          {data.today.overdue_tasks.length > 0 ? (
            <div className="flex flex-col gap-2">
              {data.today.overdue_tasks.map((task) => (
                <TaskRow key={task.id} task={task} />
              ))}
            </div>
          ) : (
            <Empty text="Просроченных задач нет." />
          )}
        </section>

        <section>
          <h2 className="font-semibold text-lg mb-3">
            📅 Сегодня
          </h2>

          {data.today.tasks.length > 0 ? (
            <div className="flex flex-col gap-2">
              {data.today.tasks.map((task) => (
                <TaskRow key={task.id} task={task} />
              ))}
            </div>
          ) : (
            <Empty text="На сегодня задач нет." />
          )}
        </section>
      </div>

      {/* UPCOMING */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg">
            ⏰ Ближайшие дедлайны
          </h2>

          <span className="text-sm text-gray-400">
            {metrics.upcoming_deadlines}
          </span>
        </div>

        {data.today.upcoming_tasks.length > 0 ? (
          <div className="flex flex-col gap-2">
            {data.today.upcoming_tasks.map((task) => (
              <TaskRow key={task.id} task={task} />
            ))}
          </div>
        ) : (
          <Empty text="Ближайших дедлайнов нет." />
        )}
      </section>

      {/* COMMITMENTS + WAITING */}
      <div className="grid md:grid-cols-2 gap-6">

        <section>
          <h2 className="font-semibold text-lg mb-3">
            🤝 Обязательства
          </h2>

          {data.today.commitments.length > 0 ? (
            <div className="flex flex-col gap-2">
              {data.today.commitments.map((item) => (
                <div
                  key={item.id}
                  className="bg-white border rounded-xl p-4"
                >
                  <div className="font-medium">
                    {item.title}
                  </div>

                  {item.deadline && (
                    <div className="text-xs text-gray-400 mt-1">
                      До: {item.deadline}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <Empty text="Открытых обязательств нет." />
          )}
        </section>

        <section>
          <h2 className="font-semibold text-lg mb-3">
            ⏳ В ожидании
          </h2>

          {data.today.waiting_for.length > 0 ? (
            <div className="flex flex-col gap-2">
              {data.today.waiting_for.map((item) => (
                <div
                  key={item.id}
                  className="bg-white border rounded-xl p-4"
                >
                  <div className="font-medium">
                    {item.title}
                  </div>

                  {item.expected_by && (
                    <div className="text-xs text-gray-400 mt-1">
                      Ожидается: {item.expected_by}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <Empty text="Ничего не ожидается." />
          )}
        </section>

      </div>

      {/* QUICK ACTIONS */}
      <section className="border rounded-2xl bg-gray-50 p-5">
        <h2 className="font-semibold mb-3">
          Быстрые действия
        </h2>

        <div className="flex flex-wrap gap-2">
          <a
            href="/tasks"
            className="bg-black text-white px-4 py-2 rounded-lg text-sm"
          >
            + Новая задача
          </a>

          <a
            href="/assistant"
            className="bg-white border px-4 py-2 rounded-lg text-sm"
          >
            Спросить помощника
          </a>

          <a
            href="/priorities"
            className="bg-white border px-4 py-2 rounded-lg text-sm"
          >
            Посмотреть приоритеты
          </a>

          <a
            href="/weekly-review"
            className="bg-white border px-4 py-2 rounded-lg text-sm"
          >
            Еженедельный обзор
          </a>
        </div>
      </section>

    </div>
  );
}
