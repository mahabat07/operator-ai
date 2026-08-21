"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

type ConnectionStatus = {
  connected: boolean;
  email?: string;
  scopes?: string;
};

export default function SettingsPage() {
  const [connecting, setConnecting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);

  useEffect(() => {
    api.get<ConnectionStatus>("/integrations/google/status")
      .then(setStatus)
      .catch(() => setStatus({ connected: false }))
      .finally(() => setLoadingStatus(false));
  }, []);

  async function connectGoogle() {
    setConnecting(true);
    setMsg(null);

    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setMsg("Please log in first.");
        return;
      }

      const res = await api.get<{ authorize_url: string }>(
        "/integrations/google/connect"
      );

      window.location.href = res.authorize_url;
    } catch (error) {
      console.error(error);
      setMsg("Unable to start Google connection. Please log in again.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-lg">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <div className="bg-white border rounded-xl p-4 flex flex-col gap-3">
        <div>
          <h2 className="font-medium">Google Workspace</h2>

          <p className="text-gray-500 text-sm">
            Connect Gmail, Calendar, and Drive so Operator AI can build real
            context using actual Google APIs.
          </p>
        </div>

        {loadingStatus ? (
          <p className="text-sm text-gray-400">Checking connection...</p>
        ) : status?.connected ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm text-green-700 font-medium">
                Connected{status.email ? `: ${status.email}` : ""}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Gmail and Google Calendar are connected and will work automatically.
              No need to reconnect unless you sign in with a different Google account.
            </p>
            <button
              onClick={connectGoogle}
              disabled={connecting}
              className="self-start border px-4 py-2 rounded-lg text-sm disabled:opacity-50 mt-2"
            >
              {connecting ? "Connecting..." : "Reconnect with different account"}
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-gray-300" />
              <span className="text-sm text-gray-500">Not connected</span>
            </div>
            <p className="text-xs text-amber-600">
              Gmail and Google Calendar are not connected yet. Connect now
              so Operator AI can sync your email and calendar.
            </p>
            <button
              onClick={connectGoogle}
              disabled={connecting}
              className="self-start bg-blue-600 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
            >
              {connecting ? "Connecting..." : "Connect Google account"}
            </button>
          </div>
        )}

        {msg && (
          <p className="text-xs text-amber-600">
            {msg}
          </p>
        )}
      </div>
    </div>
  );
}
