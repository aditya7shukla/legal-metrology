import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/client";
import Layout from "../components/Layout";
import { StatusBadge, SeverityBadge, ScoreRing } from "../components/Badges";
import { useAuth } from "../context/AuthContext";

const OVERRIDE_OPTIONS = ["compliant", "minor_issues", "non_compliant"];

export default function ReportView() {
  const { reportId } = useParams();
  const { user } = useAuth();
  const [report, setReport] = useState(null);
  const [notes, setNotes] = useState("");
  const [overrideStatus, setOverrideStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const canReview = user?.role === "admin" || user?.role === "officer";

  const load = () => {
    setLoading(true);
    api.get(`/reports/${reportId}`)
      .then((res) => { setReport(res.data); setNotes(res.data.reviewer_notes || ""); })
      .catch(() => setError("Could not load this report."))
      .finally(() => setLoading(false));
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
          <a href={`/api/v1/reports/${report.id}/download/pdf`} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
            Download PDF
          </a>
          <a href={`/api/v1/reports/${report.id}/download/docx`} target="_blank" rel="noreferrer" className="btn-secondary text-sm">
            Download Editable DOCX
          </a>
        </div>
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
