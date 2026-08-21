"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function GoogleWorkspaceCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");

    if (!code) {
      setError("Google did not return an authorization code.");
      return;
    }

    async function connectGoogleWorkspace() {
      try {
        await api.post(
          "/integrations/google/callback?code=" +
            encodeURIComponent(code as string)
        );

        router.replace("/calendar");
      } catch (err) {
        console.error(err);
        setError(
          "Google Workspace connection failed. Please try again."
        );
      }
    }

    connectGoogleWorkspace();
  }, [searchParams, router]);

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">
            Google Workspace connection failed
          </h1>

          <p className="text-red-600">{error}</p>

          <a
            href="/settings"
            className="underline mt-4 inline-block"
          >
            Back to Settings
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <p>Connecting Google Workspace...</p>
    </main>
  );
}

export default function GoogleWorkspaceCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center">
          <p>Connecting Google Workspace...</p>
        </main>
      }
    >
      <GoogleWorkspaceCallbackContent />
    </Suspense>
  );
}
