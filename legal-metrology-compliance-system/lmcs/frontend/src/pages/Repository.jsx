import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import Layout from "../components/Layout";

export default function Repository() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = (query = "") => {
    setLoading(true);
    api.get(`/products?q=${encodeURIComponent(query)}&page_size=50`)
      .then((res) => { setItems(res.data.items); setTotal(res.data.total); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    load(q);
  };

  return (
    <Layout>
      <h2 className="text-2xl font-bold text-gray-900 mb-1">Product Repository</h2>
      <p className="text-sm text-gray-500 mb-6">
        Search previously scanned products and their inspection history. {total} product(s) tracked.
      </p>

      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          className="input" placeholder="Search by name, brand, manufacturer, or barcode…"
          value={q} onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn-primary shrink-0">Search</button>
      </form>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-gray-400 text-sm">No products found.</p>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Brand</th>
                <th className="text-left px-4 py-3">Category</th>
                <th className="text-left px-4 py-3">Manufacturer</th>
                <th className="text-left px-4 py-3">Imported</th>
                <th className="text-left px-4 py-3">Channel</th>
                <th></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{p.name}</td>
                  <td className="px-4 py-3 text-gray-600">{p.brand || "—"}</td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{p.category}</td>
                  <td className="px-4 py-3 text-gray-600">{p.manufacturer_name || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{p.is_imported ? "Yes" : "No"}</td>
                  <td className="px-4 py-3 text-gray-600">{p.source_channel || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/repository/${p.id}`} className="text-brand-600 hover:underline text-xs font-medium">
                      View History →
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
