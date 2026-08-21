import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-semibold">Operator AI</h1>
      <p className="text-gray-500">Your AI Chief of Staff</p>
      <div className="flex gap-3">
        <Link href="/login" className="px-4 py-2 bg-black text-white rounded-lg">Log in</Link>
        <Link href="/register" className="px-4 py-2 border rounded-lg">Sign up</Link>
      </div>
    </main>
  );
}
