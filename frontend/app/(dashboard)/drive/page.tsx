"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type DriveFile = {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime: string;
  webViewLink: string | null;
};

type DriveResponse = {
  connected: boolean;
  count: number;
  files: DriveFile[];
  detail?: string;
};

export default function DrivePage() {
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setMessage(null);

    try {
      const data = await api.get<DriveResponse>("/drive/files");

      setFiles(data.files || []);

      if (!data.connected) {
        setMessage(
          data.detail || "Google account is not connected."
        );
      }
    } catch {
      setMessage(
        "Could not load Google Drive files."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            Google Drive
          </h1>

          <p className="text-sm text-gray-500">
            Recently modified files from your Google Drive.
          </p>
        </div>

        <button
          onClick={load}
          disabled={loading}
          className="text-sm border px-3 py-1.5 rounded-lg disabled:opacity-50"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {message && (
        <p className="text-sm text-red-500">
          {message}
        </p>
      )}

      {!loading &&
        files.length === 0 &&
        !message && (
          <p className="text-gray-400 text-sm">
            No files found.
          </p>
        )}

      <ul className="flex flex-col gap-2">
        {files.map((file) => (
          <li
            key={file.id}
            className="bg-white border rounded-xl p-4 flex items-center justify-between gap-4"
          >
            <div>
              <p className="font-medium">
                {file.name}
              </p>

              <p className="text-xs text-gray-400 mt-1">
                {file.mimeType}
                {file.modifiedTime
                  ? ` · Updated ${new Date(
                      file.modifiedTime
                    ).toLocaleString()}`
                  : ""}
              </p>
            </div>

            {file.webViewLink && (
              <a
                href={file.webViewLink}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm border px-3 py-1.5 rounded-lg"
              >
                Open
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}