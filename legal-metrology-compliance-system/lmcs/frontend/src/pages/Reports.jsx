import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import Layout from "../components/Layout";
import { StatusBadge } from "../components/Badges";

const STATUS_FILTERS = [
  { value: "", label: "All statuses" },
  { value: "compliant", label: "Compliant" },
  { value: "minor_issues", label: "Minor Issues" },
  { value: "non_compliant", label: "Non-Compliant" },
];

export default function Reports() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [finalizedOnly, setFinalizedOnly] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams({ page_size: "50" });
    if (status) params.set("overall_status", status);
    if (finalizedOnly) params.set("is_finalized", finalizedOnly);
    api.get(`/reports?${params.toString()}`)
      .then((res) => { setItems(res.data.items); setTotal(res.data.total); })
      .finally(() => setLoading(false));
  };

  useEffect(load, [status, finalizedOnly]);

  return (
    <Layout>
      <h2 className="text-2xl font-bold text-gray-900 mb-1">Compliance Reports</h2>
      <p className="text-sm text-gray-500 mb-6">{total} report(s) on record.</p>

      <div className="flex gap-3 mb-6">
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_FILTERS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
        <select className="input max-w-xs" value={finalizedOnly} onChange={(e) => setFinalizedOnly(e.target.value)}>
          <option value="">All (draft + finalized)</option>
          <option value="true">Finalized only</option>
          <option value="false">Draft only</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-gray-400 text-sm">No reports match this filter.</p>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-3">Generated</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Score</th>
                <th className="text-left px-4 py-3">Findings</th>
                <th className="text-left px-4 py-3">Finalized</th>
                <th></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-600">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3"><StatusBadge status={r.overall_status} /></td>
                  <td className="px-4 py-3 font-medium text-gray-800">{r.compliance_score}</td>
                  <td className="px-4 py-3 text-gray-600">{r.violations.length}</td>
                  <td className="px-4 py-3 text-gray-600">{r.is_finalized ? "Yes" : "Draft"}</td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/reports/${r.id}`} className="text-brand-600 hover:underline text-xs font-medium">
                      Open →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
