import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/client";
import Layout from "../components/Layout";
import { StatusBadge } from "../components/Badges";

export default function ProductHistory() {
  const { productId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    api.get(`/products/${productId}/history`)
      .then((res) => setData(res.data))
      .catch(() => setError("Could not load product history."))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) return <Layout><p className="text-gray-400 text-sm">Loading…</p></Layout>;
  if (error) return <Layout><p className="text-red-600 text-sm">{error}</p></Layout>;

  const { product, history } = data;

  return (
    <Layout>
      <Link to="/repository" className="text-sm text-brand-600 hover:underline">&larr; Back to repository</Link>

      <div className="card mt-4 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{product.name}</h2>
            <p className="text-sm text-gray-500 mt-1">
              {product.brand && <span>{product.brand} · </span>}
              <span className="capitalize">{product.category}</span>
              {product.is_imported && <span> · Imported</span>}
            </p>
          </div>
          <Link to="/scan" className="btn-primary text-sm">Scan this product</Link>
        </div>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 text-sm">
          <div>
            <dt className="text-gray-400">Manufacturer</dt>
            <dd className="font-medium text-gray-800">{product.manufacturer_name || "Not recorded"}</dd>
          </div>
          <div>
            <dt className="text-gray-400">Barcode</dt>
            <dd className="font-medium text-gray-800">{product.barcode || "—"}</dd>
          </div>
          <div>
            <dt className="text-gray-400">Source Channel</dt>
            <dd className="font-medium text-gray-800">{product.source_channel || "—"}</dd>
          </div>
          <div>
            <dt className="text-gray-400">Total Inspections</dt>
            <dd className="font-medium text-gray-800">{history.length}</dd>
          </div>
        </dl>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-3">Inspection History</h3>
      {history.length === 0 ? (
        <p className="text-gray-400 text-sm">No scans recorded yet for this product.</p>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-3">Date</th>
                <th className="text-left px-4 py-3">Listing Type</th>
                <th className="text-left px-4 py-3">Scan Status</th>
                <th className="text-left px-4 py-3">Compliance</th>
                <th className="text-left px-4 py-3">Score</th>
                <th></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {history.map((h) => (
                <tr key={h.scan_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-600">{new Date(h.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{h.listing_type.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{h.status}</td>
                  <td className="px-4 py-3">
                    {h.compliance_status ? <StatusBadge status={h.compliance_status} /> : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{h.compliance_score ?? "—"}</td>
                  <td className="px-4 py-3 text-right">
                    {h.report_id && (
                      <Link to={`/reports/${h.report_id}`} className="text-brand-600 hover:underline text-xs font-medium">
                        View Report →
                      </Link>
                    )}
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
