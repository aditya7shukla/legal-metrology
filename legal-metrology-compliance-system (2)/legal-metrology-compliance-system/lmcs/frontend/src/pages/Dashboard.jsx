import { useEffect, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import api from "../api/client";
import Layout from "../components/Layout";

const PIE_COLORS = ["#15803D", "#C2410C", "#B91C1C"];

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/dashboard/summary?days=${days}`)
      .then((res) => setSummary(res.data))
      .catch(() => setError("Could not load dashboard data."));
  }, [days]);

  if (error) return <Layout><p className="text-red-600">{error}</p></Layout>;
  if (!summary) return <Layout><p className="text-gray-500">Loading dashboard…</p></Layout>;

  const pieData = [
    { name: "Compliant", value: summary.compliant_count },
    { name: "Minor Issues", value: summary.minor_issues_count },
    { name: "Non-Compliant", value: summary.non_compliant_count },
  ];

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Enforcement Dashboard</h2>
          <p className="text-sm text-gray-500">Overview of scanning and compliance activity.</p>
        </div>
        <select
          value={days} onChange={(e) => setDays(Number(e.target.value))}
          className="input w-40"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Scans" value={summary.total_scans} />
        <StatCard label="Products Tracked" value={summary.total_products} />
        <StatCard label="Compliance Rate" value={`${summary.compliance_rate_pct}%`} />
        <StatCard label="Non-Compliant" value={summary.non_compliant_count} accent="text-red-600" />
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-3">Scans Over Time</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={summary.scans_by_day}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3 className="font-semibold text-gray-800 mb-3">Compliance Breakdown</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={90} label>
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3 className="font-semibold text-gray-800 mb-3">Most Frequent Violations</h3>
        {summary.top_violations.length === 0 ? (
          <p className="text-sm text-gray-500">No violations recorded in this period.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {summary.top_violations.map((v, i) => (
              <li key={i} className="flex justify-between py-2 text-sm">
                <span className="text-gray-700">{v.declaration}</span>
                <span className="font-semibold text-gray-900">{v.count}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Layout>
  );
}

function StatCard({ label, value, accent = "text-gray-900" }) {
  return (
    <div className="card">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}
