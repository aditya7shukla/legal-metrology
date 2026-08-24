import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard", short: "D" },
  { to: "/scan", label: "New inspection", short: "N" },
  { to: "/repository", label: "Product repository", short: "P" },
  { to: "/reports", label: "Compliance reports", short: "R" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      <aside className="bg-brand-900 text-white lg:fixed lg:inset-y-0 lg:flex lg:w-72 lg:flex-col">
        <div className="border-b border-white/10 px-5 py-5"><div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-white text-sm font-black text-brand-900">LM</div><div><h1 className="text-base font-bold leading-tight">Legal Metrology</h1><p className="text-xs text-brand-100/80">Inspection workspace</p></div></div></div>
        <nav className="flex gap-1 overflow-x-auto px-3 py-3 lg:flex-1 lg:flex-col lg:py-5">
          {navItems.map((item) => <NavLink key={item.to} to={item.to} end={item.to === "/"} className={({ isActive }) => `flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? "bg-white text-brand-900 shadow-sm" : "text-brand-100/90 hover:bg-white/10 hover:text-white"}`}><span className="grid h-5 w-5 place-items-center rounded-md bg-current/10 text-[10px] font-bold">{item.short}</span>{item.label}</NavLink>)}
        </nav>
        <div className="hidden border-t border-white/10 px-5 py-5 text-sm lg:block"><div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-full bg-white/15 text-xs font-bold">{user?.full_name?.slice(0, 1) || "U"}</div><div className="min-w-0"><p className="truncate font-medium">{user?.full_name}</p><p className="text-xs text-brand-100/70 capitalize">{user?.role?.replace("_", " ")}</p></div></div><button onClick={() => { logout(); navigate("/login"); }} className="mt-4 text-xs text-brand-100/80 hover:text-white">Sign out</button></div>
      </aside>
      <main className="min-h-screen flex-1 lg:ml-72"><div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-9">{children}</div></main>
    </div>
  );
}
