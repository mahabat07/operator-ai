"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, saveTokens } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "", workspace_name: "My Workspace" });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<{ tokens: { access_token: string; refresh_token: string } }>("/auth/register", form);
      saveTokens(res.tokens.access_token, res.tokens.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      setError("Could not create account — email may already be registered.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="w-full max-w-sm bg-white p-8 rounded-xl border flex flex-col gap-4">
        <h1 className="text-xl font-semibold">Create your workspace</h1>
        <input className="border rounded-lg px-3 py-2" placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        <input className="border rounded-lg px-3 py-2" type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <input className="border rounded-lg px-3 py-2" type="password" placeholder="Password (min 8 chars)" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} />
        <input className="border rounded-lg px-3 py-2" placeholder="Workspace name" value={form.workspace_name} onChange={(e) => setForm({ ...form, workspace_name: e.target.value })} />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button disabled={loading} className="bg-black text-white rounded-lg py-2 disabled:opacity-50">{loading ? "..." : "Sign up"}</button>
        <p className="text-sm text-gray-500 text-center">Already have an account? <Link href="/login" className="underline">Log in</Link></p>
      </form>
    </main>
  );
}
