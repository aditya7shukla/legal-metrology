import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/scan", label: "New Scan", icon: "📷" },
  { to: "/repository", label: "Product Repository", icon: "📦" },
  { to: "/reports", label: "Compliance Reports", icon: "📄" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-brand-900 text-white flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-white/10">
          <h1 className="text-base font-bold leading-tight">Legal Metrology</h1>
          <p className="text-xs text-brand-100/80">Compliance Checking System</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  isActive ? "bg-white/15 text-white" : "text-brand-100/90 hover:bg-white/10"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-white/10 text-sm">
          <p className="font-medium">{user?.full_name}</p>
          <p className="text-xs text-brand-100/70 capitalize">{user?.role?.replace("_", " ")}</p>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="mt-3 text-xs text-brand-100/80 hover:text-white underline"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 min-h-screen overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
