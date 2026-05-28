import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import StatCard from '../components/StatCard';
import { api } from '../api';

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState('');
  const [resetMessage, setResetMessage] = useState('');
  const [uploadStatus, setUploadStatus] = useState({
    sap: { loading: false, result: null, errors: [] },
    utility: { loading: false, result: null, errors: [] },
    travel: { loading: false, result: null, errors: [] },
  });

  const fetchSummary = async () => {
    try {
      const data = await api.dashboard.getSummary();
      setSummary(data);
    } catch (err) {
      setError('Failed to load dashboard summary.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleUpload = async (source, file) => {
    if (!file) return;

    setUploadStatus(prev => ({
      ...prev,
      [source]: { ...prev[source], loading: true, result: null, errors: [] }
    }));

    try {
      let response;
      if (source === 'sap') response = await api.ingest.uploadSap(file);
      if (source === 'utility') response = await api.ingest.uploadUtility(file);
      if (source === 'travel') response = await api.ingest.uploadTravel(file);

      const data = await response.json();
      if (response.ok) {
        setUploadStatus(prev => ({
          ...prev,
          [source]: { loading: false, result: data, errors: [] }
        }));
        fetchSummary(); // Refresh stats
      } else {
        setUploadStatus(prev => ({
          ...prev,
          [source]: { loading: false, result: null, errors: data.errors || [data.error || 'Upload failed'] }
        }));
      }
    } catch (err) {
      setUploadStatus(prev => ({
        ...prev,
        [source]: { loading: false, result: null, errors: ['An unexpected error occurred.'] }
      }));
    }
  };

  const handleReset = async () => {
    const confirmed = window.confirm(
      'Clear all uploaded files and processed emissions for this tenant?'
    );
    if (!confirmed) return;

    setResetting(true);
    setError('');
    setResetMessage('');

    try {
      const data = await api.ingest.reset();
      setUploadStatus({
        sap: { loading: false, result: null, errors: [] },
        utility: { loading: false, result: null, errors: [] },
        travel: { loading: false, result: null, errors: [] },
      });
      setResetMessage(
        `Cleared ${data.deleted.emissions} rows from ${data.deleted.ingestions} uploads.`
      );
      await fetchSummary();
    } catch (err) {
      setError('Failed to reset data.');
      console.error(err);
    } finally {
      setResetting(false);
    }
  };

  if (loading) return <div className="container">Loading...</div>;
  if (error) return <div className="container" style={{ color: 'var(--danger-color)' }}>{error}</div>;

  const { total_rows, pending, flagged, total_co2e_kg } = summary;

  return (
    <div>
      <Navbar />
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Dashboard</h1>
            {resetMessage && <p className="success-text">{resetMessage}</p>}
          </div>
          <button
            type="button"
            className="btn btn-danger"
            onClick={handleReset}
            disabled={resetting || total_rows === 0}
          >
            {resetting ? 'Clearing...' : 'Clear Data'}
          </button>
        </div>
        
        <div className="stats-grid">
          <StatCard label="Total Rows" value={total_rows} />
          <StatCard label="Pending" value={pending} />
          <StatCard label="Flagged" value={flagged} />
          <StatCard label="Total CO2e" value={(total_co2e_kg / 1000).toFixed(2)} unit="tonnes" />
        </div>

        <div className="breakdown-container">
          <div className="detail-section">
            <h3>By Scope</h3>
            <table>
              <thead>
                <tr>
                  <th>Scope</th>
                  <th>Count</th>
                  <th>CO2e (kg)</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_scope.map((item) => (
                  <tr key={item.scope}>
                    <td>Scope {item.scope}</td>
                    <td>{item.count}</td>
                    <td className="mono">{(item.co2e_kg || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="detail-section">
            <h3>By Source</h3>
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Count</th>
                  <th>CO2e (kg)</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_source.map((item) => (
                  <tr key={item.source_type}>
                    <td>{item.source_type}</td>
                    <td>{item.count}</td>
                    <td className="mono">{(item.co2e_kg || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <h2 className="mb-4">Data Ingestion</h2>
        <div className="upload-grid">
          {['sap', 'utility', 'travel'].map(source => (
            <div key={source} className="upload-card">
              <h3 style={{ textTransform: 'uppercase' }}>{source}</h3>
              <p className="muted mb-2">
                {source === 'travel' ? 'Accepts .json' : 'Accepts .csv'}
              </p>
              <input
                type="file"
                accept={source === 'travel' ? '.json' : '.csv'}
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) handleUpload(source, file);
                }}
                disabled={uploadStatus[source].loading}
              />
              
              {uploadStatus[source].loading && <div className="muted">Uploading...</div>}
              
              {uploadStatus[source].result && (
                <div style={{ color: 'var(--primary-accent)', fontSize: '0.875rem' }}>
                  Success: {uploadStatus[source].result.rows_processed} processed, {uploadStatus[source].result.rows_failed} failed
                </div>
              )}
              
              {uploadStatus[source].errors.length > 0 && (
                <div className="error-list">
                  {uploadStatus[source].errors.map((err, i) => (
                    <div key={i}>• {typeof err === 'string' ? err : JSON.stringify(err)}</div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
