"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/assistant", label: "Assistant" },
  { href: "/inbox", label: "Inbox" },
  { href: "/tasks", label: "Tasks" },
  { href: "/priorities", label: "Priorities" },
  { href: "/projects", label: "Projects" },
  { href: "/commitments", label: "Commitments" },
  { href: "/waiting-for", label: "Waiting For" },
  { href: "/risks", label: "Risks" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/weekly-review", label: "Weekly Review" },
  { href: "/automations", label: "Automations" },
  { href: "/calendar", label: "Calendar" },
    { href: "/drive", label: "Google Drive" },
  { href: "/meetings", label: "Meetings" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/settings", label: "Settings" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="w-56 shrink-0 border-r bg-white min-h-screen p-4 flex flex-col">
      <div className="font-semibold text-lg mb-6">Operator AI</div>
      <nav className="flex flex-col gap-1 flex-1">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`px-3 py-2 rounded-lg text-sm ${pathname === l.href ? "bg-black text-white" : "text-gray-700 hover:bg-gray-100"}`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
      <button
        onClick={() => { clearTokens(); router.push("/login"); }}
        className="text-sm text-gray-400 hover:text-gray-700 text-left px-3 py-2"
      >
        Log out
      </button>
    </aside>
  );
}
