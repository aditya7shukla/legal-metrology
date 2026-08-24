import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api, { downloadReport } from "../api/client";
import Layout from "../components/Layout";
import { StatusBadge, SeverityBadge, ScoreRing } from "../components/Badges";
import { useAuth } from "../context/AuthContext";

const OVERRIDE_OPTIONS = ["compliant", "minor_issues", "non_compliant"];

export default function ReportView() {
  const { reportId } = useParams();
  const { user } = useAuth();
  const [report, setReport] = useState(null);
  const [diagnostic, setDiagnostic] = useState(null);
  const [notes, setNotes] = useState("");
  const [overrideStatus, setOverrideStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadError, setDownloadError] = useState("");

  const canReview = user?.role === "admin" || user?.role === "officer";

  const load = () => {
    setLoading(true);
    api.get(`/reports/${reportId}`)
      .then((res) => { setReport(res.data); setNotes(res.data.reviewer_notes || ""); })
      .catch(() => setError("Could not load this report."))
      .finally(() => setLoading(false));
    api.get(`/reports/${reportId}/diagnostic`).then((res) => setDiagnostic(res.data)).catch(() => setDiagnostic(null));
  };

  useEffect(load, [reportId]);

  const handleSave = async (finalize) => {
    setSaving(true);
    try {
      const payload = { reviewer_notes: notes };
      if (overrideStatus) payload.override_status = overrideStatus;
      if (finalize !== undefined) payload.is_finalized = finalize;
      const { data } = await api.patch(`/reports/${reportId}/review`, payload);
      setReport(data);
      setOverrideStatus("");
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async (format) => {
    setDownloadError("");
    try {
      await downloadReport(report.id, format);
    } catch (err) {
      setDownloadError(err.response?.status === 404 ? "The report file is not available yet." : "Could not download the report. Please sign in again and retry.");
    }
  };

  if (loading) return <Layout><p className="text-gray-400 text-sm">Loading…</p></Layout>;
  if (error || !report) return <Layout><p className="text-red-600 text-sm">{error}</p></Layout>;

  const grouped = { critical: [], major: [], minor: [] };
  report.violations.forEach((v) => grouped[v.severity]?.push(v));

  return (
    <Layout>
      <Link to="/reports" className="text-sm text-brand-600 hover:underline">&larr; Back to reports</Link>

      <div className="card mt-4 mb-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Compliance Report</h2>
            <p className="text-xs text-gray-400 mt-1">ID: {report.id}</p>
            <p className="text-xs text-gray-400">Generated {new Date(report.created_at).toLocaleString()}</p>
          </div>
          <div className="flex items-center gap-4">
            <ScoreRing score={report.compliance_score} />
            <StatusBadge status={report.overall_status} />
            {report.is_finalized && <span className="badge bg-blue-100 text-blue-800">Finalized</span>}
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-4">{report.summary}</p>
        <div className="flex gap-3 mt-4">
          <button type="button" onClick={() => handleDownload("pdf")} className="btn-secondary text-sm">Download PDF</button>
          <button type="button" onClick={() => handleDownload("docx")} className="btn-secondary text-sm">Download Editable DOCX</button>
        </div>
        {downloadError && <p className="mt-3 text-sm text-red-600">{downloadError}</p>}
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-3">
        Violations & Findings ({report.violations.length})
      </h3>

      {report.violations.length === 0 ? (
        <div className="card mb-6"><p className="text-sm text-gray-500">No violations detected by automated screening.</p></div>
      ) : (
        <div className="space-y-3 mb-6">
          {["critical", "major", "minor"].map((sev) =>
            grouped[sev].map((v, i) => (
              <div key={`${sev}-${i}`} className="card flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <SeverityBadge severity={v.severity} />
                    <span className="font-medium text-gray-800">{v.declaration_title}</span>
                  </div>
                  <p className="text-sm text-gray-600">{v.description}</p>
                  {v.rule_reference && (
                    <p className="text-xs text-gray-400 mt-1">Rule reference: {v.rule_reference}</p>
                  )}
                  {v.detected_value && (
                    <p className="text-xs text-gray-500 mt-1">Detected: "{v.detected_value}"</p>
                  )}
                  {v.expected_requirement && (
                    <p className="text-xs text-gray-500">Expected: {v.expected_requirement}</p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <details className="card mb-6 group">
        <summary className="cursor-pointer list-none flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-slate-900">OCR diagnostic</p>
            <p className="mt-1 text-sm text-slate-500">See the exact text used for the automated rule checks.</p>
          </div>
          <span className="text-brand-600 text-sm font-medium group-open:hidden">Show</span>
          <span className="text-brand-600 text-sm font-medium hidden group-open:inline">Hide</span>
        </summary>
        <div className="mt-4 border-t border-slate-100 pt-4">
          {diagnostic?.extracted_fields?.declarations_found?.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Matched declaration evidence</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {diagnostic.extracted_fields.declarations_found.map((item) => (
                  <div key={item.code} className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
                    <p className="font-semibold text-slate-800">{item.title}</p>
                    <p className="mt-1 break-words text-slate-600">{item.matched}</p>
                    {item.evidence?.[0] && <p className="mt-1 text-slate-400">Image {item.evidence[0].image_index + 1} · x:{item.evidence[0].x}, y:{item.evidence[0].y} · OCR {Math.round(item.evidence[0].confidence)}%</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {diagnostic?.raw_ocr_text ? (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">{diagnostic.raw_ocr_text}</pre>
          ) : (
            <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">No OCR text was retained for this scan. This means the system could not provide evidence for its automated findings.</p>
          )}
        </div>
      </details>

      {canReview && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Officer Review</h3>
          <label className="label">Notes (visible in exported reports)</label>
          <textarea
            className="input mb-4" rows={4}
            placeholder="Add physical verification notes, corrective directions, or overrides…"
            value={notes} onChange={(e) => setNotes(e.target.value)}
          />
          <label className="label">Override automated status (optional)</label>
          <select className="input mb-4 max-w-xs" value={overrideStatus} onChange={(e) => setOverrideStatus(e.target.value)}>
            <option value="">No override — keep automated status</option>
            {OVERRIDE_OPTIONS.map((o) => <option key={o} value={o}>{o.replace("_", " ")}</option>)}
          </select>
          <div className="flex gap-3">
            <button disabled={saving} onClick={() => handleSave(undefined)} className="btn-secondary">
              Save Notes
            </button>
            {!report.is_finalized && (
              <button disabled={saving} onClick={() => handleSave(true)} className="btn-primary">
                Finalize Report
              </button>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
