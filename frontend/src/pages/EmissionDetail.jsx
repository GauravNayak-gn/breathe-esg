import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api';

export default function EmissionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [emission, setEmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const data = await api.emissions.get(id);
        setEmission(data);
      } catch (err) {
        setError('Failed to load emission detail.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (loading) return <div className="container">Loading...</div>;
  if (error) return <div className="container" style={{ color: 'var(--danger-color)' }}>{error}</div>;

  const getConfidenceClass = (score) => {
    if (score >= 0.8) return 'confidence-high';
    if (score >= 0.5) return 'confidence-mid';
    return 'confidence-low';
  };

  const DLRow = ({ label, value }) => (
    <div className="dl-row">
      <div className="dl-label">{label}</div>
      <div className="dl-value">{value ?? '-'}</div>
    </div>
  );

  return (
    <div>
      <Navbar />
      <div className="container">
        <button onClick={() => navigate('/review')} className="btn btn-outline mb-4">
          ← Back to Review
        </button>

        <div className="detail-grid">
          <div>
            <div className="detail-section">
              <div className="detail-header">
                <h2>Original Data</h2>
                <div className="muted">As ingested from source</div>
              </div>
              
              <DLRow label="Source" value={<span className="badge badge-grey">{emission.source_type}</span>} />
              <DLRow label="Scope" value={<span className="badge badge-grey">S{emission.scope}</span>} />
              <DLRow label="Category" value={emission.category} />
              <DLRow label="Status" value={<StatusBadge status={emission.review_status} />} />
              <DLRow label="Original Quantity" value={`${emission.quantity_original} ${emission.unit_original}`} />
              <DLRow label="Normalized Quantity" value={`${emission.quantity_normalized} ${emission.unit_normalized}`} />
              <DLRow label="Conversion Applied" value={emission.conversion_applied || 'None'} />
              <DLRow label="Emission Factor" value={emission.emission_factor_used} />
              <DLRow label="Factor Unit" value={emission.emission_factor_unit} />
              <DLRow label="Factor Source" value={emission.emission_factor_source} />
              <DLRow label="CO2e (kg)" value={<span className="mono">{parseFloat(emission.co2e_kg).toFixed(2)}</span>} />
              <DLRow label="Confidence Score" value={
                <span className={getConfidenceClass(emission.confidence_score)}>
                  {(emission.confidence_score * 100).toFixed(0)}%
                </span>
              } />
              <DLRow label="Period" value={`${emission.period_start} to ${emission.period_end}`} />

              <h3 className="mt-4 mb-2">Flags</h3>
              {emission.flags && emission.flags.length > 0 ? (
                <ul className="flag-list">
                  {emission.flags.map((flag, i) => (
                    <li key={i} className="flag-item">⚠ {flag.text}</li>
                  ))}
                </ul>
              ) : (
                <div className="muted">No flags</div>
              )}

              <h3 className="mt-4 mb-2">Metadata</h3>
              <div className="muted">
                {emission.metadata ? Object.entries(emission.metadata).map(([k, v]) => (
                  <div key={k}>{k}: {JSON.stringify(v)}</div>
                )) : 'No metadata'}
              </div>
            </div>
          </div>

          <div>
            <div className="detail-section">
              <h2>Audit Trail</h2>
              <div className="audit-timeline">
                {emission.audit_logs && emission.audit_logs.map((log, i) => (
                  <div key={i} className="audit-entry">
                    <div className="mb-1">
                      <StatusBadge status={log.action} />
                      <span className="muted" style={{ marginLeft: '0.5rem' }}>
                        by {log.performed_by__username || 'System'}
                      </span>
                    </div>
                    <div className="muted mb-2">
                      {new Date(log.performed_at).toLocaleString()}
                    </div>
                    {log.note && <div style={{ fontStyle: 'italic', color: 'var(--text-primary)' }}>"{log.note}"</div>}
                    {log.new_value && Object.keys(log.new_value).length > 0 && (
                      <div className="mt-2 mono" style={{ fontSize: '0.75rem', background: '#000', padding: '0.5rem', borderRadius: '4px' }}>
                        {JSON.stringify(log.new_value)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
