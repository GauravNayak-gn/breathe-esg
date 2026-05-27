export default function StatCard({ label, value, unit = '' }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value} <span style={{ fontSize: '0.875rem', fontWeight: 'normal' }}>{unit}</span>
      </div>
    </div>
  );
}
