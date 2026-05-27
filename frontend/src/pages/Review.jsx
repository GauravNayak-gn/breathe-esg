import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import StatusBadge from '../components/StatusBadge';
import { api } from '../api';

export default function Review() {
  const [emissions, setEmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    source: '',
    scope: '',
    status: '',
    flagged: '',
  });
  const navigate = useNavigate();

  const fetchEmissions = async () => {
    setLoading(true);
    try {
      // Clean up empty filters
      const params = {};
      if (filters.source) params.source = filters.source;
      if (filters.scope) params.scope = filters.scope;
      if (filters.status) params.status = filters.status;
      if (filters.flagged === 'true') params.flagged = 'true';

      const data = await api.emissions.list(params);
      setEmissions(data);
    } catch (err) {
      setError('Failed to load emissions.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmissions();
  }, [filters]);

  const handleAction = async (id, action) => {
    try {
      let response;
      if (action === 'approve') response = await api.emissions.approve(id);
      if (action === 'lock') response = await api.emissions.lock(id);
      if (action === 'reject') {
        const note = window.prompt('Enter rejection reason:');
        if (note === null || note.trim() === '') return;
        response = await api.emissions.reject(id, note);
      }

      if (response.ok) {
        fetchEmissions();
      } else {
        alert('Action failed');
      }
    } catch (err) {
      console.error(err);
      alert('An error occurred');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  return (
    <div>
      <Navbar />
      <div className="container">
        <h1 className="mb-4">Emission Review</h1>

        <div className="filter-bar">
          <div>
            <label className="muted mb-1 d-block">Source</label>
            <select value={filters.source} onChange={e => setFilters({...filters, source: e.target.value})}>
              <option value="">All Sources</option>
              <option value="SAP">SAP</option>
              <option value="UTILITY">UTILITY</option>
              <option value="TRAVEL">TRAVEL</option>
            </select>
          </div>
          <div>
            <label className="muted mb-1 d-block">Scope</label>
            <select value={filters.scope} onChange={e => setFilters({...filters, scope: e.target.value})}>
              <option value="">All Scopes</option>
              <option value="1">Scope 1</option>
              <option value="2">Scope 2</option>
              <option value="3">Scope 3</option>
            </select>
          </div>
          <div>
            <label className="muted mb-1 d-block">Status</label>
            <select value={filters.status} onChange={e => setFilters({...filters, status: e.target.value})}>
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="locked">Locked</option>
            </select>
          </div>
          <div>
            <label className="muted mb-1 d-block">Flagged</label>
            <select value={filters.flagged} onChange={e => setFilters({...filters, flagged: e.target.value})}>
              <option value="">All</option>
              <option value="true">Flagged only</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div>Loading...</div>
        ) : error ? (
          <div style={{ color: 'var(--danger-color)' }}>{error}</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Scope</th>
                <th>Category</th>
                <th>Description</th>
                <th>Period</th>
                <th style={{ textAlign: 'right' }}>CO2e (kg)</th>
                <th>Flags</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {emissions.map(row => (
                <tr key={row.id}>
                  <td><span className="badge badge-grey">{row.source_type}</span></td>
                  <td><span className="badge badge-grey">S{row.scope}</span></td>
                  <td>{row.category}</td>
                  <td title={row.activity_description}>
                    {row.activity_description && row.activity_description.length > 60 
                      ? row.activity_description.substring(0, 60) + '...' 
                      : (row.activity_description || '-')}
                  </td>
                  <td>{formatDate(row.period_start)}</td>
                  <td className="mono" style={{ textAlign: 'right' }}>
                    {parseFloat(row.co2e_kg).toFixed(2)}
                  </td>
                  <td>
                    {row.flags && row.flags.length > 0 && (
                      <span
                        style={{ color: 'var(--warning-color)', cursor: 'help' }}
                        title={row.flags.map(f => `• ${f.text}`).join('\n')}
                      >
                        ⚠ {row.flags.length}
                      </span>
                    )}
                  </td>
                  <td><StatusBadge status={row.review_status} /></td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {row.review_status === 'pending' && (
                        <>
                          <button onClick={() => handleAction(row.id, 'approve')} className="btn btn-primary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>Approve</button>
                          <button onClick={() => handleAction(row.id, 'reject')} className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>Reject</button>
                        </>
                      )}
                      {row.review_status === 'approved' && (
                        <button onClick={() => handleAction(row.id, 'lock')} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', borderColor: 'var(--locked-color)', color: 'var(--locked-color)' }}>Lock</button>
                      )}
                      <button onClick={() => navigate(`/review/${row.id}`)} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>Detail</button>
                    </div>
                  </td>
                </tr>
              ))}
              {emissions.length === 0 && (
                <tr>
                  <td colSpan="9" className="text-center muted">No records found.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
