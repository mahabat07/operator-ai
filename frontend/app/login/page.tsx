"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, saveTokens } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function loginWithGoogle() {
    window.location.href = "http://localhost:8001/api/v1/auth/google/login";
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.post<{
        tokens: {
          access_token: string;
          refresh_token: string;
        };
      }>("/auth/login", { email, password });

      saveTokens(
        res.tokens.access_token,
        res.tokens.refresh_token
      );

      router.push("/dashboard");
    } catch (err) {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white p-8 rounded-xl border flex flex-col gap-4"
      >
        <h1 className="text-xl font-semibold">Log in</h1>

        <button
          type="button"
          onClick={loginWithGoogle}
          className="border rounded-lg py-2 hover:bg-gray-50"
        >
          Continue with Google
        </button>

        <div className="flex items-center gap-3">
          <div className="h-px bg-gray-200 flex-1" />
          <span className="text-xs text-gray-400">OR</span>
          <div className="h-px bg-gray-200 flex-1" />
        </div>

        <input
          className="border rounded-lg px-3 py-2"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          className="border rounded-lg px-3 py-2"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && (
          <p className="text-red-600 text-sm">{error}</p>
        )}

        <button
          disabled={loading}
          className="bg-black text-white rounded-lg py-2 disabled:opacity-50"
        >
          {loading ? "..." : "Log in"}
        </button>

        <p className="text-sm text-gray-500 text-center">
          No account?{" "}
          <Link href="/register" className="underline">
            Sign up
          </Link>
        </p>
      </form>
    </main>
  );
}
