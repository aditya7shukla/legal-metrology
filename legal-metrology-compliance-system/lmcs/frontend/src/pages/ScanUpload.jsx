import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import Layout from "../components/Layout";
import { StatusBadge, SeverityBadge, ScoreRing } from "../components/Badges";

const CATEGORIES = ["food", "cosmetics", "electronics", "household", "fmcg_other", "other"];

export default function ScanUpload() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("existing"); // existing | new
  const [products, setProducts] = useState([]);
  const [productId, setProductId] = useState("");
  const [newProduct, setNewProduct] = useState({
    name: "", brand: "", category: "food", manufacturer_name: "", is_imported: false, source_channel: "",
  });
  const [listingType, setListingType] = useState("physical_package");
  const [location, setLocation] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scanResult, setScanResult] = useState(null);
  const [report, setReport] = useState(null);

  useEffect(() => {
    api.get("/products?page_size=100").then((res) => setProducts(res.data.items));
  }, []);

  const handleFile = (e) => {
    const f = e.target.files[0];
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!file) return setError("Please select a label/package image.");
    setLoading(true);
    setScanResult(null);
    setReport(null);
    try {
      const form = new FormData();
      form.append("image", file);
      if (mode === "existing") {
        if (!productId) throw new Error("Select a product from the repository, or switch to 'New product'.");
        form.append("product_id", productId);
      } else {
        form.append("new_product", JSON.stringify(newProduct));
      }
      form.append("listing_type", listingType);
      if (location) form.append("inspection_location_text", location);

      const { data: scan } = await api.post("/scans", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setScanResult(scan);

      if (scan.report_id) {
        const { data: reportData } = await api.get(`/reports/${scan.report_id}`);
        setReport(reportData);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Scan failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <h2 className="text-2xl font-bold text-gray-900 mb-1">New Compliance Scan</h2>
      <p className="text-sm text-gray-500 mb-6">
        Upload a photograph of the product label or an e-commerce listing screenshot to run automated compliance checks.
      </p>

      <div className="grid lg:grid-cols-2 gap-6">
        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="label">Product</label>
            <div className="flex gap-2 mb-2">
              <button type="button" onClick={() => setMode("existing")}
                className={`px-3 py-1.5 rounded-lg text-sm ${mode === "existing" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-600"}`}>
                Existing product
              </button>
              <button type="button" onClick={() => setMode("new")}
                className={`px-3 py-1.5 rounded-lg text-sm ${mode === "new" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-600"}`}>
                New product
              </button>
            </div>

            {mode === "existing" ? (
              <select className="input" value={productId} onChange={(e) => setProductId(e.target.value)}>
                <option value="">Select a product…</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} {p.brand ? `— ${p.brand}` : ""}</option>
                ))}
              </select>
            ) : (
              <div className="space-y-2">
                <input className="input" placeholder="Product name" required
                  value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} />
                <input className="input" placeholder="Brand (optional)"
                  value={newProduct.brand} onChange={(e) => setNewProduct({ ...newProduct, brand: e.target.value })} />
                <select className="input" value={newProduct.category}
                  onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <input className="input" placeholder="Manufacturer name (optional)"
                  value={newProduct.manufacturer_name}
                  onChange={(e) => setNewProduct({ ...newProduct, manufacturer_name: e.target.value })} />
                <input className="input" placeholder="Source channel e.g. Retail Store, Amazon.in"
                  value={newProduct.source_channel}
                  onChange={(e) => setNewProduct({ ...newProduct, source_channel: e.target.value })} />
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input type="checkbox" checked={newProduct.is_imported}
                    onChange={(e) => setNewProduct({ ...newProduct, is_imported: e.target.checked })} />
                  Imported product
                </label>
              </div>
            )}
          </div>

          <div>
            <label className="label">Listing type</label>
            <select className="input" value={listingType} onChange={(e) => setListingType(e.target.value)}>
              <option value="physical_package">Physical package (retail store)</option>
              <option value="ecommerce_listing">E-commerce listing</option>
            </select>
          </div>

          <div>
            <label className="label">Inspection location (optional)</label>
            <input className="input" placeholder="e.g. Big Bazaar, Sector 18, Noida"
              value={location} onChange={(e) => setLocation(e.target.value)} />
          </div>

          <div>
            <label className="label">Label / package photo</label>
            <input type="file" accept="image/*" onChange={handleFile} className="text-sm" />
            {preview && <img src={preview} alt="preview" className="mt-2 rounded-lg max-h-56 border" />}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Analyzing label…" : "Run Compliance Check"}
          </button>
        </form>

        <div>
          {!scanResult && (
            <div className="card h-full flex items-center justify-center text-center text-gray-400 text-sm">
              Results will appear here after you run a scan.
            </div>
          )}
          {scanResult && (
            <div className="card space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-800">Scan Result</h3>
                <span className="text-xs text-gray-400">Scan ID: {scanResult.id.slice(0, 8)}…</span>
              </div>
              {report ? (
                <>
                  <div className="flex items-center gap-4">
                    <ScoreRing score={report.compliance_score} />
                    <StatusBadge status={report.overall_status} />
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                      Findings ({report.violations.length})
                    </h4>
                    {report.violations.length === 0 ? (
                      <p className="text-sm text-green-700">No violations detected.</p>
                    ) : (
                      <ul className="space-y-2">
                        {report.violations.map((v) => (
                          <li key={v.id} className="border rounded-lg p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-gray-800">{v.declaration_title}</span>
                              <SeverityBadge severity={v.severity} />
                            </div>
                            <p className="text-xs text-gray-500">{v.description}</p>
                            {v.rule_reference && (
                              <p className="text-xs text-gray-400 mt-1">Ref: {v.rule_reference}</p>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div className="flex gap-2 pt-2">
                    <a href={`/api/v1/reports/${report.id}/download/pdf`} target="_blank" rel="noreferrer"
                      className="btn-secondary text-sm">Download PDF</a>
                    <a href={`/api/v1/reports/${report.id}/download/docx`} target="_blank" rel="noreferrer"
                      className="btn-secondary text-sm">Download DOCX</a>
                    <button onClick={() => navigate(`/reports/${report.id}`)} className="btn-primary text-sm">
                      Open Full Report
                    </button>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-500">Scan status: {scanResult.status}</p>
              )}
              <details className="text-xs text-gray-400">
                <summary className="cursor-pointer">Raw OCR text (debug)</summary>
                <pre className="whitespace-pre-wrap mt-1">{scanResult.raw_ocr_text}</pre>
              </details>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
