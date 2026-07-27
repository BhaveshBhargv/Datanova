import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { NovaMark } from "./brand/NovaMark";

const nav = [
  { to: "/", label: "Workspace", end: true },
  { to: "/datasets", label: "Datasets", end: false },
  { to: "/connections", label: "Connections", end: false },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const initial = (user?.full_name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-paper">
      <div className="mx-auto flex max-w-[1400px]">
        {/* Sidebar */}
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-line bg-white px-4 py-5 sm:flex">
          <NavLink to="/" className="flex items-center gap-2 px-2">
            <NovaMark size={24} />
            <span className="font-display text-[17px] font-bold tracking-tight text-ink">
              Data<span className="text-nova-600">Nova</span>
            </span>
          </NavLink>

          <p className="eyebrow mt-8 px-3">Navigate</p>
          <nav className="mt-2 space-y-1">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? "bg-nova-50 text-nova-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-ink"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`h-1.5 w-1.5 rounded-full transition ${
                        isActive ? "bg-nova-500" : "bg-slate-300 group-hover:bg-slate-400"
                      }`}
                    />
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-xl border border-line bg-paper p-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink font-display text-sm font-bold text-white">
                {initial}
              </div>
              <div className="min-w-0">
                <div className="truncate text-xs font-medium text-ink">
                  {user?.full_name || "Signed in"}
                </div>
                <div className="truncate font-mono text-[10px] text-slate-400">
                  {user?.email}
                </div>
              </div>
            </div>
            <button
              onClick={logout}
              className="mt-3 w-full rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </aside>

        {/* Main column */}
        <div className="flex min-h-screen flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-line bg-white/80 px-6 py-3 backdrop-blur sm:hidden">
            <span className="flex items-center gap-2">
              <NovaMark size={20} />
              <span className="font-display text-sm font-bold text-ink">DataNova</span>
            </span>
            <button
              onClick={logout}
              className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-slate-600"
            >
              Log out
            </button>
          </header>

          <main className="flex-1 px-6 py-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
