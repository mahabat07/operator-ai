"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { saveTokens, api } from "@/lib/api";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);

    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");

    if (!accessToken || !refreshToken) {
      setError("Google login did not return valid tokens.");
      return;
    }

    saveTokens(accessToken, refreshToken);

    window.history.replaceState(
      {},
      document.title,
      "/oauth/callback"
    );

    // After login, check if user already has a Google Workspace connection
    // If not, redirect to Settings so they can connect Gmail/Calendar
    async function checkAndRedirect() {
      try {
        const status = await api.get<{ connected: boolean; email?: string }>(
          "/integrations/google/status"
        );
        if (status.connected) {
          // Already connected - go to dashboard
          router.replace("/dashboard");
        } else {
          // First time - redirect to settings to connect Google Workspace
          router.replace("/settings");
        }
      } catch {
        // If check fails (e.g. token issue), just go to dashboard
        router.replace("/dashboard");
      }
    }

    checkAndRedirect();
  }, [router]);

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">
            Google login failed
          </h1>
          <p className="text-red-600">{error}</p>
          <a href="/login" className="underline mt-4 inline-block">
            Back to login
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <p>Signing you in with Google...</p>
    </main>
  );
}
