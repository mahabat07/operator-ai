"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function GoogleAuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hash = window.location.hash;

    if (!hash) {
      setError("Google login did not return valid tokens.");
      return;
    }

    const params = new URLSearchParams(hash.substring(1));

    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");

    if (!accessToken || !refreshToken) {
      setError("Google login did not return valid tokens.");
      return;
    }

    try {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);

      window.history.replaceState(
        null,
        "",
        window.location.pathname
      );

      router.replace("/dashboard");
    } catch (err) {
      console.error(err);
      setError("Failed to save Google login tokens.");
    }
  }, [router]);

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">
            Google login failed
          </h1>

          <p className="text-red-600">{error}</p>

          <a
            href="/login"
            className="underline mt-4 inline-block"
          >
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
