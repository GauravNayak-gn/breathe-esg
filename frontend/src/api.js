const BASE_URL = 'http://localhost:8000';

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

export async function apiFetch(url, options = {}) {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  const csrfToken = getCookie('csrftoken');
  
  const headers = {
    ...options.headers,
  };

  if (csrfToken && (options.method === 'POST' || options.method === 'PUT' || options.method === 'PATCH' || options.method === 'DELETE')) {
    headers['X-CSRFToken'] = csrfToken;
  }

  const response = await fetch(fullUrl, {
    credentials: 'include',
    ...options,
    headers,
  });

  if (response.status === 403) {
    if (!url.includes('/api/auth/login/') && !url.includes('/api/auth/csrf/')) {
       // Only redirect if we are not already trying to auth
       window.location.href = '/login';
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Request failed with status ${response.status}`);
  }

  return response;
}

export const api = {
  auth: {
    getCsrf: () => apiFetch('/api/auth/csrf/'),
    login: (formData) => apiFetch('/api/auth/login/', {
      method: 'POST',
      body: formData, // FormData or URLSearchParams as requested
    }),
    logout: () => apiFetch('/api/auth/logout/', { method: 'POST' }),
  },
  dashboard: {
    getSummary: () => apiFetch('/api/dashboard/').then(r => r.json()),
  },
  ingest: {
    uploadSap: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return apiFetch('/api/ingest/sap/', { method: 'POST', body: fd });
    },
    uploadUtility: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return apiFetch('/api/ingest/utility/', { method: 'POST', body: fd });
    },
    uploadTravel: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return apiFetch('/api/ingest/travel/', { method: 'POST', body: fd });
    },
  },
  emissions: {
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return apiFetch(`/api/emissions/${query ? `?${query}` : ''}`).then(r => r.json());
    },
    get: (id) => apiFetch(`/api/emissions/${id}/`).then(r => r.json()),
    approve: (id) => apiFetch(`/api/emissions/${id}/approve/`, { method: 'POST' }),
    reject: (id, note) => apiFetch(`/api/emissions/${id}/reject/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }),
    }),
    lock: (id) => apiFetch(`/api/emissions/${id}/lock/`, { method: 'POST' }),
  }
};
