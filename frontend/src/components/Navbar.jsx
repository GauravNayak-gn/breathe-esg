import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function Navbar() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await api.auth.logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed', error);
    }
  };

  return (
    <nav className="navbar">
      <div className="nav-logo">Breathe ESG</div>
      <div className="nav-links">
        <Link to="/dashboard" className="nav-link">Dashboard</Link>
        <Link to="/review" className="nav-link">Review</Link>
        <button onClick={handleLogout} className="btn btn-outline" style={{ marginLeft: '1rem' }}>
          Logout
        </button>
      </div>
    </nav>
  );
}
