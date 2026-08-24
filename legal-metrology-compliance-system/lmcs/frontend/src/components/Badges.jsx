export function StatusBadge({ status }) {
  const label = (status || "").replace("_", " ");
  return <span className={`badge badge-${status}`}>{label}</span>;
}

export function SeverityBadge({ severity }) {
  return <span className={`badge badge-${severity}`}>{severity}</span>;
}

export function ScoreRing({ score = 0 }) {
  const color = score >= 85 ? "#15803D" : score >= 60 ? "#C2410C" : "#B91C1C";
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-14 h-14 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0"
        style={{ background: color }}
      >
        {Math.round(score)}
      </div>
      <span className="text-xs text-gray-500">/ 100</span>
    </div>
  );
}
